# encoding: utf-8
from __future__ import annotations

import collections
import datetime
from itertools import count
import re
import mimetypes
import string
import json
from typing import Any, Container, Optional, Union

from urllib.parse import urlparse

import ckan.lib.navl.dictization_functions as df
import ckan.logic as logic
import ckan.logic.converters as converters
import ckan.lib.helpers as h
from ckan.model import (MAX_TAG_LENGTH, MIN_TAG_LENGTH,
                        PACKAGE_NAME_MIN_LENGTH, PACKAGE_NAME_MAX_LENGTH,
                        PACKAGE_VERSION_MAX_LENGTH,
                        VOCABULARY_NAME_MAX_LENGTH,
                        VOCABULARY_NAME_MIN_LENGTH)
import ckan.authz as authz
from ckan.model.core import State

from ckan.common import _
from ckan.types import (
    FlattenDataDict, FlattenKey, Validator, Context, FlattenErrorDict)

Invalid = df.Invalid
StopOnError = df.StopOnError
Missing = df.Missing
missing = df.missing


def owner_org_validator(key: FlattenKey, data: FlattenDataDict,
                        errors: FlattenErrorDict, context: Context) -> Any:
    """Validate organization for the dataset.

    Depending on the settings and user's permissions, this validator checks
    whether organization is optional and ensures that specified organization
    can be set as an owner of dataset.

    """
    value = data.get(key)

    if value is missing or value is None:
        if not authz.check_config_permission('create_unowned_dataset'):
            raise Invalid(_('An organization must be provided'))
        data.pop(key, None)
        raise df.StopOnError

    model = context['model']
    user = model.User.get(context['user'])
    package = context.get('package')

    if value == '':
        if not authz.check_config_permission('create_unowned_dataset'):
            raise Invalid(_('An organization must be provided'))
        return

    if (authz.check_config_permission('allow_dataset_collaborators')
            and not authz.check_config_permission('allow_collaborators_to_change_owner_org')):

        if package and user and not user.sysadmin:
            is_collaborator = authz.user_is_collaborator_on_dataset(
                user.id, package.id, ['admin', 'editor'])
            if is_collaborator:
                # User is a collaborator, check if it's also a member with
                # edit rights of the current organization (redundant, but possible)
                user_orgs = logic.get_action(
                    'organization_list_for_user')(
                        {'ignore_auth': True}, {'id': user.id, 'permission': 'update_dataset'})
                user_is_org_member = package.owner_org in [org['id'] for org in user_orgs]
                if data.get(key) != package.owner_org and not user_is_org_member:
                    raise Invalid(_('You cannot move this dataset to another organization'))

    group = model.Group.get(value)
    if not group:
        raise Invalid(_('Organization does not exist'))
    group_id = group.id

    if not package or (package and package.owner_org != group_id):
        # This is a new dataset or we are changing the organization
        if not context.get(u'ignore_auth', False) and (not user or not(
                user.sysadmin or authz.has_user_permission_for_group_or_org(
                   group_id, user.name, 'create_dataset'))):
            raise Invalid(_('You cannot add a dataset to this organization'))

    data[key] = group_id


def package_id_not_changed(value: Any, context: Context) -> Any:
    """Ensures that package's ID is not changed during the update.
    """

    package = context.get('package')
    if package and value != package.id:
        raise Invalid('Cannot change value of key from %s to %s. '
                      'This key is read-only' % (package.id, value))
    return value

def int_validator(value: Any, context: Context) -> Any:
    '''
    Return an integer for value, which may be a string in base 10 or
    a numeric type (e.g. int, long, float, Decimal, Fraction). Return
    None for None or empty/all-whitespace string values.

    :raises: ckan.lib.navl.dictization_functions.Invalid for other
        inputs or non-whole values
    '''
    if value is None:
        return None
    if hasattr(value, 'strip') and not value.strip():
        return None

    try:
        whole, part = divmod(value, 1)
    except TypeError:
        try:
            return int(value)
        except (TypeError, ValueError):
            pass
    else:
        if not part:
            try:
                return int(whole)
            except TypeError:
                pass  # complex number: fail like int(complex) does

    raise Invalid(_('Invalid integer'))

