# encoding: utf-8

import collections
import datetime
from itertools import count
import re
import mimetypes

from six import string_types

import ckan.lib.navl.dictization_functions as df
import ckan.logic as logic
import ckan.lib.helpers as h
from ckan.model import (MAX_TAG_LENGTH, MIN_TAG_LENGTH,
                        PACKAGE_NAME_MIN_LENGTH, PACKAGE_NAME_MAX_LENGTH,
                        PACKAGE_VERSION_MAX_LENGTH,
                        VOCABULARY_NAME_MAX_LENGTH,
                        VOCABULARY_NAME_MIN_LENGTH)
import ckan.authz as authz
from ckan.model.core import State

from ckan.common import _

Invalid = df.Invalid
StopOnError = df.StopOnError
Missing = df.Missing
missing = df.missing

def owner_org_validator(key, data, errors, context):

    value = data.get(key)

    if value is missing or value is None:
        if not authz.check_config_permission('create_unowned_dataset'):
            raise Invalid(_('An organization must be provided'))
        data.pop(key, None)
        raise df.StopOnError

    model = context['model']
    user = context['user']
    user = model.User.get(user)
    if value == '':
        if not authz.check_config_permission('create_unowned_dataset'):
            raise Invalid(_('An organization must be provided'))
        return

    group = model.Group.get(value)
    if not group:
        raise Invalid(_('Organization does not exist'))
    group_id = group.id
    if not context.get(u'ignore_auth', False) and not(user.sysadmin or
           authz.has_user_permission_for_group_or_org(
               group_id, user.name, 'create_dataset')):
        raise Invalid(_('You cannot add a dataset to this organization'))
    data[key] = group_id


def package_id_not_changed(value, context):

    package = context.get('package')
    if package and value != package.id:
        raise Invalid('Cannot change value of key from %s to %s. '
                      'This key is read-only' % (package.id, value))
    return value

def int_validator(value, context):
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
        except ValueError:
            pass
    else:
        if not part:
            try:
                return int(whole)
            except TypeError:
                pass  # complex number: fail like int(complex) does

    raise Invalid(_('Invalid integer'))

def natural_number_validator(value, context):
    value = int_validator(value, context)
    if value < 0:
        raise Invalid(_('Must be a natural number'))
    return value

def is_positive_integer(value, context):
    value = int_validator(value, context)
    if value < 1:
        raise Invalid(_('Must be a postive integer'))
    return value

def boolean_validator(value, context):
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

def isodate(value, context):
    if isinstance(value, datetime.datetime):
        return value
    if value == '':
        return None
    try:
        date = h.date_str_to_datetime(value)
    except (TypeError, ValueError) as e:
        raise Invalid(_('Date format incorrect'))
    return date

def no_http(value, context):

    model = context['model']
    session = context['session']

    if 'http:' in value:
        raise Invalid(_('No links are allowed in the log_message.'))
    return value

def package_id_exists(value, context):

    model = context['model']
    session = context['session']

    result = session.query(model.Package).get(value)
    if not result:
        raise Invalid('%s: %s' % (_('Not found'), _('Dataset')))
    return value

def package_id_does_not_exist(value, context):

    model = context['model']
    session = context['session']

    result = session.query(model.Package).get(value)
    if result:
        raise Invalid(_('Dataset id already exists'))
    return value

def package_name_exists(value, context):

    model = context['model']
    session = context['session']

    result = session.query(model.Package).filter_by(name=value).first()

    if not result:
        raise Invalid(_('Not found') + ': %s' % value)
    return value

def package_id_or_name_exists(package_id_or_name, context):
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


def resource_id_exists(value, context):
    model = context['model']
    session = context['session']
    if not session.query(model.Resource).get(value):
        raise Invalid('%s: %s' % (_('Not found'), _('Resource')))
    return value


def user_id_exists(user_id, context):
    '''Raises Invalid if the given user_id does not exist in the model given
    in the context, otherwise returns the given user_id.

    '''
    model = context['model']
    session = context['session']

    result = session.query(model.User).get(user_id)
    if not result:
        raise Invalid('%s: %s' % (_('Not found'), _('User')))
    return user_id

