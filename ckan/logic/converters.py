# encoding: utf-8

import json

import ckan.model as model
import ckan.lib.navl.dictization_functions as df
import ckan.logic.validators as validators

from ckan.common import _


def convert_to_extras(key, data, errors, context):

    # Get the current extras index
    current_indexes = [k[1] for k in data.keys()
                       if len(k) > 1 and k[0] == 'extras']

    new_index = max(current_indexes) + 1 if current_indexes else 0

    data[('extras', new_index, 'key')] = key[-1]
    data[('extras', new_index, 'value')] = data[key]


def convert_from_extras(key, data, errors, context):

    def remove_from_extras(data, key):
        to_remove = []
        for data_key, data_value in data.iteritems():
            if (data_key[0] == 'extras'
                and data_key[1] == key):
                to_remove.append(data_key)
        for item in to_remove:
            del data[item]

    for data_key, data_value in data.iteritems():
        if (data_key[0] == 'extras'
            and data_key[-1] == 'key'
            and data_value == key[-1]):
            data[key] = data[('extras', data_key[1], 'value')]
            break
    else:
        return
    remove_from_extras(data, data_key[1])

def extras_unicode_convert(extras, context):
    for extra in extras:
        extras[extra] = unicode(extras[extra])
    return extras

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
            raise df.Invalid(_('Tag vocabulary "%s" does not exist') % vocab)
        context['vocabulary'] = v

        for tag in new_tags:
            validators.tag_in_vocabulary_validator(tag, context)

        for num, tag in enumerate(new_tags):
            data[('tags', num + n, 'name')] = tag
            data[('tags', num + n, 'vocabulary_id')] = v.id
    return callable

def convert_from_tags(vocab):
    def callable(key, data, errors, context):
        v = model.Vocabulary.get(vocab)
        if not v:
            raise df.Invalid(_('Tag vocabulary "%s" does not exist') % vocab)

        tags = []
        for k in data.keys():
            if k[0] == 'tags':
                if data[k].get('vocabulary_id') == v.id:
                    name = data[k].get('display_name', data[k]['name'])
                    tags.append(name)
        data[key] = tags
    return callable

def convert_user_name_or_id_to_id(user_name_or_id, context):
    '''Return the user id for the given user name or id.

    The point of this function is to convert user names to ids. If you have
    something that may be a user name or a user id you can pass it into this
    function and get the user id out either way.

    Also validates that a user with the given name or id exists.

    :returns: the id of the user with the given user name or id
    :rtype: string
    :raises: ckan.lib.navl.dictization_functions.Invalid if no user can be
        found with the given id or user name

    '''
    session = context['session']
    result = session.query(model.User).filter_by(id=user_name_or_id).first()
    if not result:
        result = session.query(model.User).filter_by(
                name=user_name_or_id).first()
    if not result:
        raise df.Invalid('%s: %s' % (_('Not found'), _('User')))
    return result.id

def convert_package_name_or_id_to_id(package_name_or_id, context):
    '''Return the package id for the given package name or id.

    The point of this function is to convert package names to ids. If you have
    something that may be a package name or id you can pass it into this
    function and get the id out either way.

    Also validates that a package with the given name or id exists.

    :returns: the id of the package with the given name or id
    :rtype: string
    :raises: ckan.lib.navl.dictization_functions.Invalid if there is no
        package with the given name or id

    '''
    session = context['session']
    result = session.query(model.Package).filter_by(
            id=package_name_or_id).first()
    if not result:
        result = session.query(model.Package).filter_by(
                name=package_name_or_id).first()
    if not result:
        raise df.Invalid('%s: %s' % (_('Not found'), _('Dataset')))
    return result.id

def convert_group_name_or_id_to_id(group_name_or_id, context):
    '''Return the group id for the given group name or id.

    The point of this function is to convert group names to ids. If you have
    something that may be a group name or id you can pass it into this
    function and get the id out either way.

    Also validates that a group with the given name or id exists.

    :returns: the id of the group with the given name or id
    :rtype: string
    :raises: ckan.lib.navl.dictization_functions.Invalid if there is no
        group with the given name or id

    '''
    session = context['session']
    result = session.query(model.Group).filter_by(
            id=group_name_or_id).first()
    if not result:
        result = session.query(model.Group).filter_by(
                name=group_name_or_id).first()
    if not result:
        raise df.Invalid('%s: %s' % (_('Not found'), _('Group')))
    return result.id


def convert_to_json_if_string(value, context):
    if isinstance(value, basestring):
        try:
            return json.loads(value)
        except ValueError:
            raise df.Invalid(_('Could not parse as valid JSON'))
    else:
        return value


def convert_to_list_if_string(value, context=None):
    if isinstance(value, basestring):
        return [value]
    else:
        return value


def remove_whitespace(value, context):
    if isinstance(value, basestring):
        return value.strip()
    return value
