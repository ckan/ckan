#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8
"""Minification helpers.

This module provides enhanced versions of the ``javascript_link`` and
``stylesheet_link`` helpers in ``webhelpers.html.tags``.  These versions add
three additional arguments:

* **minified**: If true, reduce the file size by squeezing out
  whitespace and other characters insignificant to the Javascript or CSS syntax.
* **combined**: If true, concatenate the specified files into one file to
  reduce page load time.
* **beaker_kwargs** (dict): arguments to pass to ``beaker_cache``.

Dependencies: ``Pylons``, ``Beaker``, ``jsmin``, and ``cssutils`` (all
available in PyPI). If "jsmin" is not installed, the helper issues a warning
and passes Javascript through unchanged. (Changed in WebHelpers 1.1: removed
built-in "_jsmin" package due to licensing issues; details in 
webhelpers/pylonslib/_jsmin.py .)

PYRAMID USERS: this implementation is incompatible with Pyramid. No
Pyramid-compatible implementation is currently known.

Contributed by Pedro Algarvio and Domen Kozar <ufs@ufsoft.org>.
URL: http://docs.fubar.si/minwebhelpers/
"""

import re
import os
import logging
import StringIO
import warnings

from webhelpers.html.tags import javascript_link as __javascript_link
from webhelpers.html.tags import stylesheet_link as __stylesheet_link

try:
    from jsmin import JavascriptMinify
except ImportError:
    class JavascriptMinify(object):
        def minify(self, instream, outstream):
            warnings.warn(JSMIN_MISSING_MESSAGE, UserWarning)
            data = instream.read()
            outstream.write(data)
            instream.close()

JSMIN_MISSING_MESSAGE = """\
_jsmin has been removed from WebHelpers due to licensing issues
Your Javascript code has been passed through unchanged.
You can install the "jsmin" package from PyPI, and this helper will use it.
"""


__all__ = ['javascript_link', 'stylesheet_link']
log = logging.getLogger(__name__)
beaker_kwargs = dict(key='sources',
                     expire='never',
                     type='memory')

def combine_sources(sources, ext, fs_root):
    if len(sources) < 2:
        return sources

    names = list()
    js_buffer = StringIO.StringIO()
    base = os.path.commonprefix([os.path.dirname(s) for s in sources])

    for source in sources:
        # get a list of all filenames without extensions
        js_file = os.path.basename(source)
        js_file_name = os.path.splitext(js_file)[0]
        names.append(js_file_name)

        # build a master file with all contents
        full_source = os.path.join(fs_root, source.lstrip('/'))
        f = open(full_source, 'r')
        js_buffer.write(f.read())
        js_buffer.write('\n')
        f.close()

    # glue a new name and generate path to it
    fname = '.'.join(names + ['COMBINED', ext])
    fpath = os.path.join(fs_root, base.strip('/'), fname)

    # write the combined file
    f = open(fpath, 'w')
    f.write(js_buffer.getvalue())
    f.close()

    return [os.path.join(base, fname)]

def minify_sources(sources, ext, fs_root=''):
    import cssutils 

    if 'js' in ext:
        js_minify = JavascriptMinify()
    minified_sources = []

    for source in sources:
        # generate full path to source
        no_ext_source = os.path.splitext(source)[0]
        full_source = os.path.join(fs_root, (no_ext_source + ext).lstrip('/'))

        # generate minified source path
        full_source = os.path.join(fs_root, (source).lstrip('/'))
        no_ext_full_source = os.path.splitext(full_source)[0]
        minified = no_ext_full_source + ext

        f_minified_source = open(minified, 'w')

        # minify js source (read stream is auto-closed inside)
        if 'js' in ext:
            js_minify.minify(open(full_source, 'r'), f_minified_source)
        # minify css source
        if 'css' in ext:
            serializer = get_serializer()
            sheet = cssutils.parseFile(full_source)
            sheet.setSerializer(serializer)
            cssutils.ser.prefs.useMinified()
            f_minified_source.write(sheet.cssText)

        f_minified_source.close()
        minified_sources.append(no_ext_source + ext)

    return minified_sources

def base_link(ext, *sources, **options):
    from pylons import config
    from pylons.decorators.cache import beaker_cache

    combined = options.pop('combined', False)
    minified = options.pop('minified', False)
    beaker_options = options.pop('beaker_kwargs', False)
    fs_root = config.get('pylons.paths').get('static_files')

    if not (config.get('debug', False) or options.get('builtins', False)):
        if beaker_options:
            beaker_kwargs.update(beaker_options)

        if combined:
            sources = beaker_cache(**beaker_kwargs)(combine_sources)(list(sources), ext, fs_root)

        if minified:
            sources = beaker_cache(**beaker_kwargs)(minify_sources)(list(sources), '.min.' + ext, fs_root)

    if 'js' in ext:
        return __javascript_link(*sources, **options)
    if 'css' in ext:
        return __stylesheet_link(*sources, **options)

def javascript_link(*sources, **options):
    return base_link('js', *sources, **options)

def stylesheet_link(*sources, **options):
    return base_link('css', *sources, **options)


_serializer_class = None

def get_serializer():
    # This is in a function to prevent a global import of ``cssutils``,
    # which is not a WebHelpers dependency.
    # The class is cached in a global variable so that it will be 
    # compiled only once.

    import cssutils

    global _serializer_class
    if not _serializer_class:
        class CSSUtilsMinificationSerializer(cssutils.CSSSerializer):
            def __init__(self, prefs=None):
                cssutils.CSSSerializer.__init__(self, prefs)

            def do_css_CSSStyleDeclaration(self, style, separator=None):
                try:
                    color = style.getPropertyValue('color')
                    if color and color is not u'':
                        color = self.change_colors(color)
                        style.setProperty('color', color)
                except:
                    pass
                return re.sub(r'0\.([\d])+', r'.\1',
                              re.sub(r'(([^\d][0])+(px|em)+)+', r'\2',
                              cssutils.CSSSerializer.do_css_CSSStyleDeclaration(
                                  self, style, separator)))

            def change_colors(self, color):
                colours = {
                    'black': '#000000',
                    'fuchia': '#ff00ff',
                    'yellow': '#ffff00',
                    '#808080': 'gray',
                    '#008000': 'green',
                    '#800000': 'maroon',
                    '#000800': 'navy',
                    '#808000': 'olive',
                    '#800080': 'purple',
                    '#ff0000': 'red',
                    '#c0c0c0': 'silver',
                    '#008080': 'teal'
                }
                if color.lower() in colours:
                    color = colours[color.lower()]

                if color.startswith('#') and len(color) == 7:
                    if color[1]==color[2] and color[3]==color[4] and color[5]==color[6]:
                        color = '#%s%s%s' % (color[1], color[3], color[5])
                return color
        # End of class CSSUtilsMinificationSerializer
        _serializer_class = CSSUtilsMinificationSerializer
    return _serializer_class()