def user_id_or_name_exists(user_id_or_name, context):
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

def group_id_exists(group_id, context):
    '''Raises Invalid if the given group_id does not exist in the model given
    in the context, otherwise returns the given group_id.

    '''
    model = context['model']
    session = context['session']

    result = session.query(model.Group).get(group_id)
    if not result:
        raise Invalid('%s: %s' % (_('Not found'), _('Group')))
    return group_id

def group_id_or_name_exists(reference, context):
    '''
    Raises Invalid if a group identified by the name or id cannot be found.
    '''
    model = context['model']
    result = model.Group.get(reference)
    if not result:
        raise Invalid(_('That group name or ID does not exist.'))
    return reference

def activity_type_exists(activity_type):
    '''Raises Invalid if there is no registered activity renderer for the
    given activity_type. Otherwise returns the given activity_type.

    This just uses object_id_validators as a lookup.
    very safe.

    '''
    if activity_type in object_id_validators:
        return activity_type
    else:
        raise Invalid('%s: %s' % (_('Not found'), _('Activity type')))


# A dictionary mapping activity_type values from activity dicts to functions
# for validating the object_id values from those same activity dicts.
object_id_validators = {
    'new package' : package_id_exists,
    'changed package' : package_id_exists,
    'deleted package' : package_id_exists,
    'follow dataset' : package_id_exists,
    'new user' : user_id_exists,
    'changed user' : user_id_exists,
    'follow user' : user_id_exists,
    'new group' : group_id_exists,
    'changed group' : group_id_exists,
    'deleted group' : group_id_exists,
    'new organization' : group_id_exists,
    'changed organization' : group_id_exists,
    'deleted organization' : group_id_exists,
    'follow group' : group_id_exists,
    }

def object_id_validator(key, activity_dict, errors, context):
    '''Validate the 'object_id' value of an activity_dict.

    Uses the object_id_validators dict (above) to find and call an 'object_id'
    validator function for the given activity_dict's 'activity_type' value.

    Raises Invalid if the model given in context contains no object of the
    correct type (according to the 'activity_type' value of the activity_dict)
    with the given ID.

    Raises Invalid if there is no object_id_validator for the activity_dict's
    'activity_type' value.

    '''
    activity_type = activity_dict[('activity_type',)]
    if object_id_validators.has_key(activity_type):
        object_id = activity_dict[('object_id',)]
        return object_id_validators[activity_type](object_id, context)
    else:
        raise Invalid('There is no object_id validator for '
            'activity type "%s"' % activity_type)

name_match = re.compile('[a-z0-9_\-]*$')
def name_validator(value, context):
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
    if not isinstance(value, string_types):
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

def package_name_validator(key, data, errors, context):
    model = context['model']
    session = context['session']
    package = context.get('package')

    query = session.query(model.Package.state).filter_by(name=data[key])
    if package:
        package_id = package.id
    else:
        package_id = data.get(key[:-1] + ('id',))
    if package_id and package_id is not missing:
        query = query.filter(model.Package.id != package_id)
    result = query.first()
    if result and result.state != State.DELETED:
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

def package_version_validator(value, context):

    if len(value) > PACKAGE_VERSION_MAX_LENGTH:
        raise Invalid(_('Version must be a maximum of %i characters long') % \
                      PACKAGE_VERSION_MAX_LENGTH)
    return value

def duplicate_extras_key(key, data, errors, context):

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

def group_name_validator(key, data, errors, context):
    model = context['model']
    session = context['session']
    group = context.get('group')

    query = session.query(model.Group.name).filter_by(name=data[key])
    if group:
        group_id = group.id
    else:
        group_id = data.get(key[:-1] + ('id',))
    if group_id and group_id is not missing:
        query = query.filter(model.Group.id != group_id)
    result = query.first()
    if result:
        errors[key].append(_('Group name already exists in database'))

