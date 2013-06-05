import datetime
from itertools import count
import re

import ckan.lib.navl.dictization_functions as df
import ckan.logic as logic
import ckan.lib.helpers as h
from ckan.model import (MAX_TAG_LENGTH, MIN_TAG_LENGTH,
                        PACKAGE_NAME_MIN_LENGTH, PACKAGE_NAME_MAX_LENGTH,
                        PACKAGE_VERSION_MAX_LENGTH,
                        VOCABULARY_NAME_MAX_LENGTH,
                        VOCABULARY_NAME_MIN_LENGTH)
import ckan.new_authz as new_authz

from ckan.common import _

Invalid = df.Invalid
StopOnError = df.StopOnError
Missing = df.Missing
missing = df.missing

def owner_org_validator(key, data, errors, context):

    value = data.get(key)

    if value is missing or not value:
        if not new_authz.check_config_permission('create_unowned_dataset'):
            raise Invalid(_('A organization must be supplied'))
        data.pop(key, None)
        raise df.StopOnError

    model = context['model']
    group = model.Group.get(value)
    if not group:
        raise Invalid(_('Organization does not exist'))
    group_id = group.id
    user = context['user']
    user = model.User.get(user)
    if not(user.sysadmin or user.is_in_group(group_id)):
        raise Invalid(_('You cannot add a dataset to this organization'))
    data[key] = group_id


def package_id_not_changed(value, context):

    package = context.get('package')
    if package and value != package.id:
        raise Invalid('Cannot change value of key from %s to %s. '
                      'This key is read-only' % (package.id, value))
    return value

def int_validator(value, context):
    if isinstance(value, int):
        return value
    try:
        if value.strip() == '':
            return None
        return int(value)
    except (AttributeError, ValueError), e:
        raise Invalid(_('Invalid integer'))

def natural_number_validator(value, context):
    value = int_validator(value, context)
    if value < 0:
        raise Invalid(_('Must be natural number'))
    return value

def boolean_validator(value, context):
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
    except (TypeError, ValueError), e:
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

def user_id_exists(user_id, context):
    """Raises Invalid if the given user_id does not exist in the model given
    in the context, otherwise returns the given user_id.

    """
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
    """Raises Invalid if the given group_id does not exist in the model given
    in the context, otherwise returns the given group_id.

    """
    model = context['model']
    session = context['session']

    result = session.query(model.Group).get(group_id)
    if not result:
        raise Invalid('%s: %s' % (_('Not found'), _('Group')))
    return group_id


def related_id_exists(related_id, context):
    """Raises Invalid if the given related_id does not exist in the model
    given in the context, otherwise returns the given related_id.

    """
    model = context['model']
    session = context['session']

    result = session.query(model.Related).get(related_id)
    if not result:
        raise Invalid('%s: %s' % (_('Not found'), _('Related')))
    return related_id

def group_id_or_name_exists(reference, context):
    """
    Raises Invalid if a group identified by the name or id cannot be found.
    """
    model = context['model']
    result = model.Group.get(reference)
    if not result:
        raise Invalid(_('That group name or ID does not exist.'))
    return reference

def activity_type_exists(activity_type):
    """Raises Invalid if there is no registered activity renderer for the
    given activity_type. Otherwise returns the given activity_type.

    This just uses object_id_validators as a lookup.
    very safe.

    """
    if activity_type in object_id_validators:
        return activity_type
    else:
        raise Invalid('%s: %s' % (_('Not found'), _('Activity type')))

def resource_id_exists(value, context):

    model = context['model']
    session = context['session']

    result = session.query(model.Resource).get(value)
    if not result:
        raise Invalid('%s: %s' % (_('Not found'), _('Resource')))
    return value

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
    'new related item': related_id_exists,
    'deleted related item': related_id_exists,
    'changed related item': related_id_exists,
    }

