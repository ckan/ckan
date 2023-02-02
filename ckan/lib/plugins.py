# encoding: utf-8
from __future__ import annotations

import logging
import os
import sys
from typing import Any, Optional, TYPE_CHECKING, TypeVar, cast

from flask import Blueprint

import ckan.logic.schema as schema
from ckan.common import g
from ckan import logic, model, plugins
import ckan.authz
from ckan.types import Context, DataDict, Schema
from . import signals
from .navl.dictization_functions import validate
if TYPE_CHECKING:
    from ckan.config.middleware.flask_app import CKANFlask


log = logging.getLogger(__name__)

PackagePlugin = TypeVar('PackagePlugin')
GroupPlugin = TypeVar('GroupPlugin')
OrganizationPlugin = TypeVar('OrganizationPlugin')

# Mapping from package-type strings to IDatasetForm instances
_package_plugins: dict[str, 'plugins.IDatasetForm'] = {}
# The fallback behaviour
_default_package_plugin: Optional['plugins.IDatasetForm'] = None

# Mapping from group-type strings to IGroupForm instances
_group_plugins: dict[str, 'plugins.IGroupForm'] = {}
# The fallback behaviour
_default_group_plugin: Optional['plugins.IGroupForm'] = None
_default_organization_plugin: Optional['plugins.IGroupForm'] = None
# Mapping from group-type strings to controllers
_group_controllers: dict[str, str] = {}


def reset_package_plugins() -> None:
    global _default_package_plugin
    _default_package_plugin = None
    global _package_plugins
    _package_plugins = {}


def reset_group_plugins() -> None:
    global _default_group_plugin
    _default_group_plugin = None
    global _default_organization_plugin
    _default_organization_plugin = None
    global _group_plugins
    _group_plugins = {}
    global _group_controllers
    _group_controllers = {}


def lookup_package_plugin(package_type: Optional[str]=None) -> 'plugins.IDatasetForm':
    """
    Returns the plugin controller associoated with the given package type.

    If the package type is None or cannot be found in the mapping, then the
    fallback behaviour is used.

    """
    assert _default_package_plugin
    if package_type is None:
        return _default_package_plugin
    return _package_plugins.get(package_type, _default_package_plugin)



def lookup_group_plugin(group_type: Optional[str]=None) -> 'plugins.IGroupForm':
    """
    Returns the form plugin associated with the given group type.

    If the group type is None or cannot be found in the mapping, then the
    fallback behaviour is used.
    """
    assert _default_group_plugin
    assert _default_organization_plugin
    if group_type is None:
        return _default_group_plugin
    return _group_plugins.get(group_type, _default_organization_plugin
        if group_type == 'organization' else _default_group_plugin)


def lookup_group_controller(group_type: Optional[str]=None) -> Optional[str]:
    """
    Returns the group controller associated with the given group type. The
    controller is expressed as a string that you'd pass to url_to(controller=x)
    """
    if group_type:
        return _group_controllers.get(group_type)
    return None


def register_package_plugins() -> None:
    """
    Register the various IDatasetForm instances.

    This method will setup the mappings between package types and the
    registered IDatasetForm instances.
    """
    global _default_package_plugin

    # Create the mappings and register the fallback behaviour if one is found.
    for plugin in plugins.PluginImplementations(plugins.IDatasetForm):
        if plugin.is_fallback():
            if _default_package_plugin is not None and not isinstance(_default_package_plugin, DefaultDatasetForm):
                raise ValueError("More than one fallback "
                                 "IDatasetForm has been registered")
            _default_package_plugin = plugin
        for package_type in plugin.package_types():
            if package_type in _package_plugins:
                raise ValueError("An existing IDatasetForm is "
                                 "already associated with the package type "
                                 "'%s'" % package_type)
            _package_plugins[package_type] = plugin

    # Setup the fallback behaviour if one hasn't been defined.
    set_default_package_plugin()