def tag_length_validator(value, context):

    if len(value) < MIN_TAG_LENGTH:
        raise Invalid(
            _('Tag "%s" length is less than minimum %s') % (value, MIN_TAG_LENGTH)
        )
    if len(value) > MAX_TAG_LENGTH:
        raise Invalid(
            _('Tag "%s" length is more than maximum %i') % (value, MAX_TAG_LENGTH)
        )
    return value

def tag_name_validator(value, context):

    tagname_match = re.compile('[\w \-.]*$', re.UNICODE)
    if not tagname_match.match(value):
        raise Invalid(_('Tag "%s" must be alphanumeric '
                        'characters or symbols: -_.') % (value))
    return value

def tag_not_uppercase(value, context):

    tagname_uppercase = re.compile('[A-Z]')
    if tagname_uppercase.search(value):
        raise Invalid(_('Tag "%s" must not be uppercase' % (value)))
    return value

def tag_string_convert(key, data, errors, context):
    '''Takes a list of tags that is a comma-separated string (in data[key])
    and parses tag names. These are added to the data dict, enumerated. They
    are also validated.'''

    if isinstance(data[key], string_types):
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

def ignore_not_admin(key, data, errors, context):
    # Deprecated in favour of ignore_not_package_admin
    return ignore_not_package_admin(key, data, errors, context)

def ignore_not_package_admin(key, data, errors, context):
    '''Ignore if the user is not allowed to administer the package specified.'''

    model = context['model']
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


def ignore_not_sysadmin(key, data, errors, context):
    '''Ignore the field if user not sysadmin or ignore_auth in context.'''

    user = context.get('user')
    ignore_auth = context.get('ignore_auth')

    if ignore_auth or (user and authz.is_sysadmin(user)):
        return

    data.pop(key)


def ignore_not_group_admin(key, data, errors, context):
    '''Ignore if the user is not allowed to administer for the group specified.'''

    model = context['model']
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

def user_name_validator(key, data, errors, context):
    '''Validate a new user name.

    Append an error message to ``errors[key]`` if a user named ``data[key]``
    already exists. Otherwise, do nothing.

    :raises ckan.lib.navl.dictization_functions.Invalid: if ``data[key]`` is
        not a string
    :rtype: None

    '''
    model = context['model']
    new_user_name = data[key]

    if not isinstance(new_user_name, string_types):
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

def user_both_passwords_entered(key, data, errors, context):

    password1 = data.get(('password1',),None)
    password2 = data.get(('password2',),None)

    if password1 is None or password1 == '' or \
       password2 is None or password2 == '':
        errors[('password',)].append(_('Please enter both passwords'))

def user_password_validator(key, data, errors, context):
    value = data[key]

    if isinstance(value, Missing):
        pass
    elif not isinstance(value, string_types):
        errors[('password',)].append(_('Passwords must be strings'))
    elif value == '':
        pass
    elif len(value) < 8:
        errors[('password',)].append(_('Your password must be 8 characters or '
                                       'longer'))

def user_passwords_match(key, data, errors, context):

    password1 = data.get(('password1',),None)
    password2 = data.get(('password2',),None)

    if not password1 == password2:
        errors[key].append(_('The passwords you entered do not match'))
    else:
        #Set correct password
        data[('password',)] = password1

def user_password_not_empty(key, data, errors, context):
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

def user_about_validator(value,context):
    if 'http://' in value or 'https://' in value:
        raise Invalid(_('Edit not allowed as it looks like spam. Please avoid links in your description.'))

    return value

def vocabulary_name_validator(name, context):
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

def vocabulary_id_not_changed(value, context):
    vocabulary = context.get('vocabulary')
    if vocabulary and value != vocabulary.id:
        raise Invalid(_('Cannot change value of key from %s to %s. '
                        'This key is read-only') % (vocabulary.id, value))
    return value

def vocabulary_id_exists(value, context):
    model = context['model']
    session = context['session']
    result = session.query(model.Vocabulary).get(value)
    if not result:
        raise Invalid(_('Tag vocabulary was not found.'))
    return value

def tag_in_vocabulary_validator(value, context):
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

def tag_not_in_vocabulary(key, tag_dict, errors, context):
    tag_name = tag_dict[('name',)]
    if not tag_name:
        raise Invalid(_('No tag name'))
    if tag_dict.has_key(('vocabulary_id',)):
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

