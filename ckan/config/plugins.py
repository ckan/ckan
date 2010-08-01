import logging
from pkg_resources import iter_entry_points

log = logging.getLogger(__name__)

GROUP_NAME = "ckan.plugins"

class PluginException(Exception): pass

def load_all(config):
    plugins = config.get('ckan.plugins', '')
    log.info("Loading plugins: %s" % plugins)
    for plugin in plugins.split():
        for entry_point in iter_entry_points(group=GROUP_NAME, name=plugin):
            load(plugin, entry_point, config)
            break
        else:
            raise PluginException("Plugin not found: %s" % plugin)
            

def load(name, entry_point, config):
    log.debug("Plugin: %s", entry_point.dist)
    g = config.get('pylons.app_globals')
    g.plugins[name] = entry_point
    entry_func = entry_point.load()
    return entry_func(config)