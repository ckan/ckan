# coding=UTF-8

"""Data previewer functions

Functions and data structures that are needed for the ckan data preview.
"""

import urlparse

import pylons.config as config

import ckan.plugins as p

DEFAULT_DIRECT_EMBED = ['png', 'jpg', 'gif']
DEFAULT_LOADABLE_IFRAME = ['html', 'htm', 'rdf+xml', 'owl+xml', 'xml', 'n3', 'n-triples', 'turtle', 'plain', 'atom', 'rss', 'txt']


def compare_domains(urls):
    ''' Return True if the domains of the provided are the same.
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


def resource_is_on_same_domain(data_dict):
    # compare CKAN domain and resource URL
    ckan_url = config.get('ckan.site_url', '//localhost:5000')
    resource_url = data_dict['resource']['url']

    return compare_domains([ckan_url, resource_url])


def can_be_previewed(data_dict):
    '''
    Determines whether there is an extension that can preview the resource.

    :param data_dict: contains a resource and package dict.
        The resource dict has to have a value for ``on_same_domain``
    :type data_dict: dictionary
    '''
    data_dict['resource']['on_same_domain'] = resource_is_on_same_domain(data_dict)
    plugins = p.PluginImplementations(p.IResourcePreview)
    return any(plugin.can_preview(data_dict) for plugin in plugins)
