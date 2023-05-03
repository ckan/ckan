from ckan.plugins.toolkit import _, config

def datatablesview_null_label():
    return _(config.get('ckan.datatables.null_label', u''))
