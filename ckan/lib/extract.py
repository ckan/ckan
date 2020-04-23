# encoding: utf-8

from jinja2.ext import babel_extract


# It's no longer needed but all the extensions are using this
# function. Let's keep it, just in case we need to extract messages in
# some special way in future
def extract_ckan(fileobj, *args, **kw):
    if 'options' not in kw:
        kw['options'] = {}
    if 'trimmed' not in kw['options']:
        kw['options']['trimmed'] = 'True'

    return babel_extract(fileobj, *args, **kw)
