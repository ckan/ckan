import logging
from pkg_resources import iter_entry_points

log = logging.getLogger(__name__)

# Entry point group. 
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
    entry_obj = entry_point.load()(config)
    config.get('pylons.app_globals').plugins[entry_point] = entry_obj
    return entry_obj
    
    
def find_methods(method_name):
    """ For a given method name, find all plugins where that method exists and iterate over them. """
    from pylons import g
    for k, v in g.plugins.items():
        if hasattr(v, method_name):
            yield getattr(v, method_name)
        else:
            log.debug("%s has no method %s" % (k.name, method_name))
