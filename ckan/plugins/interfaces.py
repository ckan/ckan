# encoding: utf-8

u'''A collection of interfaces that CKAN plugins can implement to customize and
extend CKAN.

'''
from __future__ import annotations

from typing import (Any, Callable, Iterable, Mapping, Optional, Sequence,
                    TYPE_CHECKING, Type, Union)

from pyutilib.component.core import Interface as _pca_Interface

from flask.blueprints import Blueprint
from flask.wrappers import Response

from ckan.model.user import User
from ckan.types import (
    Action, AuthFunction, Context, DataDict, PFeedFactory,
    PUploader, PResourceUploader, Schema, SignalMapping, Validator,
    CKANApp)

if TYPE_CHECKING:
    import click
    import ckan.model as model

    from collections import OrderedDict
    from ckan.common import CKANConfig
    from ckan.config.middleware.flask_app import CKANFlask
    from ckan.config.declaration import Declaration, Key
    from .core import SingletonPlugin


__all__ = [
    u'Interface',
    u'IMiddleware',
    u'IAuthFunctions',
    u'IDomainObjectModification',
    u'IFeed',
    u'IGroupController',
    u'IOrganizationController',
    u'IPackageController',
    u'IPluginObserver',
    u'IConfigurable',
    u'IConfigDeclaration',
    u'IConfigurer',
    u'IActions',
    u'IResourceUrlChange',
    u'IDatasetForm',
    u'IValidators',
    u'IResourceView',
    u'IResourceController',
    u'IGroupForm',
    u'ITagController',
    u'ITemplateHelpers',
    u'IFacets',
    u'IAuthenticator',
    u'ITranslation',
    u'IUploader',
    u'IBlueprint',
    u'IPermissionLabels',
    u'IForkObserver',
    u'IApiToken',
    u'IClick',
    u'ISignal',
]


class Interface(_pca_Interface):
    u'''Base class for custom interfaces.

    Marker base class for extension point interfaces.  This class
    is not intended to be instantiated.  Instead, the declaration
    of subclasses of Interface are recorded, and these
    classes are used to define extension points.
    '''

    @classmethod
    def provided_by(cls, instance: "SingletonPlugin") -> bool:
        u'''Check that the object is an instance of the class that implements
        the interface.
        '''
        return cls.implemented_by(instance.__class__)

    @classmethod
    def implemented_by(cls, other: Type["SingletonPlugin"]) -> bool:
        u'''Check whether the class implements the current interface.
        '''
        try:
            return bool(cls in other._implements)
        except AttributeError:
            return False


class IMiddleware(Interface):
    u'''Hook into the CKAN middleware stack

    Note that methods on this interface will be called two times,
    one for the Pylons stack and one for the Flask stack (eventually
    there will be only the Flask stack).
    '''
    def make_middleware(self, app: CKANApp, config: 'CKANConfig') -> CKANApp:
        u'''Return an app configured with this middleware

        When called on the Flask stack, this method will get the actual Flask
        app so plugins wanting to install Flask extensions can do it like
        this::

            import ckan.plugins as p
            from flask_mail import Mail

            class MyPlugin(p.SingletonPlugin):

                p.implements(p.IMiddleware)

                def make_middleware(app, config):

                    mail = Mail(app)

                    return app
        '''
        return app

    def make_error_log_middleware(self, app: 'CKANFlask',
                                  config: 'CKANConfig') -> 'CKANFlask':
        u'''Return an app configured with this error log middleware

        Note that both on the Flask and Pylons middleware stacks, this
        method will receive a wrapped WSGI app, not the actual Flask or
        Pylons app.
        '''
        return app


class IDomainObjectModification(Interface):
    u'''
    Receives notification of new, changed and deleted datasets.
    '''

    def notify(self, entity: Any, operation: str) -> None:
        u'''
        Send a notification on entity modification.

        :param entity: instance of module.Package.
        :param operation: 'new', 'changed' or 'deleted'.
        '''
        pass

    def notify_after_commit(self, entity: Any, operation: Any) -> None:
        u'''
        ** DEPRECATED **

        Supposed to send a notification after entity modification, but it
        doesn't work.

        :param entity: instance of module.Package.
        :param operation: 'new', 'changed' or 'deleted'.
        '''
        pass


class IFeed(Interface):
    """
    For extending the default Atom feeds
    """

    def get_feed_class(self) -> PFeedFactory:
        """
        Allows plugins to provide a custom class to generate feed items.

        :returns: feed class
        :rtype: type

        The feed item generator's constructor is called as follows::

            feed_class(
                feed_title,        # Mandatory
                feed_link,         # Mandatory
                feed_description,  # Mandatory
                language,          # Optional, always set to 'en'
                author_name,       # Optional
                author_link,       # Optional
                feed_guid,         # Optional
                feed_url,          # Optional
                previous_page,     # Optional, url of previous page of feed
                next_page,         # Optional, url of next page of feed
                first_page,        # Optional, url of first page of feed
                last_page,         # Optional, url of last page of feed
            )

        """
        from ckan.views.feed import CKANFeed
        return CKANFeed

    def get_item_additional_fields(
            self, dataset_dict: dict[str, Any]) -> dict[str, Any]:
        """
        Allows plugins to set additional fields on a feed item.

        :param dataset_dict: the dataset metadata
        :type dataset_dict: dictionary
        :returns: the fields to set
        :rtype: dictionary
        """
        return {}


class IResourceUrlChange(Interface):
    u'''
    Receives notification of changed URL on a resource.
    '''

    def notify(self, resource: 'model.Resource') -> None:
        u'''
        Called when a resource url has changed.

        :param resource, instance of model.Resource
        '''
        pass


