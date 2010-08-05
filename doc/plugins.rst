Plugins
=======

**NOTE: CKAN plugin support is under development. All features documented on this page 
are subject to frequent and breaking changes and should only be used with that in mind.**

Plugin activation
-----------------

All plug-ins must be installed as generic setuptools packages and available in the 
virtualenv used by CKAN. After installing a plugin, add it to the CKAN plugin registry
by adding the following to you ``.ini`` config file::

  ckan.plugins = disqus foo bar
  
Each (space-seperated) item will be considered an entry point. If a plugin is not found, 
CKAN will not start. If you specify multiple ``ckan.plugins`` directives, only the last 
will be handled by the plugin loader. 

Plugin development
------------------

CKAN will load plugins by searching for entry points in the group ``ckan.plugin``. 
After setting up a basic package for your plugin (``paster create -t basic_package my_plugin``),
add the following information to your setup.py::

    entry_points="""
        # -*- Entry points: -*-
  
        [ckan.plugins]
        my_plugin = my_plugin:PluginClass
  
        """

This will allow CKAN to load a plugin called ``my_plugin`` by instantiating ``PluginClass``. 
Your plugin class should accept one argument to its constructor, the pylons configuration 
dictionary. Note that plugins are initialized before the model or the templating system have
been set up. 

In its current stage of development, the plugin system is explicitly called from within CKAN. 
When called, it will check for the presence of a specific method on all registered plugin 
classes. If the required method is present, it will be called and its return value will be 
handled by CKAN. 

* ``render``: This method is called when a specific page is rendered. Any registered plugin will be handed one argument, ``stream``. This is a Genshi stream of the current output document. It can be transformed using XML tree manipulation. The method is expected to return a Genshi stream.

* ``make_map``: This method is called when a routes map is generated. It will receive a ``map`` object and it is expected to return a modified version of the same object. Because it is called as the first mapping entry, it can 
override all others. 
