
from .column_types import _standard_column_types

from ckan.plugins.toolkit import _

def tabledesigner_column_type_options():
    """
    return list of {'name':..., 'value':...} dicts
    with the type name and label for all registered column types
    """
    return [
        {'name': k, 'value': _(v.label)}
        for k,v in _standard_column_types.items()
    ]