def object_id_validator(key, activity_dict, errors, context):
    """Validate the 'object_id' value of an activity_dict.

    Uses the object_id_validators dict (above) to find and call an 'object_id'
    validator function for the given activity_dict's 'activity_type' value.

    Raises Invalid if the model given in context contains no object of the
    correct type (according to the 'activity_type' value of the activity_dict)
    with the given ID.

    Raises Invalid if there is no object_id_validator for the activity_dict's
    'activity_type' value.

    """
    activity_type = activity_dict[('activity_type',)]
    if object_id_validators.has_key(activity_type):
        object_id = activity_dict[('object_id',)]
        return object_id_validators[activity_type](object_id, context)
    else:
        raise Invalid('There is no object_id validator for '
            'activity type "%s"' % activity_type)

def extras_unicode_convert(extras, context):
    for extra in extras:
        extras[extra] = unicode(extras[extra])
    return extras

name_match = re.compile('[a-z0-9_\-]*$')
def name_validator(val, context):
    # check basic textual rules
    if val in ['new', 'edit', 'search']:
        raise Invalid(_('That name cannot be used'))

    if len(val) < 2:
        raise Invalid(_('Name must be at least %s characters long') % 2)
    if len(val) > PACKAGE_NAME_MAX_LENGTH:
        raise Invalid(_('Name must be a maximum of %i characters long') % \
                      PACKAGE_NAME_MAX_LENGTH)
    if not name_match.match(val):
        raise Invalid(_('Url must be purely lowercase alphanumeric '
                        '(ascii) characters and these symbols: -_'))
    return val

def package_name_validator(key, data, errors, context):
    model = context["model"]
    session = context["session"]
    package = context.get("package")

    query = session.query(model.Package.name).filter_by(name=data[key])
    if package:
        package_id = package.id
    else:
        package_id = data.get(key[:-1] + ("id",))
    if package_id and package_id is not missing:
        query = query.filter(model.Package.id <> package_id)
    result = query.first()
    if result:
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
        query = query.filter(model.Group.id <> group_id)
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

    if isinstance(data[key], basestring):
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

    if user and new_authz.is_sysadmin(user):
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

    if ignore_auth or (user and new_authz.is_sysadmin(user)):
        return

    data.pop(key)


def ignore_not_group_admin(key, data, errors, context):
    '''Ignore if the user is not allowed to administer for the group specified.'''

    model = context['model']
    user = context.get('user')

    if user and new_authz.is_sysadmin(user):
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
    model = context["model"]
    session = context["session"]
    user = context.get("user_obj")

    query = session.query(model.User.name).filter_by(name=data[key])
    if user:
        user_id = user.id
    else:
        user_id = data.get(key[:-1] + ("id",))
    if user_id and user_id is not missing:
        query = query.filter(model.User.id <> user_id)
    result = query.first()
    if result:
        errors[key].append(_('That login name is not available.'))

def user_both_passwords_entered(key, data, errors, context):

    password1 = data.get(('password1',),None)
    password2 = data.get(('password2',),None)

    if password1 is None or password1 == '' or \
       password2 is None or password2 == '':
        errors[('password',)].append(_('Please enter both passwords'))

def user_password_validator(key, data, errors, context):
    value = data[key]

    if not value == '' and not isinstance(value, Missing) and not len(value) >= 4:
        errors[('password',)].append(_('Your password must be 4 characters or longer'))

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
    """ Checks that the provided value (if it is present) is a valid URL """
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
    if role not in new_authz.ROLE_PERMISSIONS:
        raise Invalid(_('role does not exist.'))
    return role


def list_of_strings(key, data, errors, context):
    value = data.get(key)
    if not isinstance(value, list):
        raise Invalid(_('Not a list'))
    for x in value:
        if not isinstance(x, basestring):
            raise Invalid('%s: %s' % (_('Not a string'), x))

def datasets_with_no_organization_cannot_be_private(key, data, errors,
        context):
    if data[key] is True and data.get(('owner_org',)) is None:
        errors[key].append(
                _("Datasets with no organization can't be private."))