def natural_number_validator(value: Any, context: Context) -> Any:
    """Ensures that the value is non-negative integer.
    """
    value = int_validator(value, context)
    if value < 0:
        raise Invalid(_('Must be a natural number'))
    return value

def is_positive_integer(value: Any, context: Context) -> Any:
    """Ensures that the value is an integer that is greater than zero.
    """
    value = int_validator(value, context)
    if value < 1:
        raise Invalid(_('Must be a positive integer'))
    return value

def datetime_from_timestamp_validator(value: Any, context: Context) -> Any:
    if value is missing or value is None:
        return None
    try:
        value = datetime.datetime.fromtimestamp(float(value))
    except (TypeError, ValueError):
        raise Invalid(_('Must be a float timestamp'))
    return value

def boolean_validator(value: Any, context: Context) -> Any:
    '''
    Return a boolean for value.
    Return value when value is a python bool type.
    Return True for strings 'true', 'yes', 't', 'y', and '1'.
    Return False in all other cases, including when value is an empty string or
    None
    '''
    if value is missing or value is None:
        return False
    if isinstance(value, bool):
        return value
    if value.lower() in ['true', 'yes', 't', 'y', '1']:
        return True
    return False

def isodate(value: Any, context: Context) -> Any:
    """Convert the value into ``datetime.datetime`` object.
    """
    if isinstance(value, datetime.datetime):
        return value
    if value == '':
        return None
    try:
        date = h.date_str_to_datetime(value)
    except (TypeError, ValueError):
        raise Invalid(_('Date format incorrect'))
    return date

def package_id_exists(value: str, context: Context) -> Any:
    """Ensures that the value is an existing package's ID or name.
    """
    model = context['model']
    session = context['session']

    result = session.query(model.Package).get(value)
    if not result:
        raise Invalid('%s: %s' % (_('Not found'), _('Dataset')))
    return value

def package_id_does_not_exist(value: str, context: Context) -> Any:
    """Ensures that the value is not used as a package's ID or name.
    """

    model = context['model']
    session = context['session']

    result = session.query(model.Package).get(value)
    if result:
        raise Invalid(_('Dataset id already exists'))
    return value

def package_name_exists(value: str, context: Context) -> Any:
    """Ensures that the value is an existing package's name.
    """

    model = context['model']
    session = context['session']

    result = session.query(model.Package).filter_by(name=value).first()

    if not result:
        raise Invalid(_('Not found') + ': %s' % value)
    return value

def package_id_or_name_exists(
        package_id_or_name: str, context: Context) -> Any:
    '''Return the given package_id_or_name if such a package exists.

    :raises: ckan.lib.navl.dictization_functions.Invalid if there is no
        package with the given id or name

    '''
    model = context['model']
    session = context['session']

    result = session.query(model.Package).get(package_id_or_name)
    if result:
        return package_id_or_name

    result = session.query(model.Package).filter_by(
            name=package_id_or_name).first()

    if not result:
        raise Invalid('%s: %s' % (_('Not found'), _('Dataset')))

    return package_id_or_name


def resource_id_exists(value: Any, context: Context) -> Any:
    """Ensures that the value is not used as a resource's ID or name.
    """

    model = context['model']
    session = context['session']
    if not session.query(model.Resource).get(value):
        raise Invalid('%s: %s' % (_('Not found'), _('Resource')))
    return value


def user_id_exists(user_id: str, context: Context) -> Any:
    '''Raises Invalid if the given user_id does not exist in the model given
    in the context, otherwise returns the given user_id.

    '''
    model = context['model']
    session = context['session']

    result = session.query(model.User).get(user_id)
    if not result:
        raise Invalid('%s: %s' % (_('Not found'), _('User')))
    return user_id

def user_id_or_name_exists(user_id_or_name: str, context: Context) -> Any:
    '''Return the given user_id_or_name if such a user exists.

    :raises: ckan.lib.navl.dictization_functions.Invalid if no user can be
        found with the given id or user name

    '''
    model = context['model']
    session = context['session']
    result = session.query(model.User).get(user_id_or_name)
    if result:
        return user_id_or_name
    result = session.query(model.User).filter_by(name=user_id_or_name).first()
    if not result:
        raise Invalid('%s: %s' % (_('Not found'), _('User')))
    return user_id_or_name

def group_id_exists(group_id: str, context: Context) -> Any:
    '''Raises Invalid if the given group_id does not exist in the model given
    in the context, otherwise returns the given group_id.

    '''
    model = context['model']
    session = context['session']

    result = session.query(model.Group).get(group_id)
    if not result:
        raise Invalid('%s: %s' % (_('Not found'), _('Group')))
    return group_id

def group_id_or_name_exists(reference: str, context: Context) -> Any:
    '''
    Raises Invalid if a group identified by the name or id cannot be found.
    '''
    model = context['model']
    result = model.Group.get(reference)
    if not result:
        raise Invalid(_('That group name or ID does not exist.'))
    return reference


name_match = re.compile(r'[a-z0-9_\-]*$')
def name_validator(value: Any, context: Context) -> Any:
    '''Return the given value if it's a valid name, otherwise raise Invalid.

    If it's a valid name, the given value will be returned unmodified.

    This function applies general validation rules for names of packages,
    groups, users, etc.

    Most schemas also have their own custom name validator function to apply
    custom validation rules after this function, for example a
    ``package_name_validator()`` to check that no package with the given name
    already exists.

    :raises ckan.lib.navl.dictization_functions.Invalid: if ``value`` is not
        a valid name

    '''
    if not isinstance(value, str):
        raise Invalid(_('Names must be strings'))

    # check basic textual rules
    if value in ['new', 'edit', 'search']:
        raise Invalid(_('That name cannot be used'))

    if len(value) < 2:
        raise Invalid(_('Must be at least %s characters long') % 2)
    if len(value) > PACKAGE_NAME_MAX_LENGTH:
        raise Invalid(_('Name must be a maximum of %i characters long') % \
                      PACKAGE_NAME_MAX_LENGTH)
    if not name_match.match(value):
        raise Invalid(_('Must be purely lowercase alphanumeric '
                        '(ascii) characters and these symbols: -_'))
    return value


def package_name_validator(key: FlattenKey, data: FlattenDataDict,
                           errors: FlattenErrorDict, context: Context) -> Any:
    """Ensures that value can be used as a package's name
    """
    model = context['model']
    session = context['session']
    package = context.get('package')

    query = session.query(model.Package.id).filter(
        model.Package.name == data[key],
        model.Package.state != State.DELETED,
    )
    if package:
        package_id: Union[Optional[str], Missing] = package.id
    else:
        package_id = data.get(key[:-1] + ('id',))
    if package_id and package_id is not missing:
        query = query.filter(model.Package.id != package_id)

    if session.query(query.exists()).scalar():
        errors[key].append(_('That URL is already in use.'))

    value = data[key]
    if len(value) < PACKAGE_NAME_MIN_LENGTH:
        raise Invalid(
            _('Name "%s" length is less than minimum %s') % (value, PACKAGE_NAME_MIN_LENGTH)
        )
    if len(value) > PACKAGE_NAME_MAX_LENGTH:
        raise Invalid(
            _('Name "%s" length is more than maximum %s') % (value, PACKAGE_NAME_MAX_LENGTH)
        )

def package_version_validator(value: Any, context: Context) -> Any:
    """Ensures that value can be used as a package's version
    """

    if len(value) > PACKAGE_VERSION_MAX_LENGTH:
        raise Invalid(_('Version must be a maximum of %i characters long') % \
                      PACKAGE_VERSION_MAX_LENGTH)
    return value


def duplicate_extras_key(key: FlattenKey, data: FlattenDataDict,
                         errors: FlattenErrorDict, context: Context) -> Any:
    """Ensures that there are no duplicated extras.
    """

    unflattened = df.unflatten(data)
    extras = unflattened.get('extras', [])
    extras_keys = []
    for extra in extras:
        if not extra.get('deleted'):
            extras_keys.append(extra['key'])

    for extra_key in set(extras_keys):
        extras_keys.remove(extra_key)
    if extras_keys:
        key_ = ('extras_validation',)
        assert key_ not in errors
        errors[key_] = [_('Duplicate key "%s"') % extras_keys[0]]