class IResourceView(Interface):
    u'''Add custom view renderings for different resource types.

    '''
    def info(self) -> dict[str, Any]:
        u'''
        Returns a dictionary with configuration options for the view.

        The available keys are:

        :param name: name of the view type. This should match the name of the
            actual plugin (eg ``image_view`` or ``datatables_view``).
        :param title: title of the view type. Will be displayed on the
            frontend. This should be translatable (ie wrapped with
            ``toolkit._('Title')``).
        :param default_title: default title that will be used if the view is
            created automatically (optional, defaults to 'View').
        :param default_description: default description that will be used if
            the view is created automatically (optional, defaults to '').
        :param icon: icon for the view type. Should be one of the
            `Font Awesome`_ types without the `fa fa-` prefix eg. `compass`
            (optional, defaults to 'picture').
        :param always_available: the view type should be always available when
            creating new views regardless of the format of the resource
            (optional, defaults to False).
        :param iframed: the view template should be iframed before rendering.
            You generally want this option to be True unless the view styles
            and JavaScript don't clash with the main site theme (optional,
            defaults to True).
        :param preview_enabled: the preview button should appear on the edit
            view form. Some view types have their previews integrated with the
            form (optional, defaults to False).
        :param full_page_edit: the edit form should take the full page width
            of the page (optional, defaults to False).
        :param schema: schema to validate extra configuration fields for the
            view (optional). Schemas are defined as a dictionary, with the
            keys being the field name and the values a list of validator
            functions that will get applied to the field. For instance::

                {
                    'offset': [ignore_empty, natural_number_validator],
                    'limit': [ignore_empty, natural_number_validator],
                }

        Example configuration object::

            {'name': 'image_view',
             'title': toolkit._('Image'),
             'schema': {
                'image_url': [ignore_empty, unicode]
             },
             'icon': 'image',
             'always_available': True,
             'iframed': False,
             }

        :returns: a dictionary with the view type configuration
        :rtype: dict

        .. _Font Awesome: https://fontawesome.com/search
        '''
        return {u'name': self.__class__.__name__}

    def can_view(self, data_dict: DataDict) -> bool:
        u'''
        Returns whether the plugin can render a particular resource.

        The ``data_dict`` contains the following keys:

        :param resource: dict of the resource fields
        :param package: dict of the full parent dataset

        :returns: True if the plugin can render a particular resource, False
            otherwise
        :rtype: bool
        '''
        return False

    def setup_template_variables(self, context: Context,
                                 data_dict: DataDict) -> dict[str, Any]:
        u'''
        Adds variables to be passed to the template being rendered.

        This should return a new dict instead of updating the input
        ``data_dict``.

        The ``data_dict`` contains the following keys:

        :param resource_view: dict of the resource view being rendered
        :param resource: dict of the parent resource fields
        :param package: dict of the full parent dataset

        :returns: a dictionary with the extra variables to pass
        :rtype: dict
        '''
        return {}

    def view_template(self, context: Context, data_dict: DataDict) -> str:
        u'''
        Returns a string representing the location of the template to be
        rendered when the view is displayed

        The path will be relative to the template directory you registered
        using the :py:func:`~ckan.plugins.toolkit.add_template_directory`
        on the :py:class:`~ckan.plugins.interfaces.IConfigurer.update_config`
        method, for instance ``views/my_view.html``.

        :param resource_view: dict of the resource view being rendered
        :param resource: dict of the parent resource fields
        :param package: dict of the full parent dataset

        :returns: the location of the view template.
        :rtype: string
        '''
        return ''

    def form_template(self, context: Context, data_dict: DataDict) -> str:
        u'''
        Returns a string representing the location of the template to be
        rendered when the edit view form is displayed

        The path will be relative to the template directory you registered
        using the :py:func:`~ckan.plugins.toolkit.add_template_directory`
        on the :py:class:`~ckan.plugins.interfaces.IConfigurer.update_config`
        method, for instance ``views/my_view_form.html``.

        :param resource_view: dict of the resource view being rendered
        :param resource: dict of the parent resource fields
        :param package: dict of the full parent dataset

        :returns: the location of the edit view form template.
        :rtype: string
        '''
        return ''


class ITagController(Interface):
    u'''
    Hook into the Tag view. These will usually be called just before
    committing or returning the respective object, i.e. when all validation,
    synchronization and authorization setup are complete.

    '''
    def before_view(self, tag_dict: dict[str, Any]) -> dict[str, Any]:
        u'''
        Extensions will receive this before the tag gets displayed. The
        dictionary passed will be the one that gets sent to the template.
        '''
        return tag_dict


class IGroupController(Interface):
    u'''
    Hook into the Group view. These methods will
    usually be called just before committing or returning the
    respective object i.e. when all validation, synchronization
    and authorization setup are complete.
    '''

    def read(self, entity: 'model.Group') -> None:
        u'''Called after IGroupController.before_view inside group_read.
        '''
        pass

    def create(self, entity: 'model.Group') -> None:
        u'''Called after group has been created inside group_create.
        '''
        pass

    def edit(self, entity: 'model.Group') -> None:
        u'''Called after group has been updated inside group_update.
        '''
        pass

    def delete(self, entity: 'model.Group') -> None:
        u'''Called before commit inside group_delete.
        '''
        pass

    def before_view(self, data_dict: DataDict) -> dict[str, Any]:
        u'''
        Extensions will receive this before the group gets
        displayed. The dictionary passed will be the one that gets
        sent to the template.
        '''
        return data_dict


class IOrganizationController(Interface):
    u'''
    Hook into the Organization view. These methods will
    usually be called just before committing or returning the
    respective object i.e. when all validation, synchronization
    and authorization setup are complete.
    '''

    def read(self, entity: 'model.Group') -> None:
        u'''Called after IOrganizationController.before_view inside
        organization_read.
        '''
        pass

    def create(self, entity: 'model.Group') -> None:
        u'''Called after organization had been created inside
        organization_create.
        '''
        pass

    def edit(self, entity: 'model.Group') -> None:
        u'''Called after organization had been updated inside
        organization_update.
        '''
        pass

    def delete(self, entity: 'model.Group') -> None:
        u'''Called before commit inside organization_delete.
        '''
        pass

    def before_view(self, data_dict: DataDict) -> dict[str, Any]:
        u'''
        Extensions will receive this before the organization gets
        displayed. The dictionary passed will be the one that gets
        sent to the template.
        '''
        return data_dict


class IPackageController(Interface):
    u'''
    Hook into the dataset view.
    '''

    def read(self, entity: 'model.Package') -> None:
        u'''
        Called after IPackageController.before_dataset_view inside
        package_show.
        '''
        pass

    def create(self, entity: 'model.Package') -> None:
        u'''Called after the dataset had been created inside package_create.
        '''
        pass

    def edit(self, entity: 'model.Package') -> None:
        u'''Called after the dataset had been updated inside package_update.
        '''
        pass

    def delete(self, entity: 'model.Package') -> None:
        u'''Called before commit inside package_delete.
        '''
        pass

    def after_dataset_create(
            self, context: Context, pkg_dict: dict[str, Any]) -> None:
        u'''
        Extensions will receive the validated data dict after the dataset
        has been created (Note that the create method will return a dataset
        domain object, which may not include all fields). Also the newly
        created dataset id will be added to the dict.
        '''
        pass

    def after_dataset_update(
            self, context: Context, pkg_dict: dict[str, Any]) -> None:
        u'''
        Extensions will receive the validated data dict after the dataset
        has been updated.
        '''
        pass

    def after_dataset_delete(
            self, context: Context, pkg_dict: dict[str, Any]) -> None:
        u'''
        Extensions will receive the data dict (typically containing
        just the dataset id) after the dataset has been deleted.
        '''
        pass

    def after_dataset_show(
            self, context: Context, pkg_dict: dict[str, Any]) -> None:
        u'''
        Extensions will receive the validated data dict after the dataset
        is ready for display.
        '''
        pass

    def before_dataset_search(
            self, search_params: dict[str, Any]) -> dict[str, Any]:
        u'''
        Extensions will receive a dictionary with the query parameters,
        and should return a modified (or not) version of it.

        search_params will include an `extras` dictionary with all values
        from fields starting with `ext_`, so extensions can receive user
        input from specific fields.
        '''
        return search_params

    def after_dataset_search(
            self, search_results: dict[str, Any],
            search_params: dict[str, Any]) -> dict[str, Any]:
        u'''
        Extensions will receive the search results, as well as the search
        parameters, and should return a modified (or not) object with the
        same structure::

            {'count': '', 'results': '', 'search_facets': ''}

        Note that count and facets may need to be adjusted if the extension
        changed the results for some reason.

        search_params will include an `extras` dictionary with all values
        from fields starting with `ext_`, so extensions can receive user
        input from specific fields.

        '''

        return search_results

    def before_dataset_index(self, pkg_dict: dict[str, Any]) -> dict[str, Any]:
        u'''
        Extensions will receive what will be given to Solr for
        indexing. This is essentially a flattened dict (except for
        multi-valued fields such as tags) of all the terms sent to
        the indexer. The extension can modify this by returning an
        altered version.
        '''
        return pkg_dict

    def before_dataset_view(self, pkg_dict: dict[str, Any]) -> dict[str, Any]:
        u'''
        Extensions will receive this before the dataset gets
        displayed. The dictionary passed will be the one that gets
        sent to the template.
        '''
        return pkg_dict


