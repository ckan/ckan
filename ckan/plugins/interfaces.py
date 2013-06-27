"""
Interfaces for plugins system
"""

__all__ = [
    'Interface',
    'IGenshiStreamFilter', 'IRoutes',
    'IMapper', 'ISession',
    'IMiddleware',
    'IAuthFunctions',
    'IDomainObjectModification', 'IGroupController',
    'IOrganizationController',
    'IPackageController', 'IPluginObserver',
    'IConfigurable', 'IConfigurer',
    'IActions', 'IResourceUrlChange', 'IDatasetForm',
    'IResourcePreview',
    'IGroupForm',
    'ITagController',
    'ITemplateHelpers',
    'IFacets',
    'IAuthenticator',
]

from inspect import isclass
from pyutilib.component.core import Interface as _pca_Interface


class Interface(_pca_Interface):

    @classmethod
    def provided_by(cls, instance):
        return cls.implemented_by(instance.__class__)

    @classmethod
    def implemented_by(cls, other):
        if not isclass(other):
            raise TypeError("Class expected", other)
        try:
            return cls in other._implements
        except AttributeError:
            return False


class IMiddleware(Interface):
    '''Hook into Pylons middleware stack
    '''
    def make_middleware(self, app, config):
        '''Return an app configured with this middleware
        '''
        return app


class IGenshiStreamFilter(Interface):
    '''
    Hook into template rendering.
    See ckan.lib.base.py:render
    '''

    def filter(self, stream):
        """
        Return a filtered Genshi stream.
        Called when any page is rendered.

        :param stream: Genshi stream of the current output document
        :returns: filtered Genshi stream
        """
        return stream


class IRoutes(Interface):
    """
    Plugin into the setup of the routes map creation.

    """
    def before_map(self, map):
        """
        Called before the routes map is generated. ``before_map`` is before any
        other mappings are created so can override all other mappings.

        :param map: Routes map object
        :returns: Modified version of the map object
        """
        return map

    def after_map(self, map):
        """
        Called after routes map is set up. ``after_map`` can be used to
        add fall-back handlers.

        :param map: Routes map object
        :returns: Modified version of the map object
        """
        return map


class IMapper(Interface):
    """
    A subset of the SQLAlchemy mapper extension hooks.
    See http://www.sqlalchemy.org/docs/05/reference/orm/interfaces.html#sqlalchemy.orm.interfaces.MapperExtension

    Example::

        >>> class MyPlugin(SingletonPlugin):
        ...
        ...     implements(IMapper)
        ...
        ...     def after_update(self, mapper, connection, instance):
        ...         log("Updated: %r", instance)
    """

    def before_insert(self, mapper, connection, instance):
        """
        Receive an object instance before that instance is INSERTed into
        its table.
        """

    def before_update(self, mapper, connection, instance):
        """
        Receive an object instance before that instance is UPDATEed.
        """

    def before_delete(self, mapper, connection, instance):
        """
        Receive an object instance before that instance is DELETEed.
        """

    def after_insert(self, mapper, connection, instance):
        """
        Receive an object instance after that instance is INSERTed.
        """

    def after_update(self, mapper, connection, instance):
        """
        Receive an object instance after that instance is UPDATEed.
        """

    def after_delete(self, mapper, connection, instance):
        """
        Receive an object instance after that instance is DELETEed.
        """


class ISession(Interface):
    """
    A subset of the SQLAlchemy session extension hooks.
    """

    def after_begin(self, session, transaction, connection):
        """
        Execute after a transaction is begun on a connection
        """

    def before_flush(self, session, flush_context, instances):
        """
        Execute before flush process has started.
        """

    def after_flush(self, session, flush_context):
        """
        Execute after flush has completed, but before commit has been called.
        """

    def before_commit(self, session):
        """
        Execute right before commit is called.
        """

    def after_commit(self, session):
        """
        Execute after a commit has occured.
        """

    def after_rollback(self, session):
        """
        Execute after a rollback has occured.
        """


class IDomainObjectModification(Interface):
    """
    Receives notification of new, changed and deleted datesets.
    """

    def notify(self, entity, operation):
        pass


class IResourceUrlChange(Interface):
    """
    Receives notification of changed urls.
    """

    def notify(self, resource):
        pass


