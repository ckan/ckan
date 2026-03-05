from __future__ import annotations

import logging
import os
from typing import Any, Tuple
from typing_extensions import Literal, TypedDict, assert_never

from markupsafe import Markup
from webassets.env import Environment
from webassets.loaders import YAMLLoader

from ckan.common import config, g
from ckan.lib.io import get_ckan_temp_directory


log = logging.getLogger(__name__)
env: Environment

AssetType = Literal["style", "script"]


class AssetCollection(TypedDict):
    script: list[Tuple[str, dict[str, str]]]
    style: list[Tuple[str, dict[str, str]]]
    included: set[str]


def create_library(name: str, path: str) -> None:
    """Create WebAssets library(set of Bundles).
    """
    config_path = os.path.join(path, "webassets.yaml")
    if not os.path.exists(config_path):
        config_path = os.path.join(path, "webassets.yml")

    if not os.path.exists(config_path):
        log.warning(
            "Cannot create library %s at %s because webassets.yaml is missing",
            name,
            path,
        )
        return

    library: dict[str, Any] = YAMLLoader(config_path).load_bundles()
    bundles = {
        f"{name}/{key}": bundle
        for key, bundle
        in library.items()
    }

    # skip attempts to register an asset if name is taken. It gives us
    # templates-like behavior, where the item that was registered first has
    # highest priority.
    for name, bundle in bundles.items():
        if is_registered(name):
            log.debug(
                "Skip registration of %s because it already exists",
                name,
            )
            continue

        # use absolute path to files. Otherwise they'll behave like templates
        # and if plugin A and plugin B has their own `x.css`(i.e
        # `ckanext/A/assets/x.css` and `ckanext/B/assets/x.css`), both plugins
        # will load the same `x.css` from the plugin that was first registered
        bundle.contents = [
            os.path.join(path, item)
            for item in bundle.contents
        ]
        log.debug("Register asset %s", name)
        env.register(name, bundle)


def webassets_init() -> None:
    """Initialize fresh Webassets environment
    """
    global env

    static_path = get_webassets_path()

    env = Environment()
    env.directory = static_path
    env.debug = config["debug"]
    env.url = config["ckan.webassets.url"]


def register_core_assets():
    """Register CKAN core assets.

    Call this function after registration of plugin assets. Asset overrides are
    not allowed, so if plugin tries to replace CKAN core asset, it has to
    register an asset with the same name before core asset is added. In this
    case, asset from plugin will have higher precedence and core asset will be
    ignored.

    """
    public = config["ckan.base_public_folder"]
    public_folder = os.path.abspath(os.path.join(
        os.path.dirname(__file__),
        "..",
        public,
    ))

    base_path = os.path.join(public_folder, "base")
    add_public_path(base_path, "/base/")
    create_library("vendor", os.path.join(base_path, "vendor"))
    create_library("base", os.path.join(base_path, "javascript"))
    create_library("css", os.path.join(base_path, "css"))


def _make_asset_collection() -> AssetCollection:
    return {"style": [], "script": [], "included": set()}


def include_asset(name: str) -> None:
    from ckan.lib.helpers import url_for_static_or_external

    if not hasattr(g, "_webassets"):
        log.debug("Initialize fresh assets collection")
        g._webassets = _make_asset_collection()

    if name in g._webassets["included"]:
        return

    if not is_registered(name):
        log.error("Trying to include unknown asset: %s", name)
        return

    bundle: Any = env[name]
    deps: list[str] = bundle.extra.get("preload", [])
    attrs: dict[str, str] = bundle.extra.get("attrs", {})

    # mark current asset as included in order to avoid recursion while loading
    # dependencies
    g._webassets["included"].add(name)
    for dep in deps:
        include_asset(dep)

    # Add `site_root` if configured
    urls_info = [(url_for_static_or_external(url), attrs) for url in bundle.urls()]

    for item in urls_info:
        url = item[0]
        link = url.split("?")[0]
        if link.endswith(".css"):
            type_ = "style"
            break
        elif link.endswith(".js"):
            type_ = "script"
            break
    else:
        log.warning("Undefined asset type: %s", urls_info)
        return
    g._webassets[type_].extend(urls_info)


def _to_tag(asset_info: Tuple[str, dict[str, str]], type_: AssetType) -> str:
    """Turn asset URL into corresponding HTML tag.
    """

    url, attrs = asset_info

    is_preload = attrs.get("rel") and attrs["rel"] == "preload" and attrs.get("as")

    if type_ == "style" and "rel" not in attrs:
        attrs["rel"] = "stylesheet"
    elif type_ == "script" and "type" not in attrs and not is_preload:
        attrs["type"] = "text/javascript"

    attr_items = []
    for key, value in attrs.items():
        if not value:
            attr_items.append(key)
        else:
            attr_items.append(f'{key}="{value}"')

    attrs_str = " ".join(attr_items)

    if type_ == "style" or is_preload:
        return f'<link href="{url}" {attrs_str}/>'
    elif type_ == "script":
        return f'<script src="{url}" {attrs_str}></script>'
    else:
        assert_never(type_)


def render_assets(type_: AssetType) -> Markup:
    """Render all assets of the given type as a string of HTML tags.

    All assets that are included into output will be removed from the render
    cache. I.e:

        include_asset("a") # style
        # render tags and clear style-cache
        output = render_assets("style")
        assert "a.css" in output

        # style-cache is clean, nothing included since last render
        output = render_assets("style")
        assert output ==""

        include_asset("b") # style
        include_asset("c") # style
        # render tags and clear style-cache. "a" was already rendered and
        # removed from the cache, so this time only "b" and "c" are rendered.
        output = render_assets("style")
        assert "b.css" in output
        assert "c.css" in output

        # style-cache is clean, nothing included since last render
        output = render_assets("style")
        assert output == ""
    """
    try:
        assets: AssetCollection = g._webassets
    except AttributeError:
        return Markup()

    tags = "\n".join(_to_tag(asset_info, type_) for asset_info in assets[type_])
    assets[type_].clear()

    return Markup(tags)


def get_webassets_path() -> str:
    """Compute path to the folder where compiled assets are stored.
    """
    webassets_path = config["ckan.webassets.path"]

    if not webassets_path:
        storage_path = config.get(
            "ckan.storage_path"
        ) or get_ckan_temp_directory()

        if storage_path:
            webassets_path = os.path.join(storage_path, "webassets")

    if not webassets_path:
        raise RuntimeError(
            "Either `ckan.webassets.path` or `ckan.storage_path`"
            " must be specified"
        )
    return webassets_path


def add_public_path(path: str, url: str) -> None:
    """Add a public path that can be used by `cssrewrite` filter."""
    env.append_path(path, url)


def is_registered(asset: str) -> bool:
    """Check if asset is registered in current environment."""
    return asset in env
