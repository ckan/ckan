import logging

from pylons import c
from ckan.lib import base
import ckan.lib.maintain as maintain
from ckan import logic
import logic.schema
from ckan import plugins
import ckan.new_authz

log = logging.getLogger(__name__)

# Mapping from package-type strings to IDatasetForm instances
_package_plugins = {}
# The fallback behaviour
_default_package_plugin = None

# Mapping from group-type strings to IDatasetForm instances
_group_plugins = {}
# The fallback behaviour
_default_group_plugin = None


def reset_package_plugins():
    global _default_package_plugin
    _default_package_plugin = None
    global _package_plugins
    _package_plugins = {}
    global _default_group_plugin
    _default_group_plugin = None
    global _group_plugins
    _group_plugins = {}


def lookup_package_plugin(package_type=None):
    """
    Returns the plugin controller associoated with the given package type.

    If the package type is None or cannot be found in the mapping, then the
    fallback behaviour is used.
    """
    if package_type is None:
        return _default_package_plugin
    return _package_plugins.get(package_type, _default_package_plugin)


def lookup_group_plugin(group_type=None):
    """
    Returns the plugin controller associoated with the given group type.

    If the group type is None or cannot be found in the mapping, then the
    fallback behaviour is used.
    """
    if group_type is None:
        return _default_group_plugin
    return _group_plugins.get(group_type, _default_organization_plugin
        if group_type == 'organization' else _default_group_plugin)


def register_package_plugins(map):
    """
    Register the various IDatasetForm instances.

    This method will setup the mappings between package types and the
    registered IDatasetForm instances. If it's called more than once an
    exception will be raised.
    """
    global _default_package_plugin

    # This function should have not effect if called more than once.
    # This should not occur in normal deployment, but it may happen when
    # running unit tests.
    if _default_package_plugin is not None:
        return

    # Create the mappings and register the fallback behaviour if one is found.
    for plugin in plugins.PluginImplementations(plugins.IDatasetForm):
        if plugin.is_fallback():
            if _default_package_plugin is not None:
                raise ValueError, "More than one fallback "\
                                  "IDatasetForm has been registered"
            _default_package_plugin = plugin

        for package_type in plugin.package_types():
            # Create a connection between the newly named type and the
            # package controller

            map.connect('%s_search' % package_type, '/%s' % package_type,
                        controller='package', action='search')

            map.connect('%s_new' % package_type, '/%s/new' % package_type,
                        controller='package', action='new')
            map.connect('%s_read' % package_type, '/%s/{id}' % package_type,
                        controller='package', action='read')

            for action in ['edit', 'authz', 'history']:
                map.connect('%s_%s' % (package_type, action),
                        '/%s/%s/{id}' % (package_type, action),
                        controller='package',
                        action=action
                )

            if package_type in _package_plugins:
                raise ValueError, "An existing IDatasetForm is "\
                                  "already associated with the package type "\
                                  "'%s'" % package_type
            _package_plugins[package_type] = plugin

    # Setup the fallback behaviour if one hasn't been defined.
    if _default_package_plugin is None:
        _default_package_plugin = DefaultDatasetForm()


def register_group_plugins(map):
    """
    Register the various IGroupForm instances.

    This method will setup the mappings between group types and the
    registered IGroupForm instances. If it's called more than once an
    exception will be raised.
    """
    global _default_group_plugin

    # This function should have not effect if called more than once.
    # This should not occur in normal deployment, but it may happen when
    # running unit tests.
    if _default_group_plugin is not None:
        return

    # Create the mappings and register the fallback behaviour if one is found.
    for plugin in plugins.PluginImplementations(plugins.IGroupForm):
        if plugin.is_fallback():
            if _default_group_plugin is not None:
                raise ValueError, "More than one fallback "\
                                  "IGroupForm has been registered"
            _default_group_plugin = plugin

        for group_type in plugin.group_types():
            # Create the routes based on group_type here, this will
            # allow us to have top level objects that are actually
            # Groups, but first we need to make sure we are not
            # clobbering an existing domain

            # Our version of routes doesn't allow the environ to be
            # passed into the match call and so we have to set it on the
            # map instead. This looks like a threading problem waiting
            # to happen but it is executed sequentially from inside the
            # routing setup

            map.connect('%s_index' % group_type, '/%s' % group_type,
                        controller='group', action='index')
            map.connect('%s_new' % group_type, '/%s/new' % group_type,
                        controller='group', action='new')
            map.connect('%s_read' % group_type, '/%s/{id}' % group_type,
                        controller='group', action='read')
            map.connect('%s_action' % group_type,
                        '/%s/{action}/{id}' % group_type, controller='group',
                requirements=dict(action='|'.join(['edit', 'authz', 'history']))
            )

            if group_type in _group_plugins:
                raise ValueError, "An existing IGroupForm is "\
                                  "already associated with the group type "\
                                  "'%s'" % group_type
            _group_plugins[group_type] = plugin

    # Setup the fallback behaviour if one hasn't been defined.
    if _default_group_plugin is None:
        _default_group_plugin = DefaultGroupForm()