class IResourcePreview(Interface):
    """
    Hook into the resource previews in helpers.py. This lets you
    create custom previews for example for xml files.
    """

    def can_preview(self, data_dict):
        '''
        Returns info on whether the plugin can preview the resource.

        This can be done in two ways.
        The old way is to just return True or False.
        The new way is to return a dict with the following
        {
            'can_preview': bool - if the extension can preview the resource
            'fixable': string - if the extension cannot preview but could for
                                example if the resource_proxy was enabled.
            'quality': int - how good the preview is 1-poor, 2-average, 3-good
                          used if multiple extensions can preview
        }

        The ``data_dict`` contains the resource and the package.

        Make sure to ckeck the ``on_same_domain`` value of the
        resource or the url if your preview requires the resource to be on
        the same domain because of the same origin policy.
        To find out how to preview resources that are on a
        different domain, read :ref:`resource_proxy`.
        '''

    def setup_template_variables(self, context, data_dict):
        '''
        Add variables to c just prior to the template being rendered.
        The ``data_dict`` contains the resource and the package.

        Change the url to a proxied domain if necessary.
        '''

    def preview_template(self, context, data_dict):
        '''
        Returns a string representing the location of the template to be
        rendered for the read page.
        The ``data_dict`` contains the resource and the package.
        '''


class ITagController(Interface):
    '''
    Hook into the Tag controller. These will usually be called just before
    committing or returning the respective object, i.e. all validation,
    synchronization and authorization setup are complete.

    '''
    def before_view(self, tag_dict):
        '''
        Extensions will recieve this before the tag gets displayed. The
        dictionary passed will be the one that gets sent to the template.

        '''
        return tag_dict


class IGroupController(Interface):
    """
    Hook into the Group controller. These will
    usually be called just before committing or returning the
    respective object, i.e. all validation, synchronization
    and authorization setup are complete.
    """

    def read(self, entity):
        pass

    def create(self, entity):
        pass

    def edit(self, entity):
        pass

    def authz_add_role(self, object_role):
        pass

    def authz_remove_role(self, object_role):
        pass

    def delete(self, entity):
        pass

    def before_view(self, pkg_dict):
        '''
             Extensions will recieve this before the group gets
             displayed. The dictionary passed will be the one that gets
             sent to the template.
        '''
        return pkg_dict


class IOrganizationController(Interface):
    """
    Hook into the Organization controller. These will
    usually be called just before committing or returning the
    respective object, i.e. all validation, synchronization
    and authorization setup are complete.
    """

    def read(self, entity):
        pass

    def create(self, entity):
        pass

    def edit(self, entity):
        pass

    def authz_add_role(self, object_role):
        pass

    def authz_remove_role(self, object_role):
        pass

    def delete(self, entity):
        pass

    def before_view(self, pkg_dict):
        '''
             Extensions will recieve this before the organization gets
             displayed. The dictionary passed will be the one that gets
             sent to the template.
        '''
        return pkg_dict


class IPackageController(Interface):
    """
    Hook into the package controller.
    (see IGroupController)
    """

    def read(self, entity):
        pass

    def create(self, entity):
        pass

    def edit(self, entity):
        pass

    def authz_add_role(self, object_role):
        pass

    def authz_remove_role(self, object_role):
        pass

    def delete(self, entity):
        pass

    def after_create(self, context, pkg_dict):
        '''
            Extensions will receive the validated data dict after the package
            has been created (Note that the create method will return a package
            domain object, which may not include all fields). Also the newly
            created package id will be added to the dict.
        '''
        pass

    def after_update(self, context, pkg_dict):
        '''
            Extensions will receive the validated data dict after the package
            has been updated (Note that the edit method will return a package
            domain object, which may not include all fields).
        '''
        pass

    def after_delete(self, context, pkg_dict):
        '''
            Extensions will receive the data dict (tipically containing
            just the package id) after the package has been deleted.
        '''
        pass

    def after_show(self, context, pkg_dict):
        '''
            Extensions will receive the validated data dict after the package
            is ready for display (Note that the read method will return a
            package domain object, which may not include all fields).
        '''
        pass

    def before_search(self, search_params):
        '''
            Extensions will receive a dictionary with the query parameters,
            and should return a modified (or not) version of it.

            search_params will include an `extras` dictionary with all values
            from fields starting with `ext_`, so extensions can receive user
            input from specific fields.

        '''
        return search_params

    def after_search(self, search_results, search_params):
        '''
            Extensions will receive the search results, as well as the search
            parameters, and should return a modified (or not) object with the
            same structure:

                {'count': '', 'results': '', 'facets': ''}

            Note that count and facets may need to be adjusted if the extension
            changed the results for some reason.

            search_params will include an `extras` dictionary with all values
            from fields starting with `ext_`, so extensions can receive user
            input from specific fields.

        '''

        return search_results

    def before_index(self, pkg_dict):
        '''
             Extensions will receive what will be given to the solr for
             indexing. This is essentially a flattened dict (except for
             multli-valued fields such as tags) of all the terms sent to
             the indexer. The extension can modify this by returning an
             altered version.
        '''
        return pkg_dict

    def before_view(self, pkg_dict):
        '''
             Extensions will recieve this before the dataset gets
             displayed. The dictionary passed will be the one that gets
             sent to the template.
        '''
        return pkg_dict