class IResourceController(Interface):
    u'''
    Hook into the resource view.
    '''

    def before_resource_create(
            self, context: Context, resource: dict[str, Any]) -> None:
        u'''
        Extensions will receive this before a resource is created.

        :param context: The context object of the current request, this
            includes for example access to the ``model`` and the ``user``.
        :type context: dictionary
        :param resource: An object representing the resource to be added
            to the dataset (the one that is about to be created).
        :type resource: dictionary
        '''
        pass

    def after_resource_create(
            self, context: Context, resource: dict[str, Any]) -> None:
        u'''
        Extensions will receive this after a resource is created.

        :param context: The context object of the current request, this
            includes for example access to the ``model`` and the ``user``.
        :type context: dictionary
        :param resource: An object representing the latest resource added
            to the dataset (the one that was just created). A key in the
            resource dictionary worth mentioning is ``url_type`` which is
            set to ``upload`` when the resource file is uploaded instead
            of linked.
        :type resource: dictionary
        '''
        pass

    def before_resource_update(self, context: Context, current: dict[str, Any],
                               resource: dict[str, Any]) -> None:
        u'''
        Extensions will receive this before a resource is updated.

        :param context: The context object of the current request, this
            includes for example access to the ``model`` and the ``user``.
        :type context: dictionary
        :param current: The current resource which is about to be updated
        :type current: dictionary
        :param resource: An object representing the updated resource which
            will replace the ``current`` one.
        :type resource: dictionary
        '''
        pass

    def after_resource_update(
            self, context: Context, resource: dict[str, Any]) -> None:
        u'''
        Extensions will receive this after a resource is updated.

        :param context: The context object of the current request, this
            includes for example access to the ``model`` and the ``user``.
        :type context: dictionary
        :param resource: An object representing the updated resource in
            the dataset (the one that was just updated). As with
            ``after_resource_create``, a noteworthy key in the resource
            dictionary ``url_type`` which is set to ``upload`` when the
            resource file is uploaded instead of linked.
        :type resource: dictionary
        '''
        pass

    def before_resource_delete(
            self, context: Context, resource: dict[str, Any],
            resources: list[dict[str, Any]]) -> None:
        u'''
        Extensions will receive this before a resource is deleted.

        :param context: The context object of the current request, this
            includes for example access to the ``model`` and the ``user``.
        :type context: dictionary
        :param resource: An object representing the resource that is about
            to be deleted. This is a dictionary with one key: ``id`` which
            holds the id ``string`` of the resource that should be deleted.
        :type resource: dictionary
        :param resources: The list of resources from which the resource will
            be deleted (including the resource to be deleted if it existed
            in the dataset).
        :type resources: list
        '''
        pass

    def after_resource_delete(
            self, context: Context,
            resources: list[dict[str, Any]]) -> None:
        u'''
        Extensions will receive this after a resource is deleted.

        :param context: The context object of the current request, this
            includes for example access to the ``model`` and the ``user``.
        :type context: dictionary
        :param resources: A list of objects representing the remaining
            resources after a resource has been removed.
        :type resource: list
        '''
        pass

    def before_resource_show(
            self, resource_dict: dict[str, Any]) -> dict[str, Any]:
        u'''
        Extensions will receive the validated data dict before the resource
        is ready for display.

        Be aware that this method is not only called for UI display, but also
        in other methods, like when a resource is deleted, because package_show
        is used to get access to the resources in a dataset.
        '''
        return resource_dict


class IPluginObserver(Interface):
    u'''
    Hook into the plugin loading mechanism itself
    '''

    def before_load(self, plugin: 'SingletonPlugin') -> None:
        u'''
        Called before a plugin is loaded.
        This method is passed the plugin class.
        '''

    def after_load(self, service: Any) -> None:
        u'''
        Called after a plugin has been loaded.
        This method is passed the instantiated service object.
        '''

    def before_unload(self, plugin: 'SingletonPlugin') -> None:
        u'''
        Called before a plugin is loaded.
        This method is passed the plugin class.
        '''

    def after_unload(self, service: Any) -> None:
        u'''
        Called after a plugin has been unloaded.
        This method is passed the instantiated service object.
        '''


class IConfigurable(Interface):
    u'''
    Hook called during the startup of CKAN

    See also :py:class:`IConfigurer`.
    '''
    def configure(self, config: 'CKANConfig') -> None:
        u'''
        Called during CKAN's initialization.

        This function allows plugins to initialize themselves during
        CKAN's initialization. It is called after most of the
        environment (e.g. the database) is already set up.

        Note that this function is not only called during the
        initialization of the main CKAN process but also during the
        execution of paster commands and background jobs, since these
        run in separate processes and are therefore initialized
        independently.

        :param config: dict-like configuration object
        :type config: :py:class:`ckan.common.CKANConfig`
        '''
        return


class IConfigDeclaration(Interface):
    """Register additional configuration options.

    While it's not necessary, declared config options can be printed out using
    CLI or additionally verified in code. This makes the task of adding new
    configuration, removing obsolete config options, checking the sanity of
    config options much simpler for extension consumers.

    """

    def declare_config_options(self, declaration: Declaration, key: Key):
        """Register extra config options.

        Example::

            from ckan.config.declaration import Declaration, Key

            def declare_config_options(
                self, declaration: Declaration, key: Key):

                declaration.annotate("MyExt config section")
                group = key.ckanext.my_ext.feature
                declaration.declare(group.enabled, "no").set_description(
                    "Enables feature"
                )
                declaration.declare(group.mode, "simple").set_description(
                    "Execution mode"
                )

        Run ``ckan config declaration my_ext --include-docs`` and get the
        following config suggestion::

            ## MyExt config section ######################
            # Enables feature
            ckanext.my_ext.feature.enabled = no
            # Execution mode
            ckanext.my_ext.feature.mode = simple

        See :ref:`declare configuration <declare-config-options>` guide for
        details.

        :param declaration:  object containing all the config declarations
        :type declaration: :py:class:`ckan.config.declaration.Declaration`

        :param key: object for generic option access.
        :type key: :py:class:`ckan.config.declaration.Key`

        """


class IConfigurer(Interface):
    u'''
    Configure the CKAN environment via the ``config`` object

    See also :py:class:`IConfigurable`.
    '''

    def update_config(self, config: 'CKANConfig') -> None:
        u'''
        Called by load_environment at the earliest point that config is
        available to plugins. The config should be updated in place.

        :param config: ``config`` object
        '''

    def update_config_schema(self, schema: Schema) -> Schema:
        u'''
        Return a schema with the runtime-editable config options.

        CKAN will use the returned schema to decide which configuration options
        can be edited during runtime (using
        :py:func:`ckan.logic.action.update.config_option_update`) and to
        validate them before storing them.

        Defaults to
        :py:func:`ckan.logic.schema.default_update_configuration_schema`, which
        will be passed to all extensions implementing this method, which can
        add or remove runtime-editable config options to it.

        :param schema: a dictionary mapping runtime-editable configuration
          option keys to lists
          of validator and converter functions to be applied to those keys
        :type schema: dictionary

        :returns: a dictionary mapping runtime-editable configuration option
          keys to lists of
          validator and converter functions to be applied to those keys
        :rtype: dictionary
        '''
        return schema


