# encoding: utf-8
from __future__ import annotations

import logging
import os
import tempfile
from typing import Any, Optional

import yaml
from markupsafe import Markup
from webassets import Environment
from webassets.env import RegisterError
from webassets.loaders import YAMLLoader

from ckan.common import config, g


logger = logging.getLogger(__name__)
env: Optional[Environment] = None

yaml.warnings({u'YAMLLoadWarning': False})


def create_library(name: str, path: str) -> None:
    """Create WebAssets library (set of Bundles).

    This function is executed when creating the Flask
    application and it will register in the webassets Environment
    the bundles defined in the webassets.yml file.

    It is also executed when loading plugins that registered
    webassets using the IConfigurer interface. (See
    toolkit.add_resource() for more info.)
    """
    config_path = os.path.join(path, u'webassets.yml')
    if not os.path.exists(config_path):
        return
    assert env
    library: dict[str, Any] = YAMLLoader(config_path).load_bundles()
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
        try:
            env.register(name, bundle)
        except RegisterError:
            logger.debug(f"Bundle {name} already registered, overriding.")
            env._named_bundles.pop(name, None)
            env.register(name, bundle)

    env.append_path(path)


def webassets_init() -> None:
    """ Initializes the webassets Environment and creates core libraries.

    This function is executed when running CKAN
    for the first time or when loading new plugins. It is
    called by ckan.config.environment.update_config().
    """
    global env

    static_path = get_webassets_path()

    public = config.get(u'ckan.base_public_folder')

    public_folder = os.path.abspath(os.path.join(
        os.path.dirname(__file__), u'..', public))

    base_path = os.path.join(public_folder, u'base')

    env = Environment()
    env.directory = static_path
    env.debug = config.get(u'debug')
    env.url = u'/webassets/'

    add_public_path(base_path, u'/base/')

    logger.debug(u'Base path {0}'.format(base_path))
    create_library(u'vendor', os.path.join(
        base_path, u'vendor'))

    create_library(u'base', os.path.join(base_path, u'javascript'))

    create_library(u'datapreview', os.path.join(base_path, u'datapreview'))

    create_library(u'css', os.path.join(base_path, u'css'))


def _make_asset_collection() -> dict[str, Any]:
    return {u'style': [], u'script': [], u'included': set()}


def include_asset(name: str) -> None:
    """ Appends the webasset name into the g.webassets list.

    This function is called using jinja2 asset tag. When processing
    a reuqest, CKAN will store in g.webassets all the assets found in
    the templates. Later it will render the html tags calling
    h.render_assets() at the end of base.html template.

    When running in debug mode, the call to bundle.urls()
    will copy the files into the media directory configured.
    (See get_webassets_path())
    """
    from ckan.lib.helpers import url_for_static_or_external
    try:
        if not g.webassets:
            raise AttributeError(u'WebAssets not initialized yet')
    except AttributeError:
        g.webassets = _make_asset_collection()

    if name in g.webassets[u'included']:
        return

    assert env
    try:
        bundle: Any = env[name]
    except KeyError:
        logger.error(u'Trying to include unknown asset: <{}>'.format(name))
        return

    # TODO: consider infinite loop prevention for assets that depends
    # on each other
    deps: list[str] = bundle.extra.get(u'preload', [])
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


def _to_tag(url: str, type_: str):
    if type_ == u'style':
        return u'<link href="{}" rel="stylesheet"/>'.format(url)
    elif type_ == u'script':
        return u'<script src="{}" type="text/javascript"></script>'.format(url)
    return u''


def render_assets(type_: str) -> Markup:
    """ Renders the webassets of a specific type.

    This function is called at the end of the base.html template. It
    will iterate trough g.webassets to return the necessary html tags to
    include the assets in the html response.
    """
    try:
        assets = g.webassets
    except AttributeError:
        logger.warn("Webassets are not initialized.")
        return Markup(u'')

    if not assets:
        logger.warn("Webassets are initialized but none was found.")
        return Markup(u'')
    collection = assets[type_]
    tags = u'\n'.join([_to_tag(asset, type_) for asset in assets[type_]])
    collection[:] = []
    return Markup(tags)


def get_webassets_path() -> str:
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


def add_public_path(path: str, url: str) -> None:
    assert env
    env.append_path(path, url)