class IPluginObserver(Interface):
    """
    Plugin to the plugin loading mechanism
    """

    def before_load(self, plugin):
        """
        Called before a plugin is loaded
        This method is passed the plugin class.
        """

    def after_load(self, service):
        """
        Called after a plugin has been loaded.
        This method is passed the instantiated service object.
        """

    def before_unload(self, plugin):
        """
        Called before a plugin is loaded
        This method is passed the plugin class.
        """

    def after_unload(self, service):
        """
        Called after a plugin has been unloaded.
        This method is passed the instantiated service object.
        """


class IConfigurable(Interface):
    """
    Pass configuration to plugins and extensions
    """

    def configure(self, config):
        """
        Called by load_environment
        """


class IConfigurer(Interface):
    """
    Configure CKAN (pylons) environment via the ``pylons.config`` object
    """

    def update_config(self, config):
        """
        Called by load_environment at earliest point when config is
        available to plugins. The config should be updated in place.

        :param config: ``pylons.config`` object
        """


class IActions(Interface):
    """
    Allow adding of actions to the logic layer.
    """
    def get_actions(self):
        """
        Should return a dict, the keys being the name of the logic
        function and the values being the functions themselves.

        By decorating a function with the `ckan.logic.side_effect_free`
        decorator, the associated action will be made available by a GET
        request (as well as the usual POST request) through the action API.
        """


class IAuthFunctions(Interface):
    """
    Allow customisation of default Authorization implementation
    """
    def get_auth_functions(self):
        """
        Returns a dict of all the authorization functions which the
        implementation overrides
        """


class ITemplateHelpers(Interface):
    '''Add custom template helper functions.

    By implementing this plugin interface plugins can provide their own
    template helper functions, which custom templates can then access via the
    ``h`` variable.

    See ``ckanext/example_itemplatehelpers`` for an example plugin.

    '''
    def get_helpers(self):
        '''Return a dict mapping names to helper functions.

        The keys of the dict should be the names with which the helper
        functions will be made available to templates, and the values should be
        the functions themselves. For example, a dict like:
        ``{'example_helper': example_helper}`` allows templates to access the
        ``example_helper`` function via ``h.example_helper()``.

        Function names should start with the name of the extension providing
        the function, to prevent name clashes between extensions.

        '''


