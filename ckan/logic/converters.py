from ckan.lib.navl.dictization_functions import Invalid
from ckan.lib.field_types import DateType, DateConvertError



def convert_to_extras(key, data, errors, context):

    extras = data.get(('extras',), [])
    if not extras:
        data[('extras',)] = extras

    extras.append({'key': key[-1], 'value': data[key]})

def convert_from_extras(key, data, errors, context):

    for data_key, data_value in data.iteritems():
        if (data_key[0] == 'extras'
            and data_key[-1] == 'key'
            and data_value == key[-1]):
            data[key] = data[('extras', data_key[1], 'value')]

def date_to_db(value, context):
    try:
        value = DateType.form_to_db(value)
    except DateConvertError, e:
        raise Invalid(str(e))
    return value

def date_to_form(value, context):
    try:
        value = DateType.db_to_form(value)
    except DateConvertError, e:
        raise Invalid(str(e))
    return value

