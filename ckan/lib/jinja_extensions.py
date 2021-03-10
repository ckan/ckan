# encoding: utf-8

import re
from os import path
import logging

from jinja2 import nodes
from jinja2 import loaders
from jinja2 import ext
from jinja2.exceptions import TemplateNotFound
from jinja2.utils import open_if_exists, escape
from jinja2 import Environment
from jinja2 import FileSystemBytecodeCache

from six import text_type
from six.moves import xrange

import ckan.lib.base as base
import ckan.lib.helpers as h
from ckan.common import config


log = logging.getLogger(__name__)


def _get_extensions():
    return ['jinja2.ext.do', 'jinja2.ext.with_',
            SnippetExtension,
            CkanExtend,
            CkanInternationalizationExtension,
            LinkForExtension,
            ResourceExtension,
            UrlForStaticExtension,
            UrlForExtension,
            AssetExtension]


def get_jinja_env_options():
    return dict(
        loader=CkanFileSystemLoader(config['computed_template_paths']),
        autoescape=True,
        extensions=_get_extensions(),
    )


### Filters

def empty_and_escape(value):
    ''' returns '' for a None value else escapes the content useful for form
    elements. '''
    if value is None:
        return ''
    else:
        return escape(value)

### Tags

def regularise_html(html):
    ''' Take badly formatted html with strings etc and make it beautiful
    generally remove surlus whitespace and kill \n this will break <code><pre>
    tags but they should not be being translated '''
    if html is None:
        return
    html = re.sub('\n', ' ', html)
    matches = re.findall('(<[^>]*>|%[^%]\([^)]*\)\w|[^<%]+|%)', html)
    for i in xrange(len(matches)):
        match = matches[i]
        if match.startswith('<') or match.startswith('%'):
            continue
        matches[i] = re.sub('\s{2,}', ' ', match)
    html = ''.join(matches)
    return html


class CkanInternationalizationExtension(ext.InternationalizationExtension):
    ''' Custom translation to allow cleaned up html '''

    def parse(self, parser):
        node = ext.InternationalizationExtension.parse(self, parser)
        if isinstance(node, list):
            args = getattr(node[1].nodes[0], 'args', None)
        else:
            args = getattr(node.nodes[0], 'args', None)
        if args:
            for arg in args:
                if isinstance(arg, nodes.Const):
                    value = arg.value
                    if isinstance(value, text_type):
                        arg.value = regularise_html(value)
        return node


class CkanExtend(ext.Extension):
    ''' Custom {% ckan_extends <template> %} tag that allows templates
    to inherit from the ckan template futher down the template search path
    if no template provided we assume the same template name. '''

    tags = set(['ckan_extends'])

    def __init__(self, environment):
        ext.Extension.__init__(self, environment)
        try:
            self.searchpath = environment.loader.searchpath[:]
        except AttributeError:
            # this isn't available on message extraction
            pass

    def parse(self, parser):
        lineno = next(parser.stream).lineno
        node = nodes.Extends(lineno)
        template_path = parser.filename
        # find where in the search path this template is from
        current_path = None
        if not hasattr(self, 'searchpath'):
            return node
        for searchpath in self.searchpath:
            if template_path.startswith(searchpath):
                current_path = searchpath
                break

        # get filename from full path
        filename = template_path[len(searchpath) + 1:]

        # Providing template path violently deprecated
        if parser.stream.current.type != 'block_end':
            provided_template = parser.parse_expression().value
            if provided_template != filename:
                raise Exception('ckan_extends tag wrong path %s in %s'
                                % (provided_template, template_path))
            else:
                log.critical('Remove path from ckan_extend tag in %s'
                             % template_path)

        # provide our magic format
        # format is *<search path parent directory>*<template name>
        magic_filename = '*' + current_path + '*' + filename
        # set template
        node.template = nodes.Const(magic_filename)
        return node


class CkanFileSystemLoader(loaders.FileSystemLoader):
    ''' This is a variant of the jinja2 FileSystemLoader. It allows
    functionality for the ckan_extends tag. When we use the ckan_extends
    tag we only want to look in the ckan/templates directory rather than
    looking thropugh all the template paths. This allows a none base
    template to be able to extend a base ckan template of the same name.
    This functionality allows easy customisation of ckan via template
    inheritance.

    This class is based on jinja2 code which is licensed as follows
======================================================================
    Copyright (c) 2009 by the Jinja Team, see AUTHORS for more details.

Some rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.

    * Redistributions in binary form must reproduce the above
      copyright notice, this list of conditions and the following
      disclaimer in the documentation and/or other materials provided
      with the distribution.

    * The names of the contributors may not be used to endorse or
      promote products derived from this software without specific
      prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
=====================================================================
    '''

    def get_source(self, environment, template):
        # if the template name starts with * then this should be
        # treated specially.
        # format is *<search path parent directory>*<template name>
        # so we only search from then downwards.  This allows recursive
        # ckan_extends tags
        if template.startswith('*'):
            parts = template.split('*')
            template = parts[2]
            index = self.searchpath.index(parts[1])
            searchpaths = self.searchpath[index + 1:]
        else:
            searchpaths = self.searchpath
        # end of ckan changes
        pieces = loaders.split_template_path(template)
        for searchpath in searchpaths:
            filename = path.join(searchpath, *pieces)
            f = open_if_exists(filename)
            if f is None:
                continue
            try:
                contents = f.read().decode(self.encoding)
            except UnicodeDecodeError as e:
                log.critical(
                    'Template corruption in `%s` unicode decode errors'
                    % filename
                )
                raise e
            finally:
                f.close()

            mtime = path.getmtime(filename)

            def uptodate():
                try:
                    return path.getmtime(filename) == mtime
                except OSError:
                    return False
            return contents, filename, uptodate
        raise TemplateNotFound(template)


