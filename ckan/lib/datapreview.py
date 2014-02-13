# coding=UTF-8

"""Data previewer functions

Functions and data structures that are needed for the ckan data preview.
"""

import urlparse
import logging

import pylons.config as config

import ckan.plugins as p

DEFAULT_DIRECT_EMBED = ['png', 'jpg', 'jpeg', 'gif']
DEFAULT_LOADABLE_IFRAME = ['html', 'htm', 'rdf+xml', 'owl+xml', 'xml',
                           'n3', 'n-triples', 'turtle', 'plain',
                           'atom', 'rss', 'txt']

log = logging.getLogger(__name__)


def direct():
    ''' Directly embeddable formats.'''
    direct_embed = config.get('ckan.preview.direct', '').split()
    return direct_embed or DEFAULT_DIRECT_EMBED


def loadable():
    ''' Iframe loadable formats. '''
    loadable_in_iframe = config.get('ckan.preview.loadable', '').split()
    return loadable_in_iframe or DEFAULT_LOADABLE_IFRAME


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


def _on_same_domain(data_dict):
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

    data_dict['resource']['on_same_domain'] = _on_same_domain(data_dict)

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
