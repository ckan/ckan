from .column_types import column_types

from ckan.plugins.toolkit import _


def tabledesigner_column_type_options():
    """
    return list of {'value':..., 'text':...} dicts
    with the type name and label for all registered column types
    """
    return [{"value": k, "text": _(v.label)} for k, v in column_types.items()]

def tabledesigner_column_type(tdtype):
    """
    return column type object (fall back to text if not found)
    """
    return column_types.get(tdtype, column_types['text'])

def tabledesigner_choice_list(choices):
    """
    convert choices string to choice list, ignoring surrounding whitespace
    """
    return [c.strip() for c in choices.split(',')]

def tabledesigner_data_api_examples(resource_id):
    return {
        "text_column_filters_object": {
            "subject": ["watershed", "survey"],
            "stage": "active",
        },
        "text_column_name_sql": "title",
        "insert_record_object": {
            "subject": "watershed",
            "stage": "active",
        },
        "update_record_object": {
            "_id": 1,
            "subject": "survey",
            "stage": "inactive",
        },
        "unique_filter_object": {"_id": 1},
    }
