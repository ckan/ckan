# encoding: utf-8
from ckan.plugins.toolkit import _, config


def datatablesview_null_label():
    label = config.get('ckan.datatables.null_label')
    return _(label) if label else ''
