# encoding: utf-8

from ckan.plugins.toolkit import missing, Invalid, _  # (canada fork only): field name validator
from ckanext.datastore.helpers import is_valid_field_name  # (canada fork only): field name validator


def to_datastore_plugin_data(plugin_key):
    """
    Return a validator that will move values from data to
    context['plugin_data'][field_index][plugin_key][field_name]

    where field_index is the field number, plugin_key (passed to this
    function) is typically set to the plugin name and field name is the
    original field name being validated.
    """

    def validator(key, data, errors, context):
        value = data.pop(key)
        field_index = key[-2]
        field_name = key[-1]
        context['plugin_data'].setdefault(
            field_index, {}).setdefault(
            plugin_key, {})[field_name] = value
    return validator


def datastore_default_current(key, data, errors, context):
    '''default to currently stored value if empty or missing'''
    value = data[key]
    if value is not None and value != '' and value is not missing:
        return
    field_index = key[-2]
    field_name = key[-1]
    # current values for plugin_data are available as
    # context['plugin_data'][field_index]['_current']
    current = context['plugin_data'].get(field_index, {}).get(
        '_current', {}).get('example_idatadictionaryform', {}).get(
        field_name)
    if current:
        data[key] = current


# (canada fork only): field name validator
# TODO:: upstream contrib??
def datastore_field_name(value, context):
    """
    Check if the field name is valid
    """
    if not is_valid_field_name(value):
        raise Invalid(_("Invalid value for a datastore field name."))
    return value
