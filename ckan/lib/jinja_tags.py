from os import path

from jinja2 import nodes
from jinja2 import loaders
from jinja2.ext import Extension
from jinja2.exceptions import TemplateNotFound
from jinja2.utils import open_if_exists

import lib.base as base
import lib.helpers as h


class CkanExtend(Extension):
    ''' Custom {% ckan_extends <template> %} tag that allows templates
    to inherit from the ckan base template of the same name. '''

    tags = set(['ckan_extends'])

    def parse(self, parser):
        # if the template name has a * as the first char it will only be
        # looked for in the ckan base templates
        node = nodes.Extends(lineno=next(parser.stream).lineno)
        node.template = parser.parse_expression()
        node.template.value = '*' + node.template.value
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

    def __init__(self, searchpath, ckan_base_path, encoding='utf-8'):
        # ckan changes: we accept and store the ckan_base_path
        if isinstance(searchpath, basestring):
            searchpath = [searchpath]
        self.searchpath = list(searchpath)
        self.ckan_base_path = ckan_base_path
        self.encoding = encoding

    def get_source(self, environment, template):
        # if the template name starts with * then this should be
        # treated as a ckan base template. otherwise we check all the
        # template paths.
        if template.startswith('*'):
            template = template[1:]
            searchpaths = [self.ckan_base_path]
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


class BaseExtension(Extension):
    ''' Base class for creating custom jinja2 tags.
    parse expects a tag of the format
    {% tag_name args, kw %}
    after parsing it will call _call(args, kw) which must be defined. '''

    def parse(self, parser):
        stream = parser.stream
        tag = stream.next()
        # get arguments
        args = []
        kwargs = []
        while not stream.current.test_any('block_end'):
            if args or kwargs:
                stream.expect('comma')
            if stream.current.test('name') and stream.look().test('assign'):
                key = nodes.Const(stream.next().value)
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

    {% snippet <template_name> [, <keyword>=<value>].. %}

    see lib.helpers.snippet() for more details.
    '''

    tags = set(['snippet'])

    @classmethod
    def _call(cls, args, kwargs):
        assert len(args) == 1
        return base.render_snippet(args[0], **kwargs)

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
    ''' Custom include_resource tag

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