def group_name_validator(key: FlattenKey, data: FlattenDataDict,
                         errors: FlattenErrorDict, context: Context) -> Any:
    """Ensures that value can be used as a group's name
    """

    model = context['model']
    session = context['session']
    group = context.get('group')

    query = session.query(model.Group.name).filter_by(name=data[key])
    if group:
        group_id: Union[Optional[str], Missing] = group.id
    else:
        group_id = data.get(key[:-1] + ('id',))
    if group_id and group_id is not missing:
        query = query.filter(model.Group.id != group_id)
    result = query.first()
    if result:
        errors[key].append(_('Group name already exists in database'))

def tag_length_validator(value: Any, context: Context) -> Any:
    """Ensures that tag length is in the acceptable range.
    """
    if len(value) < MIN_TAG_LENGTH:
        raise Invalid(
            _('Tag "%s" length is less than minimum %s') % (value, MIN_TAG_LENGTH)
        )
    if len(value) > MAX_TAG_LENGTH:
        raise Invalid(
            _('Tag "%s" length is more than maximum %i') % (value, MAX_TAG_LENGTH)
        )
    return value

def tag_name_validator(value: Any, context: Context) -> Any:
    """Ensures that tag does not contain wrong characters
    """
    tagname_match = re.compile(r'[\w \-.]*$', re.UNICODE)
    if not tagname_match.match(value):
        raise Invalid(_('Tag "%s" can only contain alphanumeric '
                        'characters, spaces (" "), hyphens ("-"), '
                        'underscores ("_") or dots (".")') % (value))
    return value

def tag_not_uppercase(value: Any, context: Context) -> Any:
    """Ensures that tag is lower-cased.
    """
    tagname_uppercase = re.compile('[A-Z]')
    if tagname_uppercase.search(value):
        raise Invalid(_('Tag "%s" must not be uppercase' % (value)))
    return value


def tag_string_convert(key: FlattenKey, data: FlattenDataDict,
                       errors: FlattenErrorDict, context: Context) -> Any:
    '''Takes a list of tags that is a comma-separated string (in data[key])
    and parses tag names. These are added to the data dict, enumerated. They
    are also validated.'''

    if isinstance(data[key], str):
        tags = [tag.strip() \
                for tag in data[key].split(',') \
                if tag.strip()]
    else:
        tags = data[key]

    current_index = max( [int(k[1]) for k in data.keys() if len(k) == 3 and k[0] == 'tags'] + [-1] )

    for num, tag in zip(count(current_index+1), tags):
        data[('tags', num, 'name')] = tag

    for tag in tags:
        tag_length_validator(tag, context)
        tag_name_validator(tag, context)


def ignore_not_package_admin(key: FlattenKey, data: FlattenDataDict,
                             errors: FlattenErrorDict,
                             context: Context) -> Any:
    '''Ignore if the user is not allowed to administer the package specified.'''

    user = context.get('user')

    if 'ignore_auth' in context:
        return

    if user and authz.is_sysadmin(user):
        return

    authorized = False
    pkg = context.get('package')
    if pkg:
        try:
            logic.check_access('package_change_state',context)
            authorized = True
        except logic.NotAuthorized:
            authorized = False

    if (user and pkg and authorized):
        return

    # allow_state_change in the context will allow the state to be changed
    # FIXME is this the best way to cjeck for state only?
    if key == ('state',) and context.get('allow_state_change'):
        return
    data.pop(key)


def ignore_not_sysadmin(key: FlattenKey, data: FlattenDataDict,
                        errors: FlattenErrorDict, context: Context) -> Any:
    '''Ignore the field if user not sysadmin or ignore_auth in context.'''

    user = context.get('user')
    ignore_auth = context.get('ignore_auth')
    if ignore_auth or (user and authz.is_sysadmin(user)):
        return

    data.pop(key)


