
from .column_types import column_types

from ckan.plugins.toolkit import _

def tabledesigner_column_type_options():
    """
    return list of {'value':..., 'text':...} dicts
    with the type name and label for all registered column types
    """
    return [
        {'value': k, 'text': _(v.label)}
        for k,v in column_types.items()
    ]
