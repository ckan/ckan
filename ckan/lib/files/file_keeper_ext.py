from __future__ import annotations

import file_keeper as fk
import ckan.plugins as p
from . import default


@fk.hookimpl
def register_location_transformers(registry: fk.Registry[fk.types.LocationTransformer]):
    """Collect location transformers from IFiles implementations.

    This hook is called by file_keeper inside
    ``file_keeper.ext.register(reset=True)``.
    """
    for plugin in p.PluginImplementations(p.IFiles):
        for k, v in plugin.files_get_location_transformers().items():
            registry.register(k, v)


@fk.hookimpl
def register_adapters(registry: fk.Registry[type[fk.Storage]]):
    """Collect adapters from core and IFiles implementations.

    This hook is called by file_keeper inside
    ``file_keeper.ext.register(reset=True)``.

    """
    registry.register("ckan:fs", default.FsStorage)
    registry.register("ckan:public_fs", default.PublicFsStorage)
    registry.register("ckan:null", default.NullStorage)

    if adapter := getattr(default, "LibCloudStorage", None):
        registry.register("ckan:libcloud", adapter)

    if adapter := getattr(default, "OpenDalStorage", None):
        registry.register("ckan:opendal", adapter)

    for plugin in p.PluginImplementations(p.IFiles):
        for k, v in plugin.files_get_storage_adapters().items():
            registry.register(k, v)
