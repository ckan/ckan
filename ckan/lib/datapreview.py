# coding=UTF-8

"""Data previewer functions

Functions and data structures that are needed for the ckan data preview.
"""

import urlparse
import logging

import pylons.config as config

import ckan.plugins as p
from ckan import logic
from ckan.common import _


log = logging.getLogger(__name__)


DEFAULT_RESOURCE_VIEW_TYPES = ['image', 'webpage']


def res_format(resource):
    ''' The assumed resource format in lower case. '''
    if not resource['url']:
        return None
    return (resource['format'] or resource['url'].split('.')[-1]).lower()


def compare_domains(urls):
    ''' Return True if the domains of the provided urls are the same.
    '''
    first_domain = None
    for url in urls:
        # all urls are interpreted as absolute urls,
        # except for urls that start with a /
        try:
            if not urlparse.urlparse(url).scheme and not url.startswith('/'):
                url = '//' + url
            parsed = urlparse.urlparse(url.lower(), 'http')
            domain = (parsed.scheme, parsed.hostname, parsed.port)
        except ValueError:
            # URL is so messed up that even urlparse can't stand it
            return False

        if not first_domain:
            first_domain = domain
            continue
        if first_domain != domain:
            return False
    return True


def on_same_domain(data_dict):
    # compare CKAN domain and resource URL
    ckan_url = config.get('ckan.site_url', '//localhost:5000')
    resource_url = data_dict['resource']['url']

    return compare_domains([ckan_url, resource_url])


def get_preview_plugin(data_dict, return_first=False):
    '''Determines whether there is an extension that can preview the resource.

    :param data_dict: contains a resource and package dict.
        The resource dict has to have a value for ``on_same_domain``
    :type data_dict: dictionary

    :param return_first: If True return the first plugin that can preview
    :type return_first: bool

    Returns a dict of plugins that can preview or ones that are fixable'''

    data_dict['resource']['on_same_domain'] = on_same_domain(data_dict)

    plugins_that_can_preview = []
    plugins_fixable = []
    for plugin in p.PluginImplementations(p.IResourcePreview):
        p_info = {'plugin': plugin, 'quality': 1}
        data = plugin.can_preview(data_dict)
        # old school plugins return true/False
        if isinstance(data, bool):
            p_info['can_preview'] = data
        else:
            # new school provide a dict
            p_info.update(data)
        # if we can preview
        if p_info['can_preview']:
            if return_first:
                plugin
            plugins_that_can_preview.append(p_info)
        elif p_info.get('fixable'):
            plugins_fixable.append(p_info)

    num_plugins = len(plugins_that_can_preview)
    if num_plugins == 0:
        # we didn't find any.  see if any could be made to work
        for plug in plugins_fixable:
            log.info('%s would allow previews to fix: %s' % (
                plug['plugin'], plug['fixable']))
        preview_plugin = None
    elif num_plugins == 1:
        # just one available
        preview_plugin = plugins_that_can_preview[0]['plugin']
    else:
        # multiple plugins so get the best one
        plugs = [pl['plugin'] for pl in plugins_that_can_preview]
        log.warn('Multiple previews are possible. {0}'.format(plugs))
        preview_plugin = max(plugins_that_can_preview,
                             key=lambda x: x['quality'])['plugin']
    return preview_plugin


def get_view_plugin(view_type):
    '''
    Returns the IResourceView plugin associated with the given view_type.
    '''
    for plugin in p.PluginImplementations(p.IResourceView):
        info = plugin.info()
        name = info.get('name')
        if name == view_type:
            return plugin


def get_allowed_view_plugins(data_dict):
    '''
    Returns a list of view plugins that work against the resource provided

    The ``data_dict`` contains: ``resource`` and ``package``.
    '''
    can_view = []
    for plugin in p.PluginImplementations(p.IResourceView):
        if plugin.can_view(data_dict):
            can_view.append(plugin)
    return can_view


# TODO: remove
def get_new_resources(context, data_dict):
    '''
    Returns a list of all new resources in this transaction

    This is to be used only before commiting eg on `package_create` or
    `package_update` as it uses a cache object stored in the Session and
    filled on flushig it.

    The `context` dict must contain a `model` key

    Returns a list of new dictized resources.
    '''
    model = context['model']
    session = model.Session()
    session.flush()
    if hasattr(session, '_object_cache'):
        import ckan.lib.dictization.model_dictize as model_dictize
        new_objs = session._object_cache['new']
        new_resources = [obj for obj in new_objs
                         if isinstance(obj, model.Resource)]
        return model_dictize.resource_list_dictize(new_resources, context)
    else:
        return []


