import re
from genshi.filters.i18n import extract as extract_genshi
from jinja2.ext import babel_extract as extract_jinja2

def extract_ckan(fileobj, *args, **kw):
    ''' Determine the type of file (Genshi or Jinja2) and then call the
    correct extractor function.

    Basically we just look for genshi.edgewall.org which all genshi XML
    templates should contain. '''

    source = fileobj.read()
    if re.search('genshi\.edgewall\.org', source):
        # genshi
        extractor_function = extract_genshi
    else:
        # jinja2
        extractor_function = extract_jinja2
    # we've eaten the file so we need to get back to the start
    fileobj.seek(0)
    return extractor_function(fileobj, *args, **kw)