class IDatasetForm(Interface):
    '''Customize CKAN's dataset (package) schemas and forms.

    By implementing this interface plugins can customise CKAN's dataset schema,
    for example to add new custom fields to datasets.

    Multiple IDatasetForm plugins can be used at once, each plugin associating
    itself with different package types using the ``package_types()`` and
    ``is_fallback()`` methods below, and then providing different schemas and
    templates for different types of dataset.  When a package controller action
    is invoked, the ``type`` field of the package will determine which
    IDatasetForm plugin (if any) gets delegated to.

    When implementing IDatasetForm, you can inherit from
    ``ckan.plugins.toolkit.DefaultDatasetForm``, which provides default
    implementations for each of the methods defined in this interface.

    See ``ckanext/example_idatasetform`` for an example plugin.

    '''
    def package_types(self):
        '''Return an iterable of package types that this plugin handles.

        If a request involving a package of one of the returned types is made,
        then this plugin instance will be delegated to.

        There cannot be two IDatasetForm plugins that return the same package
        type, if this happens then CKAN will raise an exception at startup.

        :rtype: iterable of strings

        '''

    def is_fallback(self):
        '''Return ``True`` if this plugin is the fallback plugin.

        When no IDatasetForm plugin's ``package_types()`` match the ``type`` of
        the package being processed, the fallback plugin is delegated to
        instead.

        There cannot be more than one IDatasetForm plugin whose
        ``is_fallback()`` method returns ``True``, if this happens CKAN will
        raise an exception at startup.

        If no IDatasetForm plugin's ``is_fallback()`` method returns ``True``,
        CKAN will use ``DefaultDatasetForm`` as the fallback.

        :rtype: boolean

        '''

    def create_package_schema(self):
        '''Return the schema for validating new dataset dicts.

        CKAN will use the returned schema to validate and convert data coming
        from users (via the dataset form or API) when creating new datasets,
        before entering that data into the database.

        If it inherits from ``ckan.plugins.toolkit.DefaultDatasetForm``, a
        plugin can call ``DefaultDatasetForm``'s ``create_package_schema()``
        method to get the default schema and then modify and return it.

        CKAN's ``convert_to_tags()`` or ``convert_to_extras()`` functions can
        be used to convert custom fields into dataset tags or extras for
        storing in the database.

        See ``ckanext/example_idatasetform`` for examples.

        :returns: a dictionary mapping dataset dict keys to lists of validator
          and converter functions to be applied to those keys
        :rtype: dictionary

        '''

    def update_package_schema(self):
        '''Return the schema for validating updated dataset dicts.

        CKAN will use the returned schema to validate and convert data coming
        from users (via the dataset form or API) when updating datasets, before
        entering that data into the database.

        If it inherits from ``ckan.plugins.toolkit.DefaultDatasetForm``, a
        plugin can call ``DefaultDatasetForm``'s ``update_package_schema()``
        method to get the default schema and then modify and return it.

        CKAN's ``convert_to_tags()`` or ``convert_to_extras()`` functions can
        be used to convert custom fields into dataset tags or extras for
        storing in the database.

        See ``ckanext/example_idatasetform`` for examples.

        :returns: a dictionary mapping dataset dict keys to lists of validator
          and converter functions to be applied to those keys
        :rtype: dictionary

        '''

    def show_package_schema(self):
        '''
        Return a schema to validate datasets before they're shown to the user.

        CKAN will use the returned schema to validate and convert data coming
        from the database before it is returned to the user via the API or
        passed to a template for rendering.

        If it inherits from ``ckan.plugins.toolkit.DefaultDatasetForm``, a
        plugin can call ``DefaultDatasetForm``'s ``show_package_schema()``
        method to get the default schema and then modify and return it.

        If you have used ``convert_to_tags()`` or ``convert_to_extras()`` in
        your ``create_package_schema()`` and ``update_package_schema()`` then
        you should use ``convert_from_tags()`` or ``convert_from_extras()`` in
        your ``show_package_schema()`` to convert the tags or extras in the
        database back into your custom dataset fields.

        See ``ckanext/example_idatasetform`` for examples.

        :returns: a dictionary mapping dataset dict keys to lists of validator
          and converter functions to be applied to those keys
        :rtype: dictionary

        '''

    def setup_template_variables(self, context, data_dict):
        '''Add variables to the template context for use in templates.

        This function is called before a dataset template is rendered. If you
        have custom dataset templates that require some additional variables,
        you can add them to the template context ``ckan.plugins.toolkit.c``
        here and they will be available in your templates. See
        ``ckanext/example_idatasetform`` for an example.

        '''

    def new_template(self):
        '''Return the path to the template for the new dataset page.

        The path should be relative to the plugin's templates dir, e.g.
        ``'package/new.html'``.

        :rtype: string

        '''

    def read_template(self):
        '''Return the path to the template for the dataset read page.

        The path should be relative to the plugin's templates dir, e.g.
        ``'package/read.html'``.

        :rtype: string

        '''

    def edit_template(self):
        '''Return the path to the template for the dataset edit page.

        The path should be relative to the plugin's templates dir, e.g.
        ``'package/edit.html'``.

        :rtype: string

        '''

    def search_template(self):
        '''Return the path to the template for use in the dataset search page.

        This template is used to render each dataset that is listed in the
        search results on the dataset search page.

        The path should be relative to the plugin's templates dir, e.g.
        ``'package/search.html'``.

        :rtype: string

        '''

    def history_template(self):
        '''Return the path to the template for the dataset history page.

        The path should be relative to the plugin's templates dir, e.g.
        ``'package/history.html'``.

        :rtype: string

        '''

    def package_form(self):
        '''Return the path to the template for the dataset form.

        The path should be relative to the plugin's templates dir, e.g.
        ``'package/form.html'``.

        :rtype: string

        '''


