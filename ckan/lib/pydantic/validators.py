from sqlalchemy.orm.exc import NoResultFound
from pydantic import BaseConfig
from pydantic.fields import ModelField
from typing import Any, Dict, Type, Union, Optional, Callable

import ckan.lib.navl.dictization_functions as df
import ckan.authz as authz
import ckan.logic as logic
from ckan.types import Context
from ckan.model.core import State
from ckan.common import _
from ckan.model import PACKAGE_NAME_MIN_LENGTH, PACKAGE_NAME_MAX_LENGTH


Missing = df.Missing
missing = df.missing
Invalid = df.Invalid
StopOnError = df.StopOnError


def p_not_empty(
    value: Any,
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
):
    """Ensure value is available in the input and is not empty."""

    valid_values = [False, 0, 0.0]

    if value in valid_values:
        return value

    if not value:
        raise ValueError(f"Missing value")
    return value


def p_user_password_validator(
    value: Any,
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
):
    """Ensures that password is safe enough."""

    if isinstance(value, Missing):
        pass
    elif not isinstance(value, str):
        raise ValueError("Passwords must be strings")
    elif value == "":
        pass
    elif len(value) < 8:
        raise ValueError("Your password must be 8 characters or longer")
    return value


def p_user_passwords_match(
    value: Any,
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
):
    """Ensures that password and password confirmation match."""

    if field.name == "password2":
        if not value == values["password1"]:
            raise ValueError("The passwords you entered do not match")
        else:
            # Set correct password
            values["password"] = value
        return value


def p_empty_if_not_sysadmin(
    value: Any,
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
):
    '''Only sysadmins may pass this value'''
    from ckan.common import current_user

    ignore_auth = context.get('ignore_auth')
    if current_user.is_authenticated:
        if ignore_auth or current_user.sysadmin:  # type: ignore
            return value

    if value:
        raise ValueError('The input field %(name)s was not expected.' % {"name": field.name})


def p_package_name_validator(
    value: Any, 
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
) -> Any:
    """Ensures that value can be used as a package's name
    """
    model = context['model']
    session = context['session']
    package = context.get('package')

    query = session.query(model.Package.id).filter(
        model.Package.name == value,
        model.Package.state != State.DELETED,
    )
    if package:
        package_id: Union[Optional[str], Missing] = package.id
    else:
        package_id = value
    if package_id and package_id is not missing:
        query = query.filter(model.Package.id != package_id)

    if session.query(query.exists()).scalar():
        raise Invalid(_('That URL is already in use.'))

    if len(value) < PACKAGE_NAME_MIN_LENGTH:
        raise Invalid(
            _('Name "%s" length is less than minimum %s') % (field.name, PACKAGE_NAME_MIN_LENGTH)
        )
    if len(value) > PACKAGE_NAME_MAX_LENGTH:
        raise Invalid(
            _('Name "%s" length is more than maximum %s') % (field.name, PACKAGE_NAME_MAX_LENGTH)
        )


def p_ignore_missing(
    value: Any, 
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
) -> None:
    '''If the key is missing from the data, ignore the rest of the key's
    schema.

    By putting ignore_missing at the start of the schema list for a key,
    you can allow users to post a dict without the key and the dict will pass
    validation. But if they post a dict that does contain the key, then any
    validators after ignore_missing in the key's schema list will be applied.

    :raises ckan.lib.navl.dictization_functions.StopOnError: if ``data[key]``
        is :py:data:`ckan.lib.navl.dictization_functions.missing` or ``None``

    :returns: ``None``

    '''

    if value is missing or value is None:
        values.pop(field.name, None)
        raise StopOnError


def p_if_empty_same_as(other_key: str) -> Callable[..., Any]:
    """Copy value from other field when current field is missing or empty.

    .. code-block::

        data, errors = tk.navl_validate(
            {"hello": 1},
            {"hello": [], "world": [if_empty_same_as("hello")]}
        )
        assert data == {"hello": 1, "world": 1}

    """
    def callable(
            value: Any, 
            values: Dict[str, Any],
            config: Type[BaseConfig],
            field: Type[ModelField],
            context: Context):

        if not value or value is missing:
            values[field.name] = values[other_key]

    return callable


