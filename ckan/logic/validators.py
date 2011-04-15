import re
from pylons.i18n import _, ungettext, N_, gettext
from ckan.lib.navl.dictization_functions import Invalid, missing

def package_id_not_changed(value, context):

    package = context.get('package')
    if package and value != package.id:
        raise Invalid(_('Cannot change value of key from %s to %s. '
                        'This key is read-only') % (package.id, value))
    return value

def package_id_exists(value, context):

    model = context['model']
    session = context['session']

    result = session.query(model.Package).get(value)
    if not result:
        raise Invalid(_('Package was not found.'))
    return value

def package_name_exists(value, context):

    model = context['model']
    session = context['session']

    result = session.query(model.Package).filter_by(name=value).first()

    if not result:
        raise Invalid(_('Package with name %r does not exist.') % str(value))
    return value

def package_id_or_name_exists(value, context):

    model = context['model']
    session = context['session']

    result = session.query(model.Package).get(value)
    if result:
        return value

    result = session.query(model.Package).filter_by(name=value).first()

    if not result:
        raise Invalid(_('Package was not found.'))

    return result.id

def extras_unicode_convert(extras, context):
    for extra in extras:
        extras[extra] = unicode(extras[extra])
    return extras

name_match = re.compile('[a-z0-9_\-]*$')
def name_validator(val, context):
    # check basic textual rules
    if len(val) < 2:
        raise Invalid(_('Name must be at least %s characters long') % 2)
    if not name_match.match(val):
        raise Invalid(_('Name must be purely lowercase alphanumeric '
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
        errors[key].append(_('Package name already exists in database'))

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

    if len(value) < 2:
        raise Invalid(
            _('Tag "%s" length is less than minimum %s') % (value, 2)
        )
    return value

def tag_name_validator(value, context):

    tagname_match = re.compile('[\w\-_.]*$', re.UNICODE)
    if not tagname_match.match(value):
        raise Invalid(_('Tag "%s" must be alphanumeric '
                        'characters or symbols: -_.') % (value))
    return value

def tag_not_uppercase(value, context):

    tagname_uppercase = re.compile('[A-Z]')
    if tagname_uppercase.search(value):
        raise Invalid(_('Tag "%s" must not be uppercase' % (value)))
    return value
