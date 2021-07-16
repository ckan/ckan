# encoding: utf-8

import logging
import os
import tempfile
import yaml

from markupsafe import Markup
from webassets import Environment
from webassets.loaders import YAMLLoader

from ckan.common import config, g, asbool


logger = logging.getLogger(__name__)
env = None

yaml.warnings({'YAMLLoadWarning': False})


def create_library(name, path):
    """Create WebAssets library(set of Bundles).
    """
    config_path = os.path.join(path, 'webassets.yml')
    if not os.path.exists(config_path):
        return

    library = YAMLLoader(config_path).load_bundles()
    bundles = {
        '/'.join([name, key]): bundle
        for key, bundle
        in library.items()
    }

    # Unfortunately, yo'll get an error attempting to register bundle
    # with the same name twice. For now, let's just pop existing
    # bundle and avoid name-conflicts
    # TODO: make PR into webassets with preferable solution
    # Issue: https://github.com/miracle2k/webassets/issues/519
    for name, bundle in bundles.items():
        env._named_bundles.pop(name, None)
        env.register(name, bundle)

    env.append_path(path)


def webassets_init():
    global env

    static_path = get_webassets_path()

    public = config.get('ckan.base_public_folder')

    public_folder = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..', public))

    base_path = os.path.join(public_folder, 'base')

    env = Environment()
    env.directory = static_path
    env.debug = asbool(config.get('debug', False))
    env.url = '/webassets/'

    add_public_path(base_path, '/base/')

    logger.debug('Base path {0}'.format(base_path))
    create_library('vendor', os.path.join(
        base_path, 'vendor'))

    create_library('base', os.path.join(base_path, 'javascript'))

    create_library('datapreview', os.path.join(base_path, 'datapreview'))

    create_library('css', os.path.join(base_path, 'css'))


def _make_asset_collection():
    return {'style': [], 'script': [], 'included': set()}


def include_asset(name):
    from ckan.lib.helpers import url_for_static_or_external
    try:
        if not g.webassets:
            raise AttributeError('WebAssets not initialized yet')
    except AttributeError:
        g.webassets = _make_asset_collection()
    if name in g.webassets['included']:
        return

    try:
        bundle = env[name]
    except KeyError:
        logger.error('Trying to include unknown asset: <{}>'.format(name))
        return

    deps = bundle.extra.get('preload', [])

    # Using DFS may lead to infinite recursion(unlikely, because
    # extensions rarely depends on each other), so there is a sense to
    # memoize visited routes.

    # TODO: consider infinite loop prevention for assets that depends
    # on each other
    for dep in deps:
        include_asset(dep)

    # Add `site_root` if configured
    urls = [url_for_static_or_external(url) for url in bundle.urls()]
    type_ = None
    for url in urls:
        link = url.split('?')[0]
        if link.endswith('.css'):
            type_ = 'style'
            break
        elif link.endswith('.js'):
            type_ = 'script'
            break
    else:
        logger.warn('Undefined asset type: {}'.format(urls))
        return
    g.webassets[type_].extend(urls)
    g.webassets['included'].add(name)


def _to_tag(url, type_):
    if type_ == 'style':
        return '<link href="{}" rel="stylesheet"/>'.format(url)
    elif type_ == 'script':
        return '<script src="{}" type="text/javascript"></script>'.format(url)
    return ''


def render_assets(type_):
    try:
        assets = g.webassets
    except AttributeError:
        return ''

    if not assets:
        return ''
    collection = assets[type_]
    tags = '\n'.join([_to_tag(asset, type_) for asset in assets[type_]])
    collection[:] = []
    return Markup(tags)


def get_webassets_path():
    webassets_path = config.get('ckan.webassets.path')

    if not webassets_path:
        storage_path = config.get(
            'ckan.storage_path'
        ) or tempfile.gettempdir()

        if storage_path:
            webassets_path = os.path.join(storage_path, 'webassets')

    if not webassets_path:
        raise RuntimeError(
            'Either `ckan.webassets.path` or `ckan.storage_path` '
            'must be specified'
        )
    return webassets_path


def add_public_path(path, url):
    env.append_path(path, url)