def register_package_blueprints(app: 'CKANFlask') -> None:
    """
    Register a Flask blueprint for the various IDatasetForm instances.

    Actually two blueprints per IDatasetForm instance, one for the dataset routes
    and one for the resources one.
    """

    from ckan.views.dataset import dataset, register_dataset_plugin_rules
    from ckan.views.resource import (
        resource, prefixed_resource,
        register_dataset_plugin_rules as dataset_resource_rules)

    registered_dataset = False

    # Create the mappings and register the fallback behaviour if one is found.
    for plugin in plugins.PluginImplementations(plugins.IDatasetForm):
        for package_type in plugin.package_types():

            if package_type == 'dataset':
                registered_dataset = True

            if package_type in app.blueprints:
                raise ValueError(
                    'A blueprint for has already been associated for the '
                    'package type {}'.format(package_type))

            dataset_blueprint = Blueprint(
                package_type,
                dataset.import_name,
                url_prefix='/{}'.format(package_type),
                url_defaults={'package_type': package_type})
            if hasattr(plugin, 'prepare_dataset_blueprint'):
                dataset_blueprint = plugin.prepare_dataset_blueprint(
                    package_type,
                    dataset_blueprint)
            register_dataset_plugin_rules(dataset_blueprint)

            signals.register_blueprint.send(
                u"dataset", blueprint=dataset_blueprint)
            app.register_blueprint(dataset_blueprint)

            resource_blueprint = Blueprint(
                u'{}_resource'.format(package_type),
                resource.import_name,
                url_prefix=u'/{}/<id>/resource'.format(package_type),
                url_defaults={u'package_type': package_type})
            if hasattr(plugin, 'prepare_resource_blueprint'):
                resource_blueprint = plugin.prepare_resource_blueprint(
                    package_type,
                    resource_blueprint)
            dataset_resource_rules(resource_blueprint)
            signals.register_blueprint.send(
                u"resource", blueprint=resource_blueprint)
            app.register_blueprint(resource_blueprint)
            log.debug(
                'Registered blueprints for custom dataset type \'{}\''.format(
                    package_type))

    if not registered_dataset:
        # core dataset blueprint not overridden
        app.register_blueprint(dataset)
        app.register_blueprint(resource)

    # core no-package-type resource blueprint loaded last
    app.register_blueprint(prefixed_resource)


def set_default_package_plugin() -> None:
    global _default_package_plugin
    if _default_package_plugin is None:
        _default_package_plugin = cast(
            plugins.IDatasetForm, DefaultDatasetForm())


def register_group_plugins() -> None:
    """
    Register the various IGroupForm instances.

    This method will setup the mappings between group types and the
    registered IGroupForm instances.

    It will register IGroupForm instances for both groups and organizations
    """
    global _default_group_plugin
    global _default_organization_plugin

    for plugin in plugins.PluginImplementations(plugins.IGroupForm):

        # Get group_controller from plugin if there is one,
        # otherwise use 'group'
        try:
            group_controller = plugin.group_controller()
        except AttributeError:
            group_controller = 'group'

        if hasattr(plugin, 'is_organization'):
            is_organization: bool = plugin.is_organization
        else:
            is_organization = group_controller == 'organization'

        if plugin.is_fallback():

            if is_organization:
                if _default_organization_plugin is not None and \
                   not isinstance(_default_organization_plugin, DefaultOrganizationForm):
                        raise ValueError("More than one fallback IGroupForm for "
                                         "organizations has been registered")
                _default_organization_plugin = plugin

            else:
                if _default_group_plugin is not None and \
                   not isinstance(_default_group_plugin, DefaultGroupForm):
                        raise ValueError("More than one fallback IGroupForm for "
                                         "groups has been registered")
                _default_group_plugin = plugin

        for group_type in plugin.group_types():

            if group_type in _group_plugins:
                raise ValueError("An existing IGroupForm is "
                                 "already associated with the group type "
                                 "'%s'" % group_type)
            _group_plugins[group_type] = plugin
            _group_controllers[group_type] = group_controller

    # Setup the fallback behaviour if one hasn't been defined.
    set_default_group_plugin()