class IActions(Interface):
    u'''
    Allow adding of actions to the logic layer.
    '''
    def get_actions(self) -> dict[str, Action]:
        u'''
        Should return a dict, the keys being the name of the logic
        function and the values being the functions themselves.

        By decorating a function with the ``ckan.logic.side_effect_free``
        decorator, the associated action will be made available to a GET
        request (as well as the usual POST request) through the Action API.

        By decorating a function with ``ckan.plugins.toolkit.chained_action``,
        the action will 'intercept' calls to an existing action function. This
        allows a plugin to modify the behaviour of an existing action function.
        Chained actions must be defined as
        ``action_function(original_action, context, data_dict)``, where the
        function's name matches the original action function it intercepts, the
        first parameter is the action function it intercepts (in the next
        plugin or in core ckan). The chained action may call the
        original_action function, optionally passing different values, handling
        exceptions, returning different values and/or raising different
        exceptions to the caller. When multiple plugins chain to an action, the
        first plugin declaring is called first, and if it chooses to call the
        original_action, then the chained action in the next plugin to be
        declared next is called, and so on.
        '''
        return {}


class IValidators(Interface):
    u'''
    Add extra validators to be returned by
    :py:func:`ckan.plugins.toolkit.get_validator`.
    '''
    def get_validators(self) -> dict[str, Validator]:
        u'''Return the validator functions provided by this plugin.

        Return a dictionary mapping validator names (strings) to
        validator functions. For example::

            {'valid_shoe_size': shoe_size_validator,
             'valid_hair_color': hair_color_validator}

        These validator functions would then be available when a
        plugin calls :py:func:`ckan.plugins.toolkit.get_validator`.
        '''
        return {}


class IAuthFunctions(Interface):
    u'''Override CKAN's authorization functions, or add new auth functions.'''

    def get_auth_functions(self) -> dict[str, AuthFunction]:
        u'''Return the authorization functions provided by this plugin.

        Return a dictionary mapping authorization function names (strings) to
        functions. For example::

            {'user_create': my_custom_user_create_function,
             'group_create': my_custom_group_create}

        When a user tries to carry out an action via the CKAN API or web
        interface and CKAN or a CKAN plugin calls
        ``check_access('some_action')`` as a result, an authorization function
        named ``'some_action'`` will be searched for in the authorization
        functions registered by plugins and in CKAN's core authorization
        functions (found in ``ckan/logic/auth/``).

        For example when action function ``'package_create'`` is called, a
        ``'package_create'`` authorization function is searched for.

        If an extension registers an authorization function with the same name
        as one of CKAN's default authorization functions (as with
        ``'user_create'`` and ``'group_create'`` above), the extension's
        function will override the default one.

        Each authorization function should take two parameters ``context`` and
        ``data_dict``, and should return a dictionary ``{'success': True}`` to
        authorize the action or ``{'success': False}`` to deny it, for
        example::

            def user_create(context, data_dict=None):
                if (some condition):
                    return {'success': True}
                else:
                    return {'success': False, 'msg': 'Not allowed to register'}

        The context object will contain a ``model`` that can be used to query
        the database, a ``user`` containing the name of the user doing the
        request (or their IP if it is an anonymous web request) and an
        ``auth_user_obj`` containing the actual model.User object (or None if
        it is an anonymous request).

        See ``ckan/logic/auth/`` for more examples.

        Note that by default, all auth functions provided by extensions are
        assumed to require a validated user or API key, otherwise a
        :py:class:`ckan.logic.NotAuthorized`: exception will be raised. This
        check will be performed *before* calling the actual auth function. If
        you want to allow anonymous access to one of your actions, its auth
        function must be decorated with the ``auth_allow_anonymous_access``
        decorator, available in the plugins toolkit.

        For example::

            import ckan.plugins as p

            @p.toolkit.auth_allow_anonymous_access
            def my_search_action(context, data_dict):
                # Note that you can still return {'success': False} if for some
                # reason access is denied.

            def my_create_action(context, data_dict):
                # Unless there is a logged in user or a valid API key provided
                # NotAuthorized will be raised before reaching this function.

        By decorating a registered auth function with the
        ``ckan.plugins.toolkit.chained_auth_function`` decorator you can create
        a chain of auth checks that are completed when auth is requested. This
        chain starts with the last chained auth function to be registered and
        ends with the original auth function (or a non-chained plugin override
        version). Chained auth functions must accept an extra parameter,
        specifically the next auth function in the chain, for example::

            auth_function(next_auth, context, data_dict).

        The chained auth function may call the next_auth function, optionally
        passing different values, handling exceptions, returning different
        values and/or raising different exceptions to the caller.
        '''
        return {}


class ITemplateHelpers(Interface):
    u'''Add custom template helper functions.

    By implementing this plugin interface plugins can provide their own
    template helper functions, which custom templates can then access via the
    ``h`` variable.

    See ``ckanext/example_itemplatehelpers`` for an example plugin.

    '''
    def get_helpers(self) -> dict[str, Callable[..., Any]]:
        u'''Return a dict mapping names to helper functions.

        The keys of the dict should be the names with which the helper
        functions will be made available to templates, and the values should be
        the functions themselves. For example, a dict like:
        ``{'example_helper': example_helper}`` allows templates to access the
        ``example_helper`` function via ``h.example_helper()``.

        Function names should start with the name of the extension providing
        the function, to prevent name clashes between extensions.

        By decorating a registered helper function with the
        ``ckan.plugins.toolkit.chained_helper`` decorator you can
        create a chain of helpers that are called in a sequence. This
        chain starts with the first chained helper to be registered and
        ends with the original helper (or a non-chained plugin
        override version). Chained helpers must accept an extra
        parameter, specifically the next helper in the chain, for
        example::

            helper(next_helper, *args, **kwargs).

        The chained helper function may call the next_helper function,
        optionally passing different values, handling exceptions,
        returning different values and/or raising different exceptions
        to the caller.

        '''
        return {}