def p_ignore_not_package_admin(
    value: Any, 
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
) -> Any:
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
    # FIXME is this the best way to check for state only?
    if 'state' in field.name and context.get('allow_state_change'):
        return
    values.pop(field.name)


def p_owner_org_validator(
    value: Any, 
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
) -> Any:
    """Validate organization for the dataset.

    Depending on the settings and user's permissions, this validator checks
    whether organization is optional and ensures that specified organization
    can be set as an owner of dataset.

    """

    if value is missing or value is None:
        if not authz.check_config_permission('create_unowned_dataset'):
            raise Invalid(_('An organization must be provided'))
        values.pop(field.name, None)
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
                if value != package.owner_org and not user_is_org_member:
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

    values[field.name] = group_id


def p_datasets_with_no_organization_cannot_be_private(value: Any,
                                                    values: Dict[str, Any],
                                                    config: Type[BaseConfig],
                                                    field: Type[ModelField],
                                                    context: Context) -> Any:

    dataset_id = values.get('id')
    owner_org = values.get('owner_org')
    private = value is True

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
       raise Invalid(_("Datasets with no organization can't be private."))


def p_ignore(
    value: Any, 
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
) -> None:
    """Remove the value from the input and skip the rest of validators.

    .. code-block::

        data, errors = tk.navl_validate(
            {"hello": 1},
            {"hello": [ignore]}
        )
        assert data == {}

    """
    values.pop(field.name, None)
    raise StopOnError


def p_ignore_empty(
    value: Any, 
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
) -> None:
    """Skip the rest of validators if the value is empty or missing.

    .. code-block::

        data, errors = tk.navl_validate(
            {"hello": ""},
            {"hello": [ignore_empty, isodate]}
        )
        assert data == {}
        assert not errors

    """
    value = values.get(field.name)

    if value is missing or not value:
        values.pop(field.name, None)
        raise StopOnError


def p_resource_id_does_not_exist(
    value: Any, 
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
) -> Any:
    breakpoint()
    session = context['session']
    model = context['model']

    if value is missing:
        return
    resource_id = value

    package_id = values.get('package_id')
    package_query = session.query(model.Package).filter(
        model.Package.name == package_id,
        model.Package.state != State.DELETED
    )

    query = session.query(model.Resource.package_id).filter(
        model.Resource.id == resource_id,
        model.Resource.state != State.DELETED,
    )
    try:
        [parent_id] = query.one()
        package = package_query.one()
    except NoResultFound:
        return
    if parent_id != package.id:
        raise Invalid(_('Resource id already exists.'))


def p_keep_extras(
    value: Any, 
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
) -> None:
    """Convert dictionary into simple fields.

    .. code-block::

        data, errors = tk.navl_validate(
            {"input": {"hello": 1, "world": 2}},
            {"input": [keep_extras]}
        )
        assert data == {"hello": 1, "world": 2}

    """
    breakpoint()
    extras = values.pop(field.name, {})
    for extras_key, value in extras.items():
        values[key[:-1] + (extras_key,)] = value


def p_list_of_strings(
    value: Any, 
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
) -> Any:
    """Ensures that value is a list of strings.
    """
    if not isinstance(value, list):
        raise Invalid(_('Not a list'))
    for x in value:
        if not isinstance(x, str):
            raise Invalid('%s: %s' % (_('Not a string'), x))


def p_default(default_value: Any):
    """Convert missing or empty value to the default one.

    .. code-block::

        data, errors = tk.navl_validate(
            {},
            {"hello": [default("not empty")]}
        )
        assert data == {"hello": "not empty"}

    """
    def callable(value: Any, values: Dict[str, Any], config: Type[BaseConfig],
                 field: Type[ModelField], context: Context):

        if value is None or value == '' or value is missing:
            value = default_value

    return callable


def p_group_name_validator(
    value: Any, 
    values: Dict[str, Any],
    config: Type[BaseConfig],
    field: Type[ModelField],
    context: Context
) -> Any:
    """Ensures that value can be used as a group's name
    """

    model = context['model']
    session = context['session']
    group = context.get('group')
    group_id = ''

    query = session.query(model.Group.name).filter_by(name=value)
    if group:
        group_id: Union[Optional[str], Missing] = group.id

    if group_id and group_id is not missing:
        query = query.filter(model.Group.id != group_id)
    result = query.first()
    if result:
       raise Invalid(_('Group name already exists in database'))
