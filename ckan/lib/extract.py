import re
from genshi.filters.i18n import extract as extract_genshi
from jinja2.ext import babel_extract as extract_jinja2
import lib.jinja_extensions

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

        if isinstance(message, basestring):
            message = lib.jinja_extensions.regularise_html(message)
        elif message is not None:
            message = (lib.jinja_extensions.regularise_html(message[0])
                       ,lib.jinja_extensions.regularise_html(message[1]))

        yield lineno, func, message, finder


def extract_ckan(fileobj, *args, **kw):
    ''' Determine the type of file (Genshi or Jinja2) and then call the
    correct extractor function.

    Basically we just look for genshi.edgewall.org which all genshi XML
    templates should contain. '''

    source = fileobj.read()
    if re.search('genshi\.edgewall\.org', source):
        # genshi
        output = extract_genshi(fileobj, *args, **kw)
    else:
        # jinja2
        output = jinja2_cleaner(fileobj, *args, **kw)
    # we've eaten the file so we need to get back to the start
    fileobj.seek(0)
    return output
