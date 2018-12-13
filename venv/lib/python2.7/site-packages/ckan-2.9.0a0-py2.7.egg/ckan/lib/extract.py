# encoding: utf-8

import re
from jinja2.ext import babel_extract as extract_jinja2
import lib.jinja_extensions
from six import string_types

jinja_extensions = '''
                    jinja2.ext.do, jinja2.ext.with_,
                    ckan.lib.jinja_extensions.SnippetExtension,
                    ckan.lib.jinja_extensions.CkanExtend,
                    ckan.lib.jinja_extensions.LinkForExtension,
                    ckan.lib.jinja_extensions.ResourceExtension,
                    ckan.lib.jinja_extensions.UrlForStaticExtension,
                    ckan.lib.jinja_extensions.UrlForExtension
                   '''

def jinja2_cleaner(fileobj, *args, **kw):
    # We want to format the messages correctly and intercepting here seems
    # the best location
    # add our custom tags
    kw['options']['extensions'] = jinja_extensions

    raw_extract = extract_jinja2(fileobj, *args, **kw)

    for lineno, func, message, finder in raw_extract:

        if isinstance(message, string_types):
            message = lib.jinja_extensions.regularise_html(message)
        elif message is not None:
            message = (lib.jinja_extensions.regularise_html(message[0])
                       ,lib.jinja_extensions.regularise_html(message[1]))

        yield lineno, func, message, finder


def extract_ckan(fileobj, *args, **kw):
    source = fileobj.read()
    output = jinja2_cleaner(fileobj, *args, **kw)
    # we've eaten the file so we need to get back to the start
    fileobj.seek(0)
    return output