def register_group_blueprints(app: 'CKANFlask') -> None:
    """
    Register a Flask blueprint for the various IGroupForm instances.

    It will register blueprints for both groups and organizations
    """

    from ckan.views.group import group, register_group_plugin_rules

    for plugin in plugins.PluginImplementations(plugins.IGroupForm):

        # Get group_controller from plugin if there is one,
        # otherwise use 'group'
        try:
            group_controller = plugin.group_controller()
        except AttributeError:
            group_controller = 'group'

        if hasattr(plugin, 'is_organization'):
            is_organization: bool = plugin.is_organization
        else:
            is_organization = group_controller == 'organization'

        for group_type in plugin.group_types():

            if group_type in (u'group', u'organization'):
                # The default routes are registered with the core
                # 'group' or 'organization' blueprint
                continue
            elif group_type in app.blueprints:
                raise ValueError(
                    'A blueprint for has already been associated for the '
                    'group type {}'.format(group_type))

            blueprint = Blueprint(group_type,
                                  group.import_name,
                                  url_prefix='/{}'.format(group_type),
                                  url_defaults={
                                      u'group_type': group_type,
                                      u'is_organization': is_organization})
            if hasattr(plugin, 'prepare_group_blueprint'):
                blueprint = plugin.prepare_group_blueprint(
                    group_type, blueprint)
            register_group_plugin_rules(blueprint)
            signals.register_blueprint.send(
                u"organization" if is_organization else u"group",
                blueprint=blueprint)
            app.register_blueprint(blueprint)


def set_default_group_plugin() -> None:
    global _default_group_plugin
    global _default_organization_plugin
    global _group_controllers
    # Setup the fallback behaviour if one hasn't been defined.
    if _default_group_plugin is None:
        _default_group_plugin = cast(
            plugins.IDatasetForm, DefaultGroupForm())
    if _default_organization_plugin is None:
        _default_organization_plugin = cast(
            plugins.IGroupForm, DefaultOrganizationForm())
    if 'group' not in _group_controllers:
        _group_controllers['group'] = 'group'
    if 'organization' not in _group_controllers:
        _group_controllers['organization'] = 'organization'


def plugin_validate(
        plugin: Any, context: Context,
        data_dict: DataDict, schema: Schema, action: Any) -> Any:
    """
    Backwards compatibility with 2.x dataset group and org plugins:
    return a default validate method if one has not been provided.
    """
    if hasattr(plugin, 'validate'):
        result = plugin.validate(context, data_dict, schema, action)
        if result is not None:
            return result

    return validate(data_dict, schema, context)


def get_permission_labels() -> Any:
    '''Return the permission label plugin (or default implementation)'''
    for plugin in plugins.PluginImplementations(plugins.IPermissionLabels):
        return plugin
    return DefaultPermissionLabels()


class DefaultDatasetForm(object):
    '''The default implementatinon of
    :py:class:`~ckan.plugins.interfaces.IDatasetForm`.

    This class serves two purposes:

    1. It provides a base class for plugin classes that implement
       :py:class:`~ckan.plugins.interfaces.IDatasetForm` to inherit from, so
       they can inherit the default behavior and just modify the bits they
       need to.

    2. It is used as the default fallback plugin when no registered
       :py:class:`~ckan.plugins.interfaces.IDatasetForm` plugin handles the
       given dataset type and no other plugin has registered itself as the
       fallback plugin.

    .. note::

       :py:class:`~ckan.plugins.toolkit.DefaultDatasetForm` doesn't call
       :py:func:`~ckan.plugins.core.implements`, because we don't want it
       being registered.

    '''
    def create_package_schema(self) -> Schema:
        return schema.default_create_package_schema()

    def update_package_schema(self) -> Schema:
        return schema.default_update_package_schema()

    def show_package_schema(self) -> Schema:
        return schema.default_show_package_schema()

    def setup_template_variables(self, context: Context,
                                 data_dict: dict[str, Any]) -> None:
        data_dict.update({'available_only': True})

        ## This is messy as auths take domain object not data_dict
        context_pkg = context.get('package', None)
        pkg = context_pkg or getattr(g, 'pkg', None)

        if pkg:
            if not context_pkg:
                context['package'] = pkg

    def new_template(self) -> str:
        return 'package/new.html'

    def read_template(self) -> str:
        return 'package/read.html'

    def edit_template(self) -> str:
        return 'package/edit.html'

    def search_template(self) -> str:
        return 'package/search.html'

    def history_template(self) -> None:
        return None

    def resource_template(self) -> str:
        return 'package/resource_read.html'

    def package_form(self) -> str:
        return 'package/new_package_form.html'

    def resource_form(self) -> str:
        return 'package/snippets/resource_form.html'