def url_validator(key, data, errors, context):
    ''' Checks that the provided value (if it is present) is a valid URL '''
    import urlparse
    import string

    model = context['model']
    session = context['session']

    url = data.get(key, None)
    if not url:
        return

    pieces = urlparse.urlparse(url)
    if all([pieces.scheme, pieces.netloc]) and \
       set(pieces.netloc) <= set(string.letters + string.digits + '-.') and \
       pieces.scheme in ['http', 'https']:
       return

    errors[key].append(_('Please provide a valid URL'))


def user_name_exists(user_name, context):
    model = context['model']
    session = context['session']
    result = session.query(model.User).filter_by(name=user_name).first()
    if not result:
        raise Invalid('%s: %s' % (_('Not found'), _('User')))
    return result.name


def role_exists(role, context):
    if role not in authz.ROLE_PERMISSIONS:
        raise Invalid(_('role does not exist.'))
    return role


def datasets_with_no_organization_cannot_be_private(key, data, errors,
        context):

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


def list_of_strings(key, data, errors, context):
    value = data.get(key)
    if not isinstance(value, list):
        raise Invalid(_('Not a list'))
    for x in value:
        if not isinstance(x, string_types):
            raise Invalid('%s: %s' % (_('Not a string'), x))

def if_empty_guess_format(key, data, errors, context):
    value = data[key]
    resource_id = data.get(key[:-1] + ('id',))

    # if resource_id then an update
    if (not value or value is Missing) and not resource_id:
        url = data.get(key[:-1] + ('url',), '')
        mimetype, encoding = mimetypes.guess_type(url)
        if mimetype:
            data[key] = mimetype

def clean_format(format):
    return h.unified_resource_format(format)

def no_loops_in_hierarchy(key, data, errors, context):
    '''Checks that the parent groups specified in the data would not cause
    a loop in the group hierarchy, and therefore cause the recursion up/down
    the hierarchy to get into an infinite loop.
    '''
    if not 'id' in data:
        # Must be a new group - has no children, so no chance of loops
        return
    group = context['model'].Group.get(data['id'])
    allowable_parents = group.\
                        groups_allowed_to_be_its_parent(type=group.type)
    for parent in data['groups']:
        parent_name = parent['name']
        # a blank name signifies top level, which is always allowed
        if parent_name and context['model'].Group.get(parent_name) \
                not in allowable_parents:
            raise Invalid(_('This parent would create a loop in the '
                            'hierarchy'))


def filter_fields_and_values_should_have_same_length(key, data, errors, context):
    convert_to_list_if_string = logic.converters.convert_to_list_if_string
    fields = convert_to_list_if_string(data.get(('filter_fields',), []))
    values = convert_to_list_if_string(data.get(('filter_values',), []))

    if len(fields) != len(values):
        msg = _('"filter_fields" and "filter_values" should have the same length')
        errors[('filter_fields',)].append(msg)
        errors[('filter_values',)].append(msg)


def filter_fields_and_values_exist_and_are_valid(key, data, errors, context):
    convert_to_list_if_string = logic.converters.convert_to_list_if_string
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


def extra_key_not_in_root_schema(key, data, errors, context):

    for schema_key in context.get('schema_keys', []):
        if schema_key == data[key]:
            raise Invalid(_('There is a schema field with the same name'))


def empty_if_not_sysadmin(key, data, errors, context):
    '''Only sysadmins may pass this value'''
    from ckan.lib.navl.validators import empty

    user = context.get('user')

    ignore_auth = context.get('ignore_auth')
    if ignore_auth or (user and authz.is_sysadmin(user)):
        return

    empty(key, data, errors, context)

#pattern from https://html.spec.whatwg.org/#e-mail-state-(type=email)
email_pattern = re.compile(r"^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9]"\
                       "(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9]"\
                       "(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$")


def email_validator(value, context):
    '''Validate email input '''

    if value:
        if not email_pattern.match(value):
            raise Invalid(_('Email {email} is not a valid format').format(email=value))
    return value
