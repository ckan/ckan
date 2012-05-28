import re
from genshi.filters.i18n import extract as extract_genshi
from jinja2.ext import babel_extract as extract_jinja2

def extract_ckan(fileobj, *args, **kw):
    ''' Determine the type of file (Genshi or Jinja2) and then call the
    correct extractor function.

    Basically we just look for a jinja2 {{ or {% tag. '''

    source = fileobj.read()
    if re.search('\{\{|\{\%', source):
        # jinja2
        extractor_function = extract_jinja2
    else:
        # genshi
        extractor_function = extract_genshi
    # we've eaten the file so we need to get back to the start
    fileobj.seek(0)
    return extractor_function(fileobj, *args, **kw)