class IGroupForm(Interface):
    """
    Allows customisation of the group controller as a plugin.

    The behaviour of the plugin is determined by 5 method hooks:

     - package_form(self)
     - form_to_db_schema(self)
     - db_to_form_schema(self)
     - check_data_dict(self, data_dict)
     - setup_template_variables(self, context, data_dict)

    Furthermore, there can be many implementations of this plugin registered
    at once.  With each instance associating itself with 0 or more package
    type strings.  When a package controller action is invoked, the package
    type determines which of the registered plugins to delegate to.  Each
    implementation must implement two methods which are used to determine the
    package-type -> plugin mapping:

     - is_fallback(self)
     - package_types(self)

    Implementations might want to consider mixing in
    ckan.lib.plugins.DefaultGroupForm which provides
    default behaviours for the 5 method hooks.

    """

    ##### These methods control when the plugin is delegated to          #####

    def is_fallback(self):
        """
        Returns true iff this provides the fallback behaviour, when no other
        plugin instance matches a package's type.

        There must be exactly one fallback controller defined, any attempt to
        register more than one will throw an exception at startup.  If there's
        no fallback registered at startup the
        ckan.lib.plugins.DefaultGroupForm used as the fallback.
        """

    def group_types(self):
        """
        Returns an iterable of group type strings.

        If a request involving a package of one of those types is made, then
        this plugin instance will be delegated to.

        There must only be one plugin registered to each group type.  Any
        attempts to register more than one plugin instance to a given group
        type will raise an exception at startup.
        """

    ##### End of control methods

    ##### Hooks for customising the PackageController's behaviour        #####
    ##### TODO: flesh out the docstrings a little more.                  #####
    def new_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the 'new' page. Uses the default_group_type configuration
        option to determine which plugin to use the template from.
        """

    def index_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the index page. Uses the default_group_type configuration
        option to determine which plugin to use the template from.
        """

    def read_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the read page
        """

    def history_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the history page
        """

    def edit_template(self):
        """
        Returns a string representing the location of the template to be
        rendered for the edit page
        """

    def package_form(self):
        """
        Returns a string representing the location of the template to be
        rendered.  e.g. "group/new_group_form.html".
        """

    def form_to_db_schema(self):
        """
        Returns the schema for mapping group data from a form to a format
        suitable for the database.
        """

    def db_to_form_schema(self):
        """
        Returns the schema for mapping group data from the database into a
        format suitable for the form (optional)
        """

    def check_data_dict(self, data_dict):
        """
        Check if the return data is correct.

        raise a DataError if not.
        """

    def setup_template_variables(self, context, data_dict):
        """
        Add variables to c just prior to the template being rendered.
        """

    ##### End of hooks                                                   #####

class IFacets(Interface):
    ''' Allows specify which facets are displayed and also the names used.

    facet_dicts are in the form {'facet_name': 'display name', ...}
    to allow translatable display names use _(...)
    eg {'facet_name': _('display name'), ...} and ensure that this is
    created each time the function is called.

    The dict supplied is actually an ordered dict.
    '''

    def dataset_facets(self, facets_dict, package_type):
        ''' Update the facets_dict and return it. '''
        return facets_dict

    def group_facets(self, facets_dict, group_type, package_type):
        ''' Update the facets_dict and return it. '''
        return facets_dict

    def organization_facets(self, facets_dict, organization_type, package_type):
        ''' Update the facets_dict and return it. '''
        return facets_dict


class IAuthenticator(Interface):
    '''EXPERIMENTAL

    Allows custom authentication methods to be integrated into CKAN.
    Currently it is experimental and the interface may change.'''


    def identify(self):
        '''called to identify the user.

        If the user is identfied then it should set
        c.user: The id of the user
        c.userobj: The actual user object (this may be removed as a
        requirement in a later release so that access to the model is not
        required)
        '''

    def login(self):
        '''called at login.'''

    def logout(self):
        '''called at logout.'''

    def abort(self, status_code, detail, headers, comment):
        '''called on abort.  This allows aborts due to authorization issues
        to be overriden'''
        return (status_code, detail, headers, comment)