def ignore_not_group_admin(key: FlattenKey, data: FlattenDataDict,
                           errors: FlattenErrorDict, context: Context) -> Any:
    '''Ignore if the user is not allowed to administer for the group specified.'''

    user = context.get('user')

    if user and authz.is_sysadmin(user):
        return

    authorized = False
    group = context.get('group')
    if group:
        try:
            logic.check_access('group_change_state',context)
            authorized = True
        except logic.NotAuthorized:
            authorized = False

    if (user and group and authorized):
        return

    data.pop(key)


def user_name_validator(key: FlattenKey, data: FlattenDataDict,
                        errors: FlattenErrorDict, context: Context) -> Any:
    '''Validate a new user name.

    Append an error message to ``errors[key]`` if a user named ``data[key]``
    already exists. Otherwise, do nothing.

    :raises ckan.lib.navl.dictization_functions.Invalid: if ``data[key]`` is
        not a string
    :rtype: None

    '''
    model = context['model']
    new_user_name = data[key]

    if not isinstance(new_user_name, str):
        raise Invalid(_('User names must be strings'))

    user = model.User.get(new_user_name)
    user_obj_from_context = context.get('user_obj')
    if user is not None:
        # A user with new_user_name already exists in the database.
        if user_obj_from_context and user_obj_from_context.id == user.id:
            # If there's a user_obj in context with the same id as the user
            # found in the db, then we must be doing a user_update and not
            # updating the user name, so don't return an error.
            return
        else:
            # Otherwise return an error: there's already another user with that
            # name, so you can create a new user with that name or update an
            # existing user's name to that name.
            errors[key].append(_('That login name is not available.'))
    elif user_obj_from_context:
        old_user = model.User.get(user_obj_from_context.id)
        if old_user is not None and old_user.state != model.State.PENDING:
            errors[key].append(_('That login name can not be modified.'))
        else:
            return


def user_both_passwords_entered(key: FlattenKey, data: FlattenDataDict,
                                errors: FlattenErrorDict,
                                context: Context) -> Any:
    """Ensures that both password and password confirmation is not empty
    """
    password1 = data.get(('password1',),None)
    password2 = data.get(('password2',),None)

    if password1 is None or password1 == '' or \
       password2 is None or password2 == '':
        errors[('password',)].append(_('Please enter both passwords'))


def user_password_validator(key: FlattenKey, data: FlattenDataDict,
                            errors: FlattenErrorDict,
                            context: Context) -> Any:
    """Ensures that password is safe enough.
    """
    value = data[key]

    if isinstance(value, Missing):
        pass
    elif not isinstance(value, str):
        errors[('password',)].append(_('Passwords must be strings'))
    elif value == '':
        pass
    elif len(value) < 8:
        errors[('password',)].append(_('Your password must be 8 characters or '
                                       'longer'))


def user_passwords_match(key: FlattenKey, data: FlattenDataDict,
                         errors: FlattenErrorDict, context: Context) -> Any:
    """Ensures that password and password confirmation match.
    """
    password1 = data.get(('password1',),None)
    password2 = data.get(('password2',),None)

    if not password1 == password2:
        errors[key].append(_('The passwords you entered do not match'))
    else:
        #Set correct password
        data[('password',)] = password1


def user_password_not_empty(key: FlattenKey, data: FlattenDataDict,
                            errors: FlattenErrorDict,
                            context: Context) -> Any:
    '''Only check if password is present if the user is created via action API.
       If not, user_both_passwords_entered will handle the validation'''
    # sysadmin may provide password_hash directly for importing users
    if (data.get(('password_hash',), missing) is not missing and
            authz.is_sysadmin(context.get('user'))):
        return

    if not ('password1',) in data and not ('password2',) in data:
        password = data.get(('password',),None)
        if not password:
            errors[key].append(_('Missing value'))

def user_about_validator(value: Any,context: Context) -> Any:
    """Ensures that user's ``about`` field does not contains links.
    """
    if 'http://' in value or 'https://' in value:
        raise Invalid(_('Edit not allowed as it looks like spam. Please avoid links in your description.'))

    return value