def get_default_view_plugins(get_datastore_views=False):
    '''
    Returns the list of view plugins to be created by default on new resources

    The default view types are defined via the `ckan.views.default_views`
    configuration option. If this is not set (as opposed to empty, which means
    no default views), the value of DEFAULT_RESOURCE_VIEW_TYPES is used to
    look up the plugins.

    If get_datastore_views is False, only the ones not requiring data to be in
    the DataStore are returned, and if True, only the ones requiring it are.

    To flag a view plugin as requiring the DataStore, it must have the
    `requires_datastore` key set to True in the dict returned by its `info()`
    method.

    Returns a list of IResourceView plugins
    '''

    if config.get('ckan.views.default_views') is None:
        default_view_types = DEFAULT_RESOURCE_VIEW_TYPES
    else:
        default_view_types = config.get('ckan.views.default_views').split(' ')

    default_view_plugins = []
    for view_type in default_view_types:

        view_plugin = get_view_plugin(view_type)

        if not view_plugin:
            log.warning('Plugin for view {0} could not be found'
                        .format(view_type))
            # We should probably check on startup if the default
            # view types exist
            continue

        info = view_plugin.info()

        plugin_requires_datastore = info.get('requires_datastore', False)

        if plugin_requires_datastore == get_datastore_views:
            default_view_plugins.append(view_plugin)

    return default_view_plugins


def add_default_views_to_resource(context,
                                  resource_dict,
                                  dataset_dict=None,
                                  create_datastore_views=False):
    '''
    Creates the default views (if necessary) on the provided resource

    The function will get the plugins for the default views defined in
    the configuration, and if some were found the `can_view` method of
    each one of them will be called to determine if a resource view should
    be created.

    Resource views extensions get the resource dict and the parent dataset
    dict. If the latter is not provided, `package_show` is called to get it.

    By default only views that don't require the resource data to be in the
    DataStore are called. See ``add_default_views_to_dataset_resources``
    for details on the ``create_datastore_views`` parameter.

    Returns a list of resource views created (empty if none were created)
    '''
    if not dataset_dict:
        dataset_dict = logic.get_action('package_show')(
            context, {resource_dict['package_id']})

    default_view_plugins = get_default_view_plugins(create_datastore_views)

    if not default_view_plugins:
        return []

    existing_views = p.toolkit.get_action('resource_view_list')(
        context, {'id': resource_dict['id']})

    existing_view_types = ([v['view_type'] for v in existing_views]
                           if existing_views
                           else [])

    created_views = []
    for view_plugin in default_view_plugins:

        view_info = view_plugin.info()

        # Check if a view of this type already exists
        if view_info['name'] in existing_view_types:
            continue

        # Check if a view of this type can preview this resource
        if view_plugin.can_view({
            'resource': resource_dict,
            'package': dataset_dict
                }):
            view = {'resource_id': resource_dict['id'],
                    'view_type': view_info['name'],
                    'title': view_info.get('default_title', _('View')),
                    'description': view_info.get('default_description', '')}

            view_dict = p.toolkit.get_action('resource_view_create')(context,
                                                                     view)
            created_views.append(view_dict)

    return created_views


def add_default_views_to_dataset_resources(context,
                                           dataset_dict,
                                           create_datastore_views=False):
    '''
    Creates the default views on all resources of the provided dataset

    By default only views that don't require the resource data to be in the
    DataStore are called. Passing `create_datastore_views` as True will only
    create views that require data to be in the DataStore. The first case
    happens when the function is called from `package_create` or
    `package_update`, the second when it's called from the DataPusher when
    data was uploaded to the DataStore.

    Returns a list of resource views created (empty if none were created)
    '''
    created_views = []
    for resource_dict in dataset_dict.get('resources', []):
        new_views = add_default_views_to_resource(context,
                                                  resource_dict,
                                                  dataset_dict,
                                                  create_datastore_views)
        created_views.extend(new_views)

    return created_views
