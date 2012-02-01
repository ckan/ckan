from ckan import model
from ckan.lib.navl.dictization_functions import Invalid
from ckan.lib.field_types import DateType, DateConvertError
from ckan.logic.validators import tag_length_validator, tag_name_validator

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

def convert_to_tags(vocab):
    def callable(key, data, errors, context):
        tag_string = data.get(key)
        new_tags = [tag.strip() for tag in tag_string.split(',') if tag.strip()]
        if not new_tags:
            return
        # get current number of tags
        n = 0
        for k in data.keys():
            if k[0] == 'tags':
                n = max(n, k[1] + 1)
        # validate
        for tag in new_tags:
            tag_length_validator(tag, context)
            tag_name_validator(tag, context)
        # get the vocab
        v = model.Vocabulary.get(vocab)
        if not v:
            # TODO: raise an exception here
            pass
        # add new tags
        for num, tag in enumerate(new_tags):
            data[('tags', num+n, 'name')] = tag
            data[('tags', num+n, 'vocabulary_id')] = v.id
    return callable

def convert_from_tags(vocab):
    def callable(key, data, errors, context):
        pass
    return callable