def vocabulary_name_validator(name: str, context: Context) -> Any:
    """Ensures that the value can be used as a tag vocabulary name.
    """
    model = context['model']
    session = context['session']

    if len(name) < VOCABULARY_NAME_MIN_LENGTH:
        raise Invalid(_('Name must be at least %s characters long') %
            VOCABULARY_NAME_MIN_LENGTH)
    if len(name) > VOCABULARY_NAME_MAX_LENGTH:
        raise Invalid(_('Name must be a maximum of %i characters long') %
                      VOCABULARY_NAME_MAX_LENGTH)
    query = session.query(model.Vocabulary.name).filter_by(name=name)
    result = query.first()
    if result:
        raise Invalid(_('That vocabulary name is already in use.'))
    return name

def vocabulary_id_not_changed(value: Any, context: Context) -> Any:
    """Ensures that vocabulary ID is not changed during the update.
    """
    vocabulary = context.get('vocabulary')
    if vocabulary and value != vocabulary.id:
        raise Invalid(_('Cannot change value of key from %s to %s. '
                        'This key is read-only') % (vocabulary.id, value))
    return value

def vocabulary_id_exists(value: Any, context: Context) -> Any:
    """Ensures that value contains existing vocabulary's ID or name.
    """
    model = context['model']
    session = context['session']
    result = session.query(model.Vocabulary).get(value)
    if not result:
        raise Invalid(_('Tag vocabulary was not found.'))
    return value

def tag_in_vocabulary_validator(value: Any, context: Context) -> Any:
    """Ensures that the tag belongs to the vocabulary.
    """
    model = context['model']
    session = context['session']
    vocabulary = context.get('vocabulary')
    if vocabulary:
        query = session.query(model.Tag)\
            .filter(model.Tag.vocabulary_id==vocabulary.id)\
            .filter(model.Tag.name==value)\
            .count()
        if not query:
            raise Invalid(_('Tag %s does not belong to vocabulary %s') % (value, vocabulary.name))
    return value


def tag_not_in_vocabulary(key: FlattenKey, tag_dict: FlattenDataDict,
                          errors: FlattenErrorDict, context: Context) -> Any:
    """Ensures that the tag does not belong to the vocabulary.
    """
    tag_name = tag_dict[('name',)]
    if not tag_name:
        raise Invalid(_('No tag name'))
    if ('vocabulary_id',) in tag_dict:
        vocabulary_id = tag_dict[('vocabulary_id',)]
    else:
        vocabulary_id = None
    model = context['model']
    session = context['session']

    query = session.query(model.Tag)
    query = query.filter(model.Tag.vocabulary_id==vocabulary_id)
    query = query.filter(model.Tag.name==tag_name)
    count = query.count()
    if count > 0:
        raise Invalid(_('Tag %s already belongs to vocabulary %s') %
                (tag_name, vocabulary_id))
    else:
        return


def url_validator(key: FlattenKey, data: FlattenDataDict,
                  errors: FlattenErrorDict, context: Context) -> Any:
    ''' Checks that the provided value (if it is present) is a valid URL '''

    url = data.get(key, None)
    if not url:
        return

    try:
        pieces = urlparse(url)
        if all([pieces.scheme, pieces.netloc]) and \
           set(pieces.netloc) <= set(string.ascii_letters + string.digits + '-.') and \
           pieces.scheme in ['http', 'https']:
            return
    except ValueError:
        # url is invalid
        pass

    errors[key].append(_('Please provide a valid URL'))


def user_name_exists(user_name: str, context: Context) -> Any:
    """Ensures that user's name exists.
    """
    model = context['model']
    session = context['session']
    result = session.query(model.User).filter_by(name=user_name).first()
    if not result:
        raise Invalid('%s: %s' % (_('Not found'), _('User')))
    return result.name


def role_exists(role: str, context: Context) -> Any:
    """Ensures that value is an existing CKAN Role name.
    """
    if role not in authz.ROLE_PERMISSIONS:
        raise Invalid(_('role does not exist.'))
    return role


def datasets_with_no_organization_cannot_be_private(key: FlattenKey,
                                                    data: FlattenDataDict,
                                                    errors: FlattenErrorDict,
                                                    context: Context) -> Any:

    dataset_id = data.get(('id',))
    owner_org = data.get(('owner_org',))
    private = data[key] is True

    check_passed = True

    if not dataset_id and private and not owner_org:
        # When creating a dataset, enforce it directly
        check_passed = False
    elif dataset_id and private and not owner_org:
        # Check if the dataset actually has an owner_org, even if not provided
        try:
            dataset_dict = logic.get_action('package_show')({},
                            {'id': dataset_id})
            if not dataset_dict.get('owner_org'):
                check_passed = False

        except logic.NotFound:
            check_passed = False

    if not check_passed:
        errors[key].append(
                _("Datasets with no organization can't be private."))