class DefaultGroupForm(object):
    """
    Provides a default implementation of the pluggable Group controller
    behaviour.

    This class has 2 purposes:

     - it provides a base class for IGroupForm implementations to use if
       only a subset of the method hooks need to be customised.

     - it provides the fallback behaviour if no plugin is setup to
       provide the fallback behaviour.

    .. note:: this isn't a plugin implementation. This is deliberate, as we
        don't want this being registered.

    """
    def group_controller(self) -> str:
        return 'group'

    def new_template(self) -> str:
        """
        Returns a string representing the location of the template to be
        rendered for the 'new' page
        """
        return 'group/new.html'

    def index_template(self) -> str:
        """
        Returns a string representing the location of the template to be
        rendered for the index page
        """
        return 'group/index.html'

    def read_template(self) -> str:
        """
        Returns a string representing the location of the template to be
        rendered for the read page
        """
        return 'group/read.html'

    def about_template(self) -> str:
        """
        Returns a string representing the location of the template to be
        rendered for the about page
        """
        return 'group/about.html'

    def edit_template(self) -> str:
        """
        Returns a string representing the location of the template to be
        rendered for the edit page
        """
        return 'group/edit.html'

    def activity_template(self) -> str:
        """
        Returns a string representing the location of the template to be
        rendered for the activity stream page
        """
        return 'group/activity_stream.html'

    def admins_template(self) -> str:
        """
        Returns a string representing the location of the template to be
        rendered for the admins page
        """
        return 'group/admins.html'

    def bulk_process_template(self) -> str:
        """
        Returns a string representing the location of the template to be
        rendered for the bulk_process page
        """
        return 'group/bulk_process.html'

    def group_form(self) -> str:
        return 'group/new_group_form.html'

    def form_to_db_schema_options(self,
                                  options: dict[str, Any]) -> dict[str, Any]:
        ''' This allows us to select different schemas for different
        purpose eg via the web interface or via the api or creation vs
        updating. It is optional and if not available form_to_db_schema
        should be used.
        If a context is provided, and it contains a schema, it will be
        returned.
        '''
        schema = options.get('context', {}).get('schema', None)
        if schema:
            return schema

        if options.get('api'):
            if options.get('type') == 'create':
                return self.form_to_db_schema_api_create()
            else:
                return self.form_to_db_schema_api_update()
        else:
            return self.form_to_db_schema()

    def form_to_db_schema_api_create(self) -> dict[str, Any]:
        return schema.default_group_schema()

    def form_to_db_schema_api_update(self) -> dict[str, Any]:
        return schema.default_update_group_schema()

    def form_to_db_schema(self) -> dict[str, Any]:
        return schema.group_form_schema()

    def db_to_form_schema(self) -> dict[str, Any]:
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''
        return {}

    def db_to_form_schema_options(self,
                                  options: dict[str, Any]) -> dict[str, Any]:
        '''This allows the selection of different schemas for different
        purposes.  It is optional and if not available, ``db_to_form_schema``
        should be used.
        If a context is provided, and it contains a schema, it will be
        returned.
        '''
        schema = options.get('context', {}).get('schema', None)
        if schema:
            return schema
        return self.db_to_form_schema()

    def check_data_dict(self, data_dict: dict[str, Any]) -> None:
        '''Check if the return data is correct, mostly for checking out
        if spammers are submitting only part of the form

        .. code-block:: python

            # Resources might not exist yet (eg. Add Dataset)
            surplus_keys_schema = ['__extras', '__junk', 'state', 'groups',
                'extras_validation', 'save', 'return_to',
                'resources'
            ]

            schema_keys = form_to_db_package_schema().keys()
            keys_in_schema = set(schema_keys) - set(surplus_keys_schema)

            missing_keys = keys_in_schema - set(data_dict.keys())

            if missing_keys:
                #print data_dict
                #print missing_keys
                log.info('incorrect form fields posted')
                raise DataError(data_dict)

        '''
        pass

    def setup_template_variables(self, context: Context,
                                 data_dict: dict[str, Any]) -> None:
        pass


