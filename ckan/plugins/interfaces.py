"""
Interfaces for plugins system
See doc/plugins.rst for more information
"""

__all__ = [
    'Interface',
    'IGenshiStreamFilter', 'IRoutes',
    'IMapper', 'ISession',
    'IMiddleware',
    'IAuthFunctions',
    'IDomainObjectModification', 'IGroupController', 
    'IPackageController', 'IPluginObserver',
    'IConfigurable', 'IConfigurer', 'IAuthorizer',
    'IActions', 'IResourceUrlChange'
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
        Called after routes map is set up. ``after_map`` can be used to add fall-back handlers. 

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
        Receive an object instance before that instance is INSERTed into its table.
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

    def before_search(self, search_params):
        '''
            Extensions will receive a dictionary with the query parameters,
            and should return a modified (or not) version of it.

            search_params will include an 'extras' dictionary with all values
            from fields starting with 'ext_', so extensions can receive user
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

            search_params will include an 'extras' dictionary with all values
            from fields starting with 'ext_', so extensions can receive user
            input from specific fields.

        '''

        return search_results

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


class IAuthorizer(Interface):
    """
    Allow customisation of default Authorization implementation
    """
    def get_authorization_groups(self, username):
        """
        Called by Authorizer to extend the list of groups to which a
        user belongs.  Should return a list of AuthorizationGroups.
        """

    def get_roles(self, username, domain_obj):
        """
        Called by Authorizer to extend the list of roles which a user
        has in the context of the supplied object.  Should return a
        list of strings which are the names of valid UserObjectRoles.
        """

    def is_authorized(self, username, action, domain_obj):
        """
        Called by Authorizer to assert that a user ```username``` can
        perform ``action``` on ```domain_obj```.

        Should return True or False.  A value of False will allow
        other Authorizers to run; True will shortcircuit and return.
        """
        
class IActions(Interface):
    """
    Allow adding of actions to the logic layer.
    """
    def get_actions(self):
        """
        Should return a dict, the keys being the name of the logic 
        function and the values being the functions themselves.
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

