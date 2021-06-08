# encoding: utf-8

from jinja2.ext import babel_extract
from ckan.lib.jinja_extensions import _get_extensions


def extract_ckan(fileobj, *args, **kw):
    extensions = [
        ':'.join([ext.__module__, ext.__name__])
        if isinstance(ext, type)
        else ext
        for ext in _get_extensions()
    ]
    if 'options' not in kw:
        kw['options'] = {}
    if 'trimmed' not in kw['options']:
        kw['options']['trimmed'] = 'True'
    if 'silent' not in kw['options']:
        kw['options']['silent'] = 'False'
    if 'extensions' not in kw['options']:
        kw['options']['extensions'] = ','.join(extensions)

    return babel_extract(fileobj, *args, **kw)
