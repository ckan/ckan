from pylons.i18n import _
from ckan import model
from ckan.lib.navl.dictization_functions import Invalid
from ckan.lib.field_types import DateType, DateConvertError
from ckan.logic.validators import tag_length_validator, tag_name_validator, \
    tag_in_vocabulary_validator

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

def free_tags_only(key, data, errors, context):
    tag_number = key[1]
    if not data.get(('tags', tag_number, 'vocabulary_id')):
        return
    for k in data.keys():
        if k[0] == 'tags' and k[1] == tag_number:
            del data[k]

def convert_to_tags(vocab):
    def callable(key, data, errors, context):
        new_tags = data.get(key)
        if not new_tags:
            return
        if isinstance(new_tags, basestring):
            new_tags = [new_tags]

        # get current number of tags
        n = 0
        for k in data.keys():
            if k[0] == 'tags':
                n = max(n, k[1] + 1)

        v = model.Vocabulary.get(vocab)
        if not v:
            raise Invalid(_('Tag vocabulary "%s" does not exist') % vocab)
        context['vocabulary'] = v

        for tag in new_tags:
            tag_in_vocabulary_validator(tag, context)

        for num, tag in enumerate(new_tags):
            data[('tags', num + n, 'name')] = tag
            data[('tags', num + n, 'vocabulary_id')] = v.id
    return callable

def convert_from_tags(vocab):
    def callable(key, data, errors, context):
        v = model.Vocabulary.get(vocab)
        if not v:
            raise Invalid(_('Tag vocabulary "%s" does not exist') % vocab)

        tags = []
        for k in data.keys():
            if k[0] == 'tags':
                if data[k].get('vocabulary_id') == v.id:
                    name = data[k].get('display_name', data[k]['name'])
                    tags.append(name)
        data[key] = tags
    return callable

