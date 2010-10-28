import logging
from pkg_resources import iter_entry_points

log = logging.getLogger(__name__)

# Entry point group. 
GROUP_NAME = "ckan.plugins"

class PluginException(Exception): pass

def load_all(config):
    plugins = config.get('ckan.plugins', '')
    log.debug("Loading plugins: %s" % plugins)
    for plugin in plugins.split():
        for entry_point in iter_entry_points(group=GROUP_NAME, name=plugin):
            load(plugin, entry_point, config)
            break
        else:
            raise PluginException("Plugin not found: %s" % plugin)
            

def load(name, entry_point, config):
    log.debug("Plugin: %s", entry_point.dist)
    entry_obj = entry_point.load()(config)
    registry = config.get('ckan.plugin_registry', {})
    registry[entry_point] = entry_obj
    config['ckan.plugin_registry'] = registry
    return entry_obj
    
    
def find_methods(method_name):
    """ For a given method name, find all plugins where that method exists and iterate over them. """
    from pylons import config
    for k, v in config.get('ckan.plugin_registry', {}).items():
        if hasattr(v, method_name):
            yield getattr(v, method_name)
        else:
            pass
            #log.debug("%s has no method %s" % (k.name, method_name))



#####  Pylons monkey-patch

from pylons.wsgiapp import PylonsApp
import pkg_resources

log.info("Monkey-patching Pylons to allow loading of controllers via entry point mechanism")

find_controller_generic = PylonsApp.find_controller

# This is from pylons 1.0 source, will monkey-patch into 0.9.7
def find_controller(self, controller):
    if controller in self.controller_classes:
        return self.controller_classes[controller]

    # Check to see if its a dotted name
    if '.' in controller or ':' in controller:
        mycontroller = pkg_resources.EntryPoint.parse('x=%s' % controller).load(False)
        self.controller_classes[controller] = mycontroller
        return mycontroller

    return find_controller_generic(self, controller)

PylonsApp.find_controller = find_controller