class BaseExtension(ext.Extension):
    ''' Base class for creating custom jinja2 tags.
    parse expects a tag of the format
    {% tag_name args, kw %}
    after parsing it will call _call(args, kw) which must be defined. '''

    def parse(self, parser):
        stream = parser.stream
        tag = next(stream)
        # get arguments
        args = []
        kwargs = []
        while not stream.current.test_any('block_end'):
            if args or kwargs:
                stream.expect('comma')
            if stream.current.test('name') and stream.look().test('assign'):
                key = nodes.Const(next(stream).value)
                stream.skip()
                value = parser.parse_expression()
                kwargs.append(nodes.Pair(key, value, lineno=key.lineno))
            else:
                args.append(parser.parse_expression())

        def make_call_node(*kw):
            return self.call_method('_call', args=[
                nodes.List(args),
                nodes.Dict(kwargs),
            ], kwargs=kw)

        return nodes.Output([make_call_node()]).set_lineno(tag.lineno)


class SnippetExtension(BaseExtension):
    ''' Custom snippet tag

    {% snippet <template_name> [, <fallback_template_name>]...
               [, <keyword>=<value>]... %}

    see lib.helpers.snippet() for more details.
    '''

    tags = set(['snippet'])

    @classmethod
    def _call(cls, args, kwargs):
        return base.render_snippet(*args, **kwargs)

class UrlForStaticExtension(BaseExtension):
    ''' Custom url_for_static tag for getting a path for static assets.

    {% url_for_static <path> %}

    see lib.helpers.url_for_static() for more details.
    '''

    tags = set(['url_for_static'])

    @classmethod
    def _call(cls, args, kwargs):
        assert len(args) == 1
        return h.url_for_static(args[0], **kwargs)

class UrlForExtension(BaseExtension):
    ''' Custom url_for tag

    {% url_for <params> %}

    see lib.helpers.url_for() for more details.
    '''

    tags = set(['url_for'])

    @classmethod
    def _call(cls, args, kwargs):
        return h.url_for(*args, **kwargs)


class LinkForExtension(BaseExtension):
    ''' Custom link_for tag

    {% link_for <params> %}

    see lib.helpers.nav_link() for more details.
    '''

    tags = set(['link_for'])

    @classmethod
    def _call(cls, args, kwargs):
        return h.nav_link(*args, **kwargs)

class ResourceExtension(BaseExtension):
    ''' Deprecated. Custom include_resource tag.

    {% resource <resource_name> %}

    see lib.helpers.include_resource() for more details.
    '''

    tags = set(['resource'])

    @classmethod
    def _call(cls, args, kwargs):
        assert len(args) == 1
        assert len(kwargs) == 0
        h.include_resource(args[0], **kwargs)
        return ''


class AssetExtension(BaseExtension):
    ''' Custom include_asset tag.

    {% asset <bundle_name> %}

    see lib.webassets_tools.include_asset() for more details.
    '''

    tags = set(['asset'])

    @classmethod
    def _call(cls, args, kwargs):
        assert len(args) == 1
        assert len(kwargs) == 0
        h.include_asset(args[0])
        return ''


'''
The following function is based on jinja2 code

Provides a class that holds runtime and parsing time options.

:copyright: (c) 2010 by the Jinja Team.
:license: BSD, see LICENSE for more details.
'''

def jinja2_getattr(self, obj, attribute):
    """Get an item or attribute of an object but prefer the attribute.
    Unlike :meth:`getitem` the attribute *must* be a bytestring.

    This is a customised version to work with properties
    """
    try:
        value = getattr(obj, attribute)
        if isinstance(value, property):
            value = value.fget()
        return value
    except AttributeError:
        pass
    try:
        value = obj[attribute]
        if isinstance(value, property):
            value = value.fget()
        return value
    except (TypeError, LookupError, AttributeError):
        return self.undefined(obj=obj, name=attribute)

setattr(Environment, 'get_attr', jinja2_getattr)
del jinja2_getattr