def list_of_strings(key: FlattenKey, data: FlattenDataDict,
                    errors: FlattenErrorDict, context: Context) -> Any:
    """Ensures that value is a list of strings.
    """
    value = data.get(key)
    if not isinstance(value, list):
        raise Invalid(_('Not a list'))
    for x in value:
        if not isinstance(x, str):
            raise Invalid('%s: %s' % (_('Not a string'), x))


def if_empty_guess_format(key: FlattenKey, data: FlattenDataDict,
                          errors: FlattenErrorDict, context: Context) -> Any:
    """Make an attempt to guess resource's format using URL.
    """
    value = data[key]
    resource_id = data.get(key[:-1] + ('id',))

    # if resource_id then an update
    if (not value or value is Missing) and not resource_id:
        url = data.get(key[:-1] + ('url',), '')
        if not url:
            return

        # Uploaded files have only the filename as url, so check scheme to
        # determine if it's an actual url
        parsed = urlparse(url)
        if parsed.scheme and not parsed.path:
            return

        mimetype, _encoding = mimetypes.guess_type(url)
        if mimetype:
            data[key] = mimetype

def clean_format(format: str):
    """Normalize resource's format.
    """
    return h.unified_resource_format(format)


def no_loops_in_hierarchy(key: FlattenKey, data: FlattenDataDict,
                          errors: FlattenErrorDict, context: Context) -> Any:
    '''Checks that the parent groups specified in the data would not cause
    a loop in the group hierarchy, and therefore cause the recursion up/down
    the hierarchy to get into an infinite loop.
    '''
    if not ('id',) in data:
        # Must be a new group - has no children, so no chance of loops
        return
    group = context['model'].Group.get(data[('id',)])
    assert group
    allowable_parents = group.groups_allowed_to_be_its_parent(type=group.type)
    parent_name = data[key]
    # a blank name signifies top level, which is always allowed
    if parent_name and context['model'].Group.get(parent_name) \
            not in allowable_parents:
        raise Invalid(_('This parent would create a loop in the '
                        'hierarchy'))


def filter_fields_and_values_should_have_same_length(key: FlattenKey,
                                                     data: FlattenDataDict,
                                                     errors: FlattenErrorDict,
                                                     context: Context) -> Any:
    convert_to_list_if_string = converters.convert_to_list_if_string
    fields = convert_to_list_if_string(data.get(('filter_fields',), []))
    values = convert_to_list_if_string(data.get(('filter_values',), []))

    if len(fields) != len(values):
        msg = _('"filter_fields" and "filter_values" should have the same length')
        errors[('filter_fields',)].append(msg)
        errors[('filter_values',)].append(msg)


def filter_fields_and_values_exist_and_are_valid(key: FlattenKey,
                                                 data: FlattenDataDict,
                                                 errors: FlattenErrorDict,
                                                 context: Context) -> Any:
    convert_to_list_if_string = converters.convert_to_list_if_string
    fields = convert_to_list_if_string(data.get(('filter_fields',)))
    values = convert_to_list_if_string(data.get(('filter_values',)))

    if not fields:
        errors[('filter_fields',)].append(_('"filter_fields" is required when '
                                            '"filter_values" is filled'))
    if not values:
        errors[('filter_values',)].append(_('"filter_values" is required when '
                                            '"filter_fields" is filled'))

    filters = collections.defaultdict(list)
    for field, value in zip(fields, values):
        filters[field].append(value)

    data[('filters',)] = dict(filters)


def extra_key_not_in_root_schema(key: FlattenKey, data: FlattenDataDict,
                                 errors: FlattenErrorDict,
                                 context: Context) -> Any:
    """Ensures that extras are not duplicating base fields
    """
    for schema_key in context.get('schema_keys', []):
        if schema_key == data[key]:
            raise Invalid(_('There is a schema field with the same name'))