class DefaultOrganizationForm(DefaultGroupForm):
    def group_controller(self) -> str:
        return 'organization'

    def group_form(self) -> str:
        return 'organization/new_organization_form.html'

    def setup_template_variables(self, context: Context,
                                 data_dict: dict[str, Any]) -> None:
        pass

    def new_template(self) -> str:
        return 'organization/new.html'

    def about_template(self) -> str:
        return 'organization/about.html'

    def index_template(self) -> str:
        return 'organization/index.html'

    def admins_template(self) -> str:
        return 'organization/admins.html'

    def bulk_process_template(self) -> str:
        return 'organization/bulk_process.html'

    def read_template(self) -> str:
        return 'organization/read.html'

    # don't override history_template - use group template for history

    def edit_template(self) -> str:
        return 'organization/edit.html'

    def activity_template(self) -> str:
        return 'organization/activity_stream.html'


class DefaultTranslation(object):
    name: str

    def i18n_directory(self) -> str:
        '''Change the directory of the *.mo translation files

        The default implementation assumes the plugin is
        ckanext/myplugin/plugin.py and the translations are stored in
        i18n/
        '''
        # assume plugin is called ckanext.<myplugin>.<...>.PluginClass
        extension_module_name = '.'.join(self.__module__.split('.')[:3])
        module = sys.modules[extension_module_name]
        return os.path.join(os.path.dirname(str(module.__file__)), 'i18n')

    def i18n_locales(self) -> list[str]:
        '''Change the list of locales that this plugin handles

        By default the will assume any directory in subdirectory in the
        directory defined by self.directory() is a locale handled by this
        plugin
        '''
        directory = self.i18n_directory()
        return [ d for
                 d in os.listdir(directory)
                 if os.path.isdir(os.path.join(directory, d))
        ]

    def i18n_domain(self) -> str:
        '''Change the gettext domain handled by this plugin

        This implementation assumes the gettext domain is
        ckanext-{extension name}, hence your pot, po and mo files should be
        named ckanext-{extension name}.mo'''
        return 'ckanext-{name}'.format(name=self.name)


class DefaultPermissionLabels(object):
    u'''
    Default permissions for package_search/package_show:
    - everyone can read public datasets "public"
    - users can read their own drafts "creator-(user id)"
    - users can read datasets belonging to their orgs "member-(org id)"
    - users can read datasets where they are collaborators "collaborator-(dataset id)"
    '''
    def get_dataset_labels(self, dataset_obj: model.Package) -> list[str]:
        if dataset_obj.state == u'active' and not dataset_obj.private:
            return [u'public']

        if ckan.authz.check_config_permission('allow_dataset_collaborators'):
            # Add a generic label for all this dataset collaborators
            labels = [u'collaborator-%s' % dataset_obj.id]
        else:
            labels = []

        if dataset_obj.owner_org:
            labels.append(u'member-%s' % dataset_obj.owner_org)
        else:
            labels.append(u'creator-%s' % dataset_obj.creator_user_id)

        return labels

    def get_user_dataset_labels(self, user_obj: model.User) -> list[str]:
        labels = [u'public']
        if not user_obj or user_obj.is_anonymous:
            return labels

        labels.append(u'creator-%s' % user_obj.id)

        orgs = logic.get_action(u'organization_list_for_user')(
            {u'user': user_obj.id}, {u'permission': u'read'})
        labels.extend(u'member-%s' % o[u'id'] for o in orgs)

        if ckan.authz.check_config_permission('allow_dataset_collaborators'):
            # Add a label for each dataset this user is a collaborator of
            datasets = logic.get_action('package_collaborator_list_for_user')(
                {'ignore_auth': True}, {'id': user_obj.id})

            labels.extend('collaborator-%s' % d['package_id'] for d in datasets)

        return labels
