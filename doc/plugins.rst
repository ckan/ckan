Plugins
=======

**NOTE: CKAN plugin support is under development. All features documented on this page 
are subject to frequent and breaking changes and should only be used with that in mind.**


Overview
--------

The CKAN plugin code provides a simple mechanism for plugins to extend core
CKAN functionality.

Examples of services provided by plugins include:

- Asynchronous model update notifications through AMQP (i.e. RabbitMQ_)
- Genshi template stream filters
- User comments through disqus_
- Integration with Deliverance_

Existing plugins are described on the CKAN public wiki: http://wiki.okfn.org/ckan/plugins - If you write a plugin then do share details of it there.


Installing a plugin
-------------------

To install a plugin on a CKAN instance:

1. Install the plugin code using pip. The -E parameter is for your CKAN python environment (e.g. '~/var/srvc/ckan.net/pyenv'). Prefix the source url with the repo type ('hg+' for Mercurial, 'git+' for Git). For example::

       $ pip install -E ~/var/srvc/ckan.net/pyenv hg+http://bitbucket.org/okfn/ckanext-disqus

2. Add it to the CKAN config. The config file may have a filepath something like: '~/var/srvc/ckan.net/ckan.net.ini'. The plugins variable is in the '[app:main]' section under 'ckan.plugins'. e.g.::

       [app:main]
       ckan.plugins = disqus

   If you have multiple plugins, separate them with spaces::

       ckan.plugins = disqus amqp myplugin


3. Restart WSGI, which usually means restarting Apache::

       $ sudo /etc/init.d/apache2 restart


Concepts
--------

The plug-in implementation is based on the PyUtilib_ component architecture (PCA). In
summary:

#. The CKAN core contains various ``ExtensionPoints``, each specifying a point
   where plugins may hook into the software.

#. Each ``ExtensionPoint`` specifies the interface that corresponding plugins
   must implement. For example a plugin wanting to hook into the SQLAlchemy
   mapping layer would need to implement the ``IMapperExtension`` interface.

#. Plugin objects must be registered as setuptools entry points. The
   ``ckan.plugins`` configuration directive is searched for names of plugin entry
   points to load and activate.

Writing an extension point
--------------------------

This describes how to add an extension point to make core CKAN code pluggable.

Suppose you have a class such as this::

        class DataInputDoodah(object):

                def accept_new_data(self, data):
                        self.data = data

And you want plugins to hook into ``accept_new_data`` to modify the data.

You would start by declaring an interface specifying the methods that plugin
classes must provide. You would add the following code to
``ckan/plugins/interfaces.py``::

        class IDataMunger(Interface):

                def munge(self, data):
                        return data

Now you can add an extension point into the original class, so that it looks
like this::

        from ckan.plugins import ExtensionPoint, IDataMunger

        class DataInputDooDah(object):

                extensionpoint = ExtensionPoint(IDataMunger)

                def accept_new_data(self, data):

                        for service in self.extensionpoint:
                                data = service.munge(data)

                        self.data = data

Any registered plugins that implement ``IDataMunger`` will then be available in
your class via the ``ExtensionPoint``.

See the pyutilib_ documentation for more information on creating interfaces and
extension points.


Writing plugins
----------------

This describes how to create a plugin that works with a previously defined
extension point.

Plugins should be created as standalone packages in the ``ckanext.plugins``
namespace and installed in the virtualenv used by CKAN. The following commands
create a new skeleton plugin package and install it in your virtualenv::

        % paster create -t ckan_plugin myplugin
        % pip -E /path/to/virtualenv -e myplugin

Plugins are created within the ``ckanext.plugins`` namespace package.

The plugin class
````````````````

A plugin is a class that derives from ``ckan.plugins.Plugin`` or more
commonly ``SingletonPlugin``.

It must also implement one of the plugin interfaces exposed in
``ckan.plugins.interfaces``. The choice interface determines the
functionality the plugin is expected to provide.

See the `ckan.plugins API documentation`_ for a complete list of available interfaces.

A skeleton plugin implementation hooking into the database mapping layer looks
like this::

        from logging import getLogger
        from ckan.plugins import implements, SingletonPlugin 
        from ckan.plugins import IMapperExtension

        log = getLogger(__name__)

        class InsertLoggerPlugin(SingletonPlugin):
                """
                Emit a log line when objects are inserted into the database
                """

                implements(IMapperExtension, inherit=True)

                def after_insert(mapper, connection, instance):
                        log.info('Object %r was inserted', instance)


Registration and entry points
`````````````````````````````

CKAN finds plugins by searching for entry points in the group ``ckan.plugin``.
For example, the following line in your package's ``setup.py`` will register an
entry point for a plugin called ``my_plugin``::

    entry_points={
        'ckan.plugins': ['my_plugin=ckanext.plugins.my_plugin:PluginClass']
    }

The entry point will be called without any parameters and must return an
instance of ``ckan.plugins.Plugin``.

Testing plugins
---------------

When writing tests for your plugin code you will need setup and teardown code
similar to the following to ensure that your plugin is loaded while testing::

        from ckan import plugins

        class TestMyPlugin(TestCase):

                @classmethod
                def setup_class(cls):
                        # Use the entry point name of your plugin as declared
                        # in your package's setup.py
                        plugins.load('my_plugin')

                @classmethod
                def teardown_class(cls):
                        plugins.reset()


The exception to using plugins.load() is for when your plug-in is for routes.
In this case, the plugin must be configured before the WSGI app is started. 
Here is an example test set-up::

        from paste.deploy import appconfig
        import paste.fixture
        from ckan.config.middleware import make_app
        from ckan.tests import conf_dir

        class TestMyRoutesPlugin(TestCase):

                @classmethod
                def setup_class(cls):
                    config = appconfig('config:test.ini', relative_to=conf_dir)
                    config.local_conf['ckan.plugins'] = 'my_routes_plugin'
                    wsgiapp = make_app(config.global_conf, **config.local_conf)
                    cls.app = paste.fixture.TestApp(wsgiapp)


.. Links
.. -----
.. 
.. Etherpad discussion: http://ckan.okfnpad.org/plugins
.. 
.. Existing plugin implementations (using the old API), comments from are pudo:
.. 
.. - Comments: http://bitbucket.org/pudo/ckandisqus
.. - Weird stuff: http://bitbucket.org/pudo/ckanextdeliverance
.. - Shouldn't be a plugin, but typical for localized versions: http://bitbucket.org/pudo/offenedaten
.. - and probably the largest yet least plugin-ish: http://bitbucket.org/okfn/ckanextiati
.. - this is what I want to avoid: http://bitbucket.org/okfn/ckanextiati/src/tip/ckanext/iati/authz.py

ckan.plugins API documentation
-------------------------------

.. automodule:: ckan.plugins.core
        :members:

.. automodule:: ckan.plugins.interfaces
        :members:

.. _disqus: http://disqus.com/
.. _pyutilib: https://software.sandia.gov/trac/pyutilib
.. _deliverance: http://pypi.python.org/pypi/Deliverance
.. _RabbitMQ: http://www.rabbitmq.com/
