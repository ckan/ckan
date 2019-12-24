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

yaml.warnings({u'YAMLLoadWarning': False})


def create_library(name, path):
    """Create WebAssets library(set of Bundles).
    """
    config_path = os.path.join(path, u'webassets.yml')
    if not os.path.exists(config_path):
        return

    library = YAMLLoader(config_path).load_bundles()
    bundles = {
        u'/'.join([name, key]): bundle
        for key, bundle
        in library.items()
    }

    # Unfortunately, you'll get an error attempting to register bundle
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

    public = config.get(u'ckan.base_public_folder')

    public_folder = os.path.abspath(os.path.join(
        os.path.dirname(__file__), u'..', public))

    base_path = os.path.join(public_folder, u'base')

    env = Environment()
    env.directory = static_path
    env.debug = asbool(config.get(u'debug', False))
    env.url = u'/webassets/'

    add_public_path(base_path, u'/base/')

    logger.debug(u'Base path {0}'.format(base_path))
    create_library(u'vendor', os.path.join(
        base_path, u'vendor'))

    create_library(u'base', os.path.join(base_path, u'javascript'))

    create_library(u'datapreview', os.path.join(base_path, u'datapreview'))

    create_library(u'css', os.path.join(base_path, u'css'))


def _make_asset_collection():
    return {u'style': [], u'script': [], u'included': set()}


def include_asset(name):
    from ckan.lib.helpers import url_for_static_or_external
    try:
        if not g.webassets:
            raise AttributeError(u'WebAssets not initialized yet')
    except AttributeError:
        g.webassets = _make_asset_collection()
    if name in g.webassets[u'included']:
        return

    try:
        bundle = env[name]
    except KeyError:
        logger.error(u'Trying to include unknown asset: <{}>'.format(name))
        return

    deps = bundle.extra.get(u'preload', [])

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
        link = url.split(u'?')[0]
        if link.endswith(u'.css'):
            type_ = u'style'
            break
        elif link.endswith(u'.js'):
            type_ = u'script'
            break
    else:
        logger.warn(u'Undefined asset type: {}'.format(urls))
        return
    g.webassets[type_].extend(urls)
    g.webassets[u'included'].add(name)


def _to_tag(url, type_):
    if type_ == u'style':
        return u'<link href="{}" rel="stylesheet"/>'.format(url)
    elif type_ == u'script':
        return u'<script src="{}" type="text/javascript"></script>'.format(url)
    return u''


def render_assets(type_):
    try:
        assets = g.webassets
    except AttributeError:
        return u''

    if not assets:
        return u''
    collection = assets[type_]
    tags = u'\n'.join([_to_tag(asset, type_) for asset in assets[type_]])
    collection[:] = []
    return Markup(tags)


def get_webassets_path():
    webassets_path = config.get(u'ckan.webassets.path')

    if not webassets_path:
        storage_path = config.get(
            u'ckan.storage_path'
        ) or tempfile.gettempdir()

        if storage_path:
            webassets_path = os.path.join(storage_path, u'webassets')

    if not webassets_path:
        raise RuntimeError(
            u'Either `ckan.webassets.path` or `ckan.storage_path` '
            u'must be specified'
        )
    return webassets_path


def add_public_path(path, url):
    env.append_path(path, url)