class DefaultDatasetForm(object):
    '''The default implementation of
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
    def create_package_schema(self):
        return ckan.logic.schema.default_create_package_schema()

    def update_package_schema(self):
        return ckan.logic.schema.default_update_package_schema()

    def show_package_schema(self):
        return ckan.logic.schema.default_show_package_schema()

    def setup_template_variables(self, context, data_dict):
        authz_fn = logic.get_action('group_list_authz')
        c.groups_authz = authz_fn(context, data_dict)
        data_dict.update({'available_only': True})

        c.groups_available = authz_fn(context, data_dict)

        c.licenses = [('', '')] + base.model.Package.get_license_options()
        # CS: bad_spelling ignore 2 lines
        c.licences = c.licenses
        maintain.deprecate_context_item('licences', 'Use `c.licenses` instead')
        c.is_sysadmin = ckan.new_authz.is_sysadmin(c.user)

        if c.pkg:
            c.related_count = c.pkg.related_count

        ## This is messy as auths take domain object not data_dict
        context_pkg = context.get('package', None)
        pkg = context_pkg or c.pkg
        if pkg:
            try:
                if not context_pkg:
                    context['package'] = pkg
                logic.check_access('package_change_state', context)
                c.auth_for_change_state = True
            except logic.NotAuthorized:
                c.auth_for_change_state = False

    def new_template(self):
        return 'package/new.html'

    def read_template(self):
        return 'package/read.html'

    def edit_template(self):
        return 'package/edit.html'

    def search_template(self):
        return 'package/search.html'

    def history_template(self):
        return 'package/history.html'

    def package_form(self):
        return 'package/new_package_form.html'


class DefaultGroupForm(object):
    """
    Provides a default implementation of the pluggable Group controller
    behaviour.

    This class has 2 purposes:

     - it provides a base class for IGroupForm implementations to use if
       only a subset of the method hooks need to be customised.

     - it provides the fallback behaviour if no plugin is setup to
       provide the fallback behaviour.

    Note - this isn't a plugin implementation. This is deliberate, as we
           don't want this being registered.
    """
    def new_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the 'new' page
        """
        return 'group/new.html'

    def index_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the index page
        """
        return 'group/index.html'

    def read_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the read page
        """
        return 'group/read.html'

    def about_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the about page
        """
        return 'group/about.html'

    def history_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the history page
        """
        return 'group/history.html'

    def edit_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the edit page
        """
        return 'group/edit.html'

    def activity_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the activity stream page
        """
        return 'group/activity_stream.html'

    def admins_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the admins page
        """
        return 'group/admins.html'

    def bulk_process_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the bulk_process page
        """
        return 'group/bulk_process.html'

    def about_template(self):
        '''Return the path to the template for the group's 'about' page.

        :rtype: string

        '''
        return 'group/about.html'

    def group_form(self):
        return 'group/new_group_form.html'

    def form_to_db_schema_options(self, options):
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

    def form_to_db_schema_api_create(self):
        return logic.schema.default_group_schema()

    def form_to_db_schema_api_update(self):
        return logic.schema.default_update_group_schema()

    def form_to_db_schema(self):
        return logic.schema.group_form_schema()

    def db_to_form_schema(self):
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''

    def db_to_form_schema_options(self, options):
        '''This allows the selectino of different schemas for different
        purposes.  It is optional and if not available, ``db_to_form_schema``
        should be used.
        If a context is provided, and it contains a schema, it will be
        returned.
        '''
        schema = options.get('context', {}).get('schema', None)
        if schema:
            return schema
        return self.db_to_form_schema()

    def check_data_dict(self, data_dict):
        '''Check if the return data is correct, mostly for checking out
        if spammers are submitting only part of the form

        # Resources might not exist yet (eg. Add Dataset)
        surplus_keys_schema = ['__extras', '__junk', 'state', 'groups',
                               'extras_validation', 'save', 'return_to',
                               'resources']

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

    def setup_template_variables(self, context, data_dict):
        c.is_sysadmin = ckan.new_authz.is_sysadmin(c.user)

        ## This is messy as auths take domain object not data_dict
        context_group = context.get('group', None)
        group = context_group or c.group
        if group:
            try:
                if not context_group:
                    context['group'] = group
                logic.check_access('group_change_state', context)
                c.auth_for_change_state = True
            except logic.NotAuthorized:
                c.auth_for_change_state = False


class DefaultOrganizationForm(DefaultGroupForm):
    def group_form(self):
        return 'organization/new_organization_form.html'

    def setup_template_variables(self, context, data_dict):
        pass

    def new_template(self):
        return 'organization/new.html'

    def about_template(self):
        return 'organization/about.html'

    def index_template(self):
        return 'organization/index.html'

    def admins_template(self):
        return 'organization/admins.html'

    def bulk_process_template(self):
        return 'organization/bulk_process.html'

    def read_template(self):
        return 'organization/read.html'

    # don't override history_template - use group template for history

    def edit_template(self):
        return 'organization/edit.html'

    def activity_template(self):
        return 'organization/activity_stream.html'

_default_organization_plugin = DefaultOrganizationForm()