class IDatasetForm(Interface):
    u'''Customize CKAN's dataset (package) schemas and forms.

    By implementing this interface plugins can customise CKAN's dataset schema,
    for example to add new custom fields to datasets.

    Multiple IDatasetForm plugins can be used at once, each plugin associating
    itself with different dataset types using the ``package_types()`` and
    ``is_fallback()`` methods below, and then providing different schemas and
    templates for different types of dataset.  When a dataset view action
    is invoked, the ``type`` field of the dataset will determine which
    IDatasetForm plugin (if any) gets delegated to.

    When implementing IDatasetForm, you can inherit from
    ``ckan.plugins.toolkit.DefaultDatasetForm``, which provides default
    implementations for each of the methods defined in this interface.

    See ``ckanext/example_idatasetform`` for an example plugin.

    '''
    def package_types(self) -> Sequence[str]:
        u'''Return an iterable of dataset (package) types that this plugin
        handles.

        If a request involving a dataset of one of the returned types is made,
        then this plugin instance will be delegated to.

        There cannot be two IDatasetForm plugins that return the same dataset
        type, if this happens then CKAN will raise an exception at startup.

        :rtype: iterable of strings

        '''
        return []

    def is_fallback(self) -> bool:
        u'''Return ``True`` if this plugin is the fallback plugin.

        When no IDatasetForm plugin's ``package_types()`` match the ``type`` of
        the dataset being processed, the fallback plugin is delegated to
        instead.

        There cannot be more than one IDatasetForm plugin whose
        ``is_fallback()`` method returns ``True``, if this happens CKAN will
        raise an exception at startup.

        If no IDatasetForm plugin's ``is_fallback()`` method returns ``True``,
        CKAN will use ``DefaultDatasetForm`` as the fallback.

        :rtype: bool

        '''
        return False

    def create_package_schema(self) -> Schema:
        u'''Return the schema for validating new dataset dicts.

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
        return {}

    def update_package_schema(self) -> Schema:
        u'''Return the schema for validating updated dataset dicts.

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
        return {}

    def show_package_schema(self) -> Schema:
        u'''
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
        return {}

    def setup_template_variables(self, context: Context,
                                 data_dict: DataDict) -> None:
        u'''Add variables to the template context for use in dataset templates.

        This function is called before a dataset template is rendered. If you
        have custom dataset templates that require some additional variables,
        you can add them to the template context ``ckan.plugins.toolkit.c``
        here and they will be available in your templates. See
        ``ckanext/example_idatasetform`` for an example.

        '''

    def new_template(self, package_type: str) -> str:
        u'''Return the path to the template for the new dataset page.

        The path should be relative to the plugin's templates dir, e.g.
        ``'package/new.html'``.

        :rtype: string

        '''
        return ''

    def read_template(self, package_type: str) -> str:
        u'''Return the path to the template for the dataset read page.

        The path should be relative to the plugin's templates dir, e.g.
        ``'package/read.html'``.

        If the user requests the dataset in a format other than HTML, then
        CKAN will try to render a template file with the same path as returned
        by this function, but a different filename extension,
        e.g. ``'package/read.rdf'``.  If your extension (or another one)
        does not provide this version of the template file, the user
        will get a 404 error.

        :rtype: string

        '''
        return ''

    def edit_template(self, package_type: str) -> str:
        u'''Return the path to the template for the dataset edit page.

        The path should be relative to the plugin's templates dir, e.g.
        ``'package/edit.html'``.

        :rtype: string

        '''
        return ''

    def search_template(self, package_type: str) -> str:
        u'''Return the path to the template for use in the dataset search page.

        This template is used to render each dataset that is listed in the
        search results on the dataset search page.

        The path should be relative to the plugin's templates dir, e.g.
        ``'package/search.html'``.

        :rtype: string

        '''
        return ''

    def history_template(self, package_type: str) -> str:
        u'''
        .. warning:: This template is removed. The function exists for
            compatibility. It now returns None.

        '''
        return ''

    def resource_template(self, package_type: str) -> str:
        u'''Return the path to the template for the resource read page.

        The path should be relative to the plugin's templates dir, e.g.
        ``'package/resource_read.html'``.

        :rtype: string

        '''
        return ''

    def package_form(self, package_type: str) -> str:
        u'''Return the path to the template for the dataset form.

        The path should be relative to the plugin's templates dir, e.g.
        ``'package/form.html'``.

        :rtype: string

        '''
        return ''

    def resource_form(self, package_type: str) -> str:
        u'''Return the path to the template for the resource form.

        The path should be relative to the plugin's templates dir, e.g.
        ``'package/snippets/resource_form.html'``

        :rtype: string
        '''
        return ''

    def validate(
            self, context: Context, data_dict: DataDict, schema: Schema,
            action: str) -> Optional[tuple[dict[str, Any], dict[str, Any]]]:
        u'''Customize validation of datasets.

        When this method is implemented it is used to perform all validation
        for these datasets. The default implementation calls and returns the
        result from ``ckan.plugins.toolkit.navl_validate``.

        This is an adavanced interface. Most changes to validation should be
        accomplished by customizing the schemas returned from
        ``show_package_schema()``, ``create_package_schema()``
        and ``update_package_schema()``. If you need to have a different
        schema depending on the user or value of any field stored in the
        dataset, or if you wish to use a different method for validation, then
        this method may be used.

        :param context: extra information about the request
        :type context: dictionary
        :param data_dict: the dataset to be validated
        :type data_dict: dictionary
        :param schema: a schema, typically from ``show_package_schema()``,
          ``create_package_schema()`` or ``update_package_schema()``
        :type schema: dictionary
        :param action: ``'package_show'``, ``'package_create'`` or
          ``'package_update'``
        :type action: string
        :returns: (data_dict, errors) where data_dict is the possibly-modified
          dataset and errors is a dictionary with keys matching data_dict
          and lists-of-string-error-messages as values
        :rtype: (dictionary, dictionary)
        '''
        return

    def prepare_dataset_blueprint(self, package_type: str,
                                  blueprint: Blueprint) -> Blueprint:
        u'''Update or replace dataset blueprint for given package type.

        Internally CKAN registers blueprint for every custom dataset
        type. Before default routes added to this blueprint and it
        registered inside application this method is called. It can be
        used either for registration of the view function under new
        path or under existing path(like `/new`), in which case this
        new function will be used instead of default one.

        Note, this blueprint has prefix `/{package_type}`.

        :rtype: flask.Blueprint

        '''
        return blueprint

    def prepare_resource_blueprint(self, package_type: str,
                                   blueprint: Blueprint) -> Blueprint:
        u'''Update or replace resource blueprint for given package type.

        Internally CKAN registers separate resource blueprint for
        every custom dataset type. Before default routes added to this
        blueprint and it registered inside application this method is
        called. It can be used either for registration of the view
        function under new path or under existing path(like `/new`),
        in which case this new function will be used instead of
        default one.

        Note, this blueprint has prefix `/{package_type}/<id>/resource`.

        :rtype: flask.Blueprint

        '''
        return blueprint


class IGroupForm(Interface):
    u'''
    Allows customisation of the group form and its underlying schema.

    The behaviour of the plugin is determined by 5 method hooks:

     - group_form(self)
     - form_to_db_schema(self)
     - db_to_form_schema(self)
     - check_data_dict(self, data_dict)
     - setup_template_variables(self, context, data_dict)

    Furthermore, there can be many implementations of this plugin registered
    at once.  With each instance associating itself with 0 or more group
    type strings.  When a group form action is invoked, the group
    type determines which of the registered plugins to delegate to.  Each
    implementation must implement these methods which are used to determine the
    group-type -> plugin mapping:

     - is_fallback(self)
     - group_types(self)
     - group_controller(self)

    Implementations might want to consider mixing in
    ckan.lib.plugins.DefaultGroupForm which provides
    default behaviours for the 5 method hooks.

    '''

    # These methods control when the plugin is delegated to ###################

    def is_fallback(self) -> bool:
        u'''
        Returns true if this provides the fallback behaviour, when no other
        plugin instance matches a group's type.

        There must be exactly one fallback view defined, any attempt to
        register more than one will throw an exception at startup.  If there's
        no fallback registered at startup the
        ckan.lib.plugins.DefaultGroupForm used as the fallback.
        '''
        return False

    def group_types(self) -> Iterable[str]:
        u'''
        Returns an iterable of group type strings.

        If a request involving a group of one of those types is made, then
        this plugin instance will be delegated to.

        There must only be one plugin registered to each group type.  Any
        attempts to register more than one plugin instance to a given group
        type will raise an exception at startup.
        '''
        return []

    def group_controller(self) -> str:
        u'''
        Returns the name of the group view

        The group view is the view, that is used to handle requests
        of the group type(s) of this plugin.

        If this method is not provided, the default group view is used
        (`group`).
        '''
        return 'group'

    # End of control methods ##################################################

    # Hooks for customising the GroupController's behaviour          ##########
    # TODO: flesh out the docstrings a little more
    def new_template(self, group_type: str) -> str:
        u'''
        Returns a string representing the location of the template to be
        rendered for the 'new' page. Uses the default_group_type configuration
        option to determine which plugin to use the template from.
        '''
        return ''

    def index_template(self, group_type: str) -> str:
        u'''
        Returns a string representing the location of the template to be
        rendered for the index page. Uses the default_group_type configuration
        option to determine which plugin to use the template from.
        '''
        return ''

    def read_template(self, group_type: str) -> str:
        u'''
        Returns a string representing the location of the template to be
        rendered for the read page
        '''
        return ''

    def history_template(self, group_type: str) -> str:
        u'''
        Returns a string representing the location of the template to be
        rendered for the history page
        '''
        return ''

    def edit_template(self, group_type: str) -> str:
        u'''
        Returns a string representing the location of the template to be
        rendered for the edit page
        '''
        return ''

    def group_form(self, group_type: str) -> str:
        u'''
        Returns a string representing the location of the template to be
        rendered.  e.g. ``group/new_group_form.html``.
        '''
        return ''

    def form_to_db_schema(self) -> Schema:
        u'''
        Returns the schema for mapping group data from a form to a format
        suitable for the database.
        '''
        return {}

    def db_to_form_schema(self) -> Schema:
        u'''
        Returns the schema for mapping group data from the database into a
        format suitable for the form (optional)
        '''
        return {}

    def check_data_dict(self,
                        data_dict: DataDict,
                        schema: Optional[Schema] = None) -> None:
        u'''
        Check if the return data is correct.

        raise a DataError if not.
        '''

    def setup_template_variables(self, context: Context,
                                 data_dict: DataDict) -> None:
        u'''
        Add variables to c just prior to the template being rendered.
        '''

    def validate(
            self, context: Context, data_dict: DataDict, schema: Schema,
            action: str) -> Optional[tuple[dict[str, Any], dict[str, Any]]]:
        u'''Customize validation of groups.

        When this method is implemented it is used to perform all validation
        for these groups. The default implementation calls and returns the
        result from ``ckan.plugins.toolkit.navl_validate``.

        This is an adavanced interface. Most changes to validation should be
        accomplished by customizing the schemas returned from
        ``form_to_db_schema()`` and ``db_to_form_schema()``
        If you need to have a different
        schema depending on the user or value of any field stored in the
        group, or if you wish to use a different method for validation, then
        this method may be used.

        :param context: extra information about the request
        :type context: dictionary
        :param data_dict: the group to be validated
        :type data_dict: dictionary
        :param schema: a schema, typically from ``form_to_db_schema()``,
          or ``db_to_form_schema()``
        :type schema: dictionary
        :param action: ``'group_show'``, ``'group_create'``,
          ``'group_update'``, ``'organization_show'``,
          ``'organization_create'`` or ``'organization_update'``
        :type action: string
        :returns: (data_dict, errors) where data_dict is the possibly-modified
          group and errors is a dictionary with keys matching data_dict
          and lists-of-string-error-messages as values
        :rtype: (dictionary, dictionary)
        '''
        return

    def prepare_group_blueprint(self, group_type: str,
                                blueprint: Blueprint) -> Blueprint:
        u'''Update or replace group blueprint for given group type.

        Internally CKAN registers separate blueprint for
        every custom group type. Before default routes added to this
        blueprint and it registered inside application this method is
        called. It can be used either for registration of the view
        function under new path or under existing path(like `/new`),
        in which case this new function will be used instead of
        default one.

        Note, this blueprint has prefix `/{group_type}`.

        :rtype: flask.Blueprint

        '''
        return blueprint

    # End of hooks ############################################################


class IFacets(Interface):
    u'''Customize the search facets shown on search pages.

    By implementing this interface plugins can customize the search facets that
    are displayed for filtering search results on the dataset search page,
    organization pages and group pages.

    The ``facets_dict`` passed to each of the functions below is an
    ``OrderedDict`` in which the keys are CKAN's internal names for the facets
    and the values are the titles that will be shown for the facets in the web
    interface. The order of the keys in the dict determine the order that
    facets appear in on the page.  For example::

        {'groups': _('Groups'),
         'tags': _('Tags'),
         'res_format': _('Formats'),
         'license': _('License')}

    To preserve ordering, make sure to add new facets to the existing dict
    rather than updating it, ie do this::

        facets_dict['groups'] = p.toolkit._('Publisher')
        facets_dict['secondary_publisher'] = p.toolkit._('Secondary Publisher')

    rather than this::

        facets_dict.update({
           'groups': p.toolkit._('Publisher'),
           'secondary_publisher': p.toolkit._('Secondary Publisher'),
        })

    Dataset searches can be faceted on any field in the dataset schema that it
    makes sense to facet on. This means any dataset field that is in CKAN's
    Solr search index, basically any field that you see returned by
    :py:func:`~ckan.logic.action.get.package_show`.

    If there are multiple ``IFacets`` plugins active at once, each plugin will
    be called (in the order that they're listed in the CKAN config file) and
    they will each be able to modify the facets dict in turn.

    '''
    def dataset_facets(self,
                       facets_dict: 'OrderedDict[str, Any]',
                       package_type: str) -> 'OrderedDict[str, Any]':
        u'''Modify and return the ``facets_dict`` for the dataset search page.

        The ``package_type`` is the type of dataset that these facets apply to.
        Plugins can provide different search facets for different types of
        dataset. See :py:class:`~ckan.plugins.interfaces.IDatasetForm`.

        :param facets_dict: the search facets as currently specified
        :type facets_dict: OrderedDict

        :param package_type: the dataset type that these facets apply to
        :type package_type: string

        :returns: the updated ``facets_dict``
        :rtype: OrderedDict

        '''
        return facets_dict

    def group_facets(self, facets_dict: 'OrderedDict[str, Any]',
                     group_type: str, package_type: Optional[str]
                     ) -> 'OrderedDict[str, Any]':
        u'''Modify and return the ``facets_dict`` for a group's page.

        The ``package_type`` is the type of dataset that these facets apply to.
        Plugins can provide different search facets for different types of
        dataset. See :py:class:`~ckan.plugins.interfaces.IDatasetForm`.

        The ``group_type`` is the type of group that these facets apply to.
        Plugins can provide different search facets for different types of
        group. See :py:class:`~ckan.plugins.interfaces.IGroupForm`.

        :param facets_dict: the search facets as currently specified
        :type facets_dict: OrderedDict

        :param group_type: the group type that these facets apply to
        :type group_type: string

        :param package_type: the dataset type that these facets apply to
        :type package_type: string

        :returns: the updated ``facets_dict``
        :rtype: OrderedDict

        '''
        return facets_dict

    def organization_facets(
            self, facets_dict: 'OrderedDict[str, Any]', organization_type: str,
            package_type: Optional[str]) -> 'OrderedDict[str, Any]':
        u'''Modify and return the ``facets_dict`` for an organization's page.

        The ``package_type`` is the type of dataset that these facets apply to.
        Plugins can provide different search facets for different types of
        dataset. See :py:class:`~ckan.plugins.interfaces.IDatasetForm`.

        The ``organization_type`` is the type of organization that these facets
        apply to.  Plugins can provide different search facets for different
        types of organization. See
        :py:class:`~ckan.plugins.interfaces.IGroupForm`.

        :param facets_dict: the search facets as currently specified
        :type facets_dict: OrderedDict

        :param organization_type: the organization type that these facets apply
                                  to
        :type organization_type: string

        :param package_type: the dataset type that these facets apply to
        :type package_type: string

        :returns: the updated ``facets_dict``
        :rtype: OrderedDict

        '''
        return facets_dict


class IAuthenticator(Interface):
    u'''Allows custom authentication methods to be integrated into CKAN.

        All interface methods except for the ``abort()`` one support
        returning a Flask response object. This can be used for instance to
        issue redirects or set cookies in the response. If a response object
        is returned there will be no further processing of the current request
        and that response will be returned. This can be used by plugins to:

        * Issue a redirect::

            def identify(self):

                return toolkit.redirect_to('myplugin.custom_endpoint')

        * Set or clear cookies (or headers)::

            from Flask import make_response

            def identify(self)::

                response = make_response(toolkit.render('my_page.html'))
                response.set_cookie(cookie_name, expires=0)

                return response

    '''

    def identify(self) -> Optional[Response]:
        u'''Called to identify the user.

        If the user is identified then it should set:

         - g.user: The name of the user
         - g.userobj: The actual user object

        Alternatively, plugins can return a response object in order to prevent
        the default CKAN authorization flow. See
        the :py:class:`~ckan.plugins.interfaces.IAuthenticator` documentation
        for more details.

        '''

    def login(self) -> Optional[Response]:
        u'''Called before the login starts (that is before asking the user for
        user name and a password in the default authentication).

        Plugins can return a response object to prevent the default CKAN
        authorization flow. See
        the :py:class:`~ckan.plugins.interfaces.IAuthenticator` documentation
        for more details.
        '''

    def logout(self) -> Optional[Response]:
        u'''Called before the logout starts (that is before clicking the logout
        button in the default authentication).

        Plugins can return a response object to prevent the default CKAN
        authorization flow. See
        the :py:class:`~ckan.plugins.interfaces.IAuthenticator` documentation
        for more details.
        '''

    def abort(
        self,
        status_code: int,
        detail: str,
        headers: Optional[dict[str, Any]],
        comment: Optional[str],
    ) -> tuple[int, str, Optional[dict[str, Any]], Optional[str]]:
        """Called on abort.  This allows aborts due to authorization issues
        to be overridden"""
        return (status_code, detail, headers, comment)

    def authenticate(
        self, identity: 'Mapping[str, Any]'
    ) -> Optional["User"]:
        """Called before the authentication starts
        (that is after clicking the login button)

        Plugins should return a user object if the authentication was
        successful, or ``None``` otherwise.
        """


class ITranslation(Interface):
    u'''
    Allows extensions to provide their own translation strings.
    '''
    def i18n_directory(self) -> str:
        u'''Change the directory of the .mo translation files'''
        return ''

    def i18n_locales(self) -> list[str]:
        u'''Change the list of locales that this plugin handles'''
        return []

    def i18n_domain(self) -> str:
        u'''Change the gettext domain handled by this plugin'''
        return ''


class IUploader(Interface):
    u'''
    Extensions implementing this interface can provide custom uploaders to
    upload resources and group images.
    '''

    def get_uploader(self, upload_to: str,
                     old_filename: Optional[str]) -> Optional[PUploader]:
        u'''Return an uploader object to upload general files that must
        implement the following methods:

        ``__init__(upload_to, old_filename=None)``

        Set up the uploader.

        :param upload_to: name of the subdirectory within the storage
            directory to upload the file
        :type upload_to: string

        :param old_filename: name of an existing image asset, so the extension
            can replace it if necessary
        :type old_filename: string

        ``update_data_dict(data_dict, url_field, file_field, clear_field)``

        Allow the data_dict to be manipulated before it reaches any
        validators.

        :param data_dict: data_dict to be updated
        :type data_dict: dictionary

        :param url_field: name of the field where the upload is going to be
        :type url_field: string

        :param file_field: name of the key where the FieldStorage is kept (i.e
            the field where the file data actually is).
        :type file_field: string

        :param clear_field: name of a boolean field which requests the upload
            to be deleted.
        :type clear_field: string

        ``upload(max_size)``

        Perform the actual upload.

        :param max_size: upload size can be limited by this value in MBs.
        :type max_size: int

        '''

    def get_resource_uploader(
            self, resource: dict[str, Any]) -> Optional[PResourceUploader]:
        u'''Return an uploader object used to upload resource files that must
        implement the following methods:

        ``__init__(resource)``

        Set up the resource uploader.

        :param resource: resource dict
        :type resource: dictionary

        Optionally, this method can set the following two attributes
        on the class instance so they are set in the resource object:

         - filesize (int):  Uploaded file filesize.
         - mimetype (str):  Uploaded file mimetype.

        ``upload(id, max_size)``

        Perform the actual upload.

        :param id: resource id, can be used to create filepath
        :type id: string

        :param max_size: upload size can be limited by this value in MBs.
        :type max_size: int

        ``get_path(id)``

        Required by the ``resource_download`` action to determine the path to
        the file.

        :param id: resource id
        :type id: string

        '''


class IBlueprint(Interface):

    u'''Register an extension as a Flask Blueprint.'''

    def get_blueprint(self) -> Union[list[Blueprint], Blueprint]:
        u'''
        Return either a single Flask Blueprint object or a list of Flask
        Blueprint objects to be registered by the app.
        '''
        return []


class IPermissionLabels(Interface):
    u'''
    Extensions implementing this interface can override the permission
    labels applied to datasets to precisely control which datasets are
    visible to each user.

    Implementations might want to consider mixing in
    ``ckan.lib.plugins.DefaultPermissionLabels`` which provides
    default behaviours for these methods.

    See ``ckanext/example_ipermissionlabels`` for an example plugin.
    '''

    def get_dataset_labels(self, dataset_obj: 'model.Package') -> list[str]:
        u'''
        Return a list of unicode strings to be stored in the search index
        as the permission lables for a dataset dict.

        :param dataset_obj: dataset details
        :type dataset_obj: Package model object

        :returns: permission labels
        :rtype: list of unicode strings
        '''
        return []

    def get_user_dataset_labels(self,
                                user_obj: Optional['model.User']) -> list[str]:
        u'''
        Return the permission labels that give a user permission to view
        a dataset. If any of the labels returned from this method match
        any of the labels returned from :py:meth:`.get_dataset_labels`
        then this user is permitted to view that dataset.

        :param user_obj: user details
        :type user_obj: User model object or None

        :returns: permission labels
        :rtype: list of unicode strings
        '''
        return []


class IForkObserver(Interface):
    u'''
    Observe forks of the CKAN process.
    '''
    def before_fork(self) -> None:
        u'''
        Called shortly before the CKAN process is forked.
        '''


class IApiToken(Interface):
    """Extend functionality of API Tokens.

    This interface is unstable and new methods may be
    introduced in future. Always use `inherit=True` when implementing
    it.

    Example::

        p.implements(p.IApiToken, inherit=True)


    """

    def create_api_token_schema(self, schema: Schema) -> Schema:
        u'''Return the schema for validating new API tokens.

        :param schema: a dictionary mapping api_token dict keys to lists of
          validator and converter functions to be applied to those
          keys
        :type schema: dict

        :returns: a dictionary mapping api_token dict keys to lists of
          validator and converter functions to be applied to those
          keys
        :rtype: dict

        '''
        return schema

    def decode_api_token(
            self, encoded: str, **kwargs: Any) -> Optional[dict[str, Any]]:
        """Make an attempt to decode API Token provided in request.

        Decode token if it possible and return dictionary with
        mandatory `jti` key(token id for DB lookup) and optional
        additional items, which will be used further in
        `preprocess_api_token`.

        :param encoded: API Token provided in request
        :type encoded: str

        :param kwargs: any additional parameters that can be added
            in future or by plugins. Current implementation won't pass
            any additional fields, but plugins may use this feature, passing
            JWT `aud` or `iss` claims, for example
        :type kwargs: dict

        :returns: dictionary with all the decoded fields or None
        :rtype: dict | None

        """
        return None

    def encode_api_token(self, data: dict[str, Any],
                         **kwargs: Any) -> Optional[str]:
        """Make an attempt to encode API Token.

        Encode token if it possible and return string, that will be
        shown to user.

        :param data: dictionary, containing all postprocessed data
        :type data: dict

        :param kwargs: any additional parameters that can be added
            in future or by plugins. Current implementation won't pass
            any additional fields, but plugins may use this feature, passing
            JWT `aud` or `iss` claims, for example
        :type kwargs: dict

        :returns: token as encodes string or None
        :rtype: str | None

        """
        return None

    def preprocess_api_token(
            self, data: Mapping[str, Any]) -> Mapping[str, Any]:
        """Handle additional info from API Token.

        Allows decoding or extracting any kind of additional
        information from API Token, before it used for fetching
        current user from database.

        :param data: dictionary with all fields that were previously
            created in `postprocess_api_token` (potentially
            modified by some other plugin already.)
        :type data: dict

        :returns: dictionary that will be passed into other
            plugins and, finally, used for fetching User instance
        :rtype: dict

        """
        return data

    def postprocess_api_token(self, data: dict[str, Any], jti: str,
                              data_dict: dict[str, Any]) -> dict[str, Any]:
        """Encode additional information into API Token.

        Allows passing any kind of additional information into API
        Token or performing side effects, before it shown to user.

        :param data: dictionary representing newly
            generated API Token. May be already modified by some
            plugin.
        :type data: dict

        :param jti: Id of the token
        :type jti: str

        :param data_dict: data used for token creation.
        :type data_dict: dict

        :returns: dictionary with fields that will be encoded into
            final API Token
        :rtype: dict

        """
        return data

    def add_extra_fields(self, data_dict: DataDict) -> dict[str, Any]:
        """Provide additional information alongside with API Token.

        Any extra information that is not itself a part of a token,
        but can extend its functionality(for example, refresh token)
        is registered here.

        :param data_dict: dictionary that will bre returned from
            `api_token_create` API call.
        :type data_dict: dict

        :returns: dictionary with token and optional set of extra fields.
        :rtype: dict

        """
        return data_dict


class IClick(Interface):
    u'''
    Allow extensions to define click commands.
    '''
    def get_commands(self) -> list['click.Command']:
        u'''
        Return a list of command functions objects
        to be registered by the click.add_command.

        Example::

            p.implements(p.IClick)
            # IClick
            def get_commands(self):
                """Call me via: `ckan hello`"""
                import click
                @click.command()
                def hello():
                    click.echo('Hello, World!')
                return [hello]

        :returns: command functions objects
        :rtype: list of function objects
        '''
        return []


class ISignal(Interface):
    """Subscribe to CKAN signals.
    """

    def get_signal_subscriptions(self) -> SignalMapping:
        """Return a mapping of signals to their listeners.

        Note that keys are not strings, they are instances of
        ``blinker.Signal``. When using signals provided by CKAN core,
        it is better to use the references from the :doc:`plugins
        toolkit <plugins-toolkit>` for better future
        compatibility. Values should be a list of listener functions::

            def get_signal_subscriptions(self):
                import ckan.plugins.toolkit as tk

                # or, even better, but requires additional dependency:
                # pip install ckantoolkit
                import ckantoolkit as tk

                return {
                    tk.signals.request_started: [request_listener],
                    tk.signals.register_blueprint: [
                        first_blueprint_listener,
                        second_blueprint_listener
                    ]
                }

        Listeners are callables that accept one mandatory
        argument (``sender``) and an arbitrary number of
        named arguments (text). The best signature for a listener is
        ``def(sender, **kwargs)``.

        The ``sender`` argument  will be different depending on the signal
        and will be generally used to conditionally executing code on the
        listener. For example, the ``register_blueprint`` signal is sent every
        time a custom dataset/group/organization blueprint is registered
        (using :class:`ckan.plugins.interfaces.IDatasetForm`
        or :class:`ckan.plugins.interfaces.IGroupForm`). Depending on
        the kind of blueprint, ``sender`` may be 'dataset', 'group',
        'organization' or 'resource'. If you want to do some work only
        for 'dataset' blueprints, you may end up with something similar to::


            import ckan.plugins.toolkit as tk

            def dataset_blueprint_listener(sender, **kwargs):
                if sender != 'dataset':
                    return
                # Otherwise, do something..

            class ExamplePlugin(plugins.SingletonPlugin)
                plugins.implements(plugins.ISignal)

                def get_signal_subscriptions(self):

                    return {
                        tk.signals.register_blueprint: [
                            dataset_blueprint_listener,
                        ]
                    }

        Because this is a really common use case, there is additional
        form of listener registration supported. Instead of just
        callables, one can use dictionaries of form ``{'receiver':
        CALLABLE, 'sender': DESIRED_SENDER}``. The following code
        snippet has the same effect than the previous one::


            import ckan.plugins.toolkit as tk

            def dataset_blueprint_listener(sender, **kwargs):
                # do something..

            class ExamplePlugin(plugins.SingletonPlugin)
                plugins.implements(plugins.ISignal)

                def get_signal_subscriptions(self):

                    return {
                        tk.signals.register_blueprint: [{
                            'receiver': dataset_blueprint_listener,
                            'sender': 'dataset'
                        }]
                    }

        The two forms of registration can be mixed when multiple
        listeners are registered, callables and dictionaries with
        ``receiver``/``sender`` keys::

            import ckan.plugins.toolkit as tk

            def log_registration(sender, **kwargs):
                log.info("Log something")

            class ExamplePlugin(plugins.SingletonPlugin)
                plugins.implements(plugins.ISignal)

                def get_signal_subscriptions(self):
                    return {
                        tk.signals.request_started: [
                            log_registration,
                            {'receiver': log_registration, 'sender': 'dataset'}
                        ]
                    }

        Even though it is possible to change mutable arguments inside the
        listener, or return something from it, the main purpose of signals
        is the triggering of side effects, like logging, starting background
        jobs, calls to external services, etc.

        Any mutation or attempt to change CKAN behavior through signals should
        be considered unsafe and may lead to hard to track bugs in
        the future. So never modify the arguments of signal listener and
        treat them as constants.

        Always check for the presence of the desired value inside the received
        context (named arguments). Arguments passed to
        signals may change over time, and some arguments may disappear.

        :returns: mapping of subscriptions to signals
        :rtype: dict

        """
        return {}