def empty_if_not_sysadmin(key: FlattenKey, data: FlattenDataDict,
                          errors: FlattenErrorDict, context: Context) -> Any:
    '''Only sysadmins may pass this value'''
    from ckan.lib.navl.validators import empty

    user = context.get('user')

    ignore_auth = context.get('ignore_auth')
    if ignore_auth or (user and authz.is_sysadmin(user)):
        return

    empty(key, data, errors, context)

#pattern from https://html.spec.whatwg.org/#e-mail-state-(type=email)
email_pattern = re.compile(
                            # additional pattern to reject malformed dots usage
                            r"^(?!\.)(?!.*\.$)(?!.*?\.\.)"\
                            r"[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9]"\
                            r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9]"\
                            r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
                        )


def strip_value(value: str):
    '''Trims the Whitespace'''
    return value.strip()


def email_validator(value: Any, context: Context) -> Any:
    '''Validate email input '''

    if value:
        if not email_pattern.match(value):
            raise Invalid(_('Email {email} is not a valid format').format(email=value))
    return value

def collect_prefix_validate(prefix: str, *validator_names: str) -> Validator:
    """
    Return a validator that will collect top-level keys starting with
    prefix then apply validator_names to each one. Results are moved
    to a dict under the prefix name, with prefix removed from keys
    """
    validator_fns = [logic.get_validator(v) for v in validator_names]

    def prefix_validator(key: FlattenKey, data: FlattenDataDict,
                         errors: FlattenErrorDict, context: Context):
        out = {}
        extras = data.get(('__extras',), {})

        # values passed as lists of dicts will have been flattened into __junk
        junk = df.unflatten(data.get(('__junk',), {}))
        for field_name in junk:
            if not field_name.startswith(prefix):
                continue
            extras[field_name] = junk[field_name]

        for field_name in list(extras):
            if not field_name.startswith(prefix):
                continue
            data[(field_name,)] = extras.pop(field_name)
            for v in validator_fns:
                try:
                    df.convert(v, (field_name,), data, errors, context)
                except df.StopOnError:
                    break
            out[field_name[len(prefix):]] = data.pop((field_name,))

        data[(prefix,)] = out

    return prefix_validator


def dict_only(value: Any) -> dict[Any, Any]:
    """Ensures that the value is a dictionary
    """
    if not isinstance(value, dict):
        raise Invalid(_('Must be a dict'))
    return value


def email_is_unique(key: FlattenKey, data: FlattenDataDict,
                    errors: FlattenErrorDict, context: Context) -> Any:
    '''Validate email is unique'''
    model = context['model']
    session = context['session']

    users = session.query(model.User) \
        .filter(model.User.email == data[key]) \
        .filter(model.User.state == 'active').all()
    # if there are no active users with this email, it's free
    if not users:
        return
    else:
        # allow user to update their own email
        for user in users:
            if (user.name in (data.get(("name",)), data.get(("id",)))
                    or user.id == data.get(("id",))):
                return

    raise Invalid(
        _('The email address \'{email}\' belongs to a registered user.').format(email=data[key]))


def one_of(list_of_value: Container[Any]) -> Validator:
    ''' Checks if the provided value is present in a list or is an empty string'''
    def callable(value: Any):
        if value != "" and value not in list_of_value:
            raise Invalid(_('Value must be one of {}'.format(list_of_value)))
        return value
    return callable


def json_object(value: Any) -> Any:
    ''' Make sure value can be serialized as a JSON object'''
    if value is None or value == '':
        return
    try:
        if not json.dumps(value).startswith('{'):
            raise Invalid(_('The value should be a valid JSON object'))
    except ValueError:
        raise Invalid(_('Could not parse the value as a valid JSON object'))

    return value


def extras_valid_json(extras: Any, context: Context) -> Any:
    """Ensures that every item in the value dictionary is JSON-serializable.
    """
    for extra, value in extras.items():
        try:
            json.dumps(value)
        except ValueError:
            raise Invalid(_(u'Could not parse extra \'{name}\' as valid JSON').
                          format(name=extra))
    return extras
