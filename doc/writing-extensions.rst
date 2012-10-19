===============================
Understand and Write Extensions
===============================

If you want to extend CKAN core functionality, the best way to do so is by writing extensions. 

Extensions allow you to customise CKAN for your own requirements, without interfering with the basic CKAN system.

To meet the need to customize CKAN efficiently, we have introduced the concepts of CKAN extensions and plugin
interfaces. These work together to provide a simple mechanism to extend core CKAN functionality.

.. warning:: This is an advanced topic. We are working to make the most popular extensions more easily available as Debian packages. 

.. note:: The terms **extension** and **plugin interface** have very precise meanings: the use of the generic word **plugin** to describe any way in which CKAN might be extended is deprecated.

.. contents ::

CKAN Extensions
---------------

Extensions are implemented as *namespace packages* under the ``ckanext``
package which means that they can be imported like this:

::

    $ python
    >>> import ckanext.example

Individual CKAN *extensions* may implement one or more *plugin interfaces* 
to provide their functionality.

Creating CKAN Extensions
~~~~~~~~~~~~~~~~~~~~~~~~

All CKAN extensions must start with the name ``ckanext-``. You can create your
own CKAN extension like this:

::

    (pyenv)$ paster create -t ckanext ckanext-myextension

You'll get prompted to complete a number of variables which will be used in your dataset. You change these later by editing the generated ``setup.py`` file. Here's some example output:

::

    Selected and implied templates:
      ckan#ckanext  CKAN extension project template
    
    Variables:
      egg:      ckanext_myextension
      package:  ckanextmyextension
      project:  ckanext-myextension
    Enter version (Version (like 0.1)) ['']: 0.4
    Enter description (One-line description of the package) ['']: Great extension package
    Enter author (Author name) ['']: James Gardner
    Enter author_email (Author email) ['']: james.gardner@okfn.org
    Enter url (URL of homepage) ['']: http://jimmyg.org
    Enter license_name (License name) ['']: GPL
    Creating template ckanext
    Creating directory ./ckanext-myextension
      Directory ./ckanext-myextension exists
      Skipping hidden file pyenv/src/ckan/ckan/pastertemplates/template/.setup.py_tmpl.swp
      Recursing into ckanext
        Creating ./ckanext-myextension/ckanext/
        .svn/ does not exist; cannot add directory
        Recursing into +project+
          Creating ./ckanext-myextension/ckanext/myextension/
          .svn/ does not exist; cannot add directory
          Copying __init__.py to ./ckanext-myextension/ckanext/myextension/__init__.py
          .svn/ does not exist; cannot add file
        Copying __init__.py to ./ckanext-myextension/ckanext/__init__.py
        .svn/ does not exist; cannot add file
      Copying setup.py_tmpl to ./ckanext-myextension/setup.py
      .svn/ does not exist; cannot add file
    Running pyenv/bin/python setup.py egg_info

Once you've run this, you should now install the extension in your virtual environment:

::

    (pyenv)$ cd ckanext-myextension
    (pyenv)$ python setup.py develop
    (pyenv)$ python
    Python 2.6.6 (r266:84292, Oct  6 2010, 16:19:55)
    [GCC 4.1.2 20080704 (Red Hat 4.1.2-48)] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import ckanext.myextension
    >>>

.. note:: 
    Running ``python setup.py develop`` will add a ``.egg-link`` file to your python
    site-packages directory (which is on your python path). 
    This allows your extension to be imported and used, with
    any changes made to the extension source code showing up immediately without needing
    to be reinstalled, which is very useful during development.

    To instead install a python package by copying all of the files to the site-packages directory
    run ``python setup.py install``.

To build useful extensions you need to be able to "hook into" different parts
of CKAN in order to extend its functionality. You do this using CKAN's plugin
architecture. We'll look at this in the next section. 


Plugins: An Overview
--------------------

Plugin interfaces provide a specification which extensions can implement in
order to "hook into" core CKAN functionality. 

The CKAN plugin implementation is based on the PyUtilib_ component architecture
(PCA). Here's a quick summary, we'll go through all this in much more detail in
a minute:

#. The CKAN core contains various *plugin interfaces*, each specifying a set of methods
   where plugins may hook into the software. For example a plugin wanting to hook into the SQLAlchemy
   mapping layer would need to implement the ``IMapperExtension`` interface.

#. A plugin is a class that derives from ``ckan.plugins.Plugin`` or more
   commonly ``SingletonPlugin``. It must also implement one of the plugin 
   interfaces exposed in ``ckan.plugins.interfaces``. The choice interface 
   determines the functionality the plugin is expected to provide.

#. Plugin objects must be registered as setuptools entry points. The
   ``ckan.plugins`` configuration directive is searched for names of plugin entry
   points to load and activate.



Here's a list of some of the more commonly used plugin interfaces:


``IDatasetForm``
    Provide a custom dataset form and schema.

``IMapper``
    Listens and react to every database change.

``IRoutes`` and ``IController``
    Provide an implementation to handle a particular URL.

``IGenshiStreamFilter``
    Intercept template rendering to modify the output.

``IDomainObjectModification``
    Listens for changes to CKAN domain objects.

``IGroupController``
    Plugins for in the groups controller. These will 
    usually be called just before committing or returning the
    respective object, i.e. all validation, synchronization 
    and authorization setup are complete. 

``IConfigurable``
    Pass configuration to plugins and extensions.

``IAuthorizer``
    Allows customisation of the default Authorization behaviour.

If you look in `ckan/plugins/interfaces.py
<https://github.com/okfn/ckan/blob/master/ckan/plugins/interfaces.py>`_ you
will see the latest plugin interfaces. 
Alternatively see the `Plugin API documentation`_ below.

.. .. note::
..    The existing 'IRoutesExtension', 'IMapperExtension' and 'ISessionExtension'
..    should be renamed in the code to not have the word 'Extension' in their names.


.. _PyUtilib: https://software.sandia.gov/trac/pyutilib

Example CKAN Extension
----------------------

A example CKAN extension can be found at http://github.com/okfn/ckanext-example.
Have a look at the README file for installation instructions.


Publishing Extensions
---------------------

At this point you might want to share your extension with the public. 

First check you have chosen an open source licence (e.g. the `MIT
<http://opensource.org/licenses/mit-license.html>`_ licence) and then 
update the ``long_description`` variable in ``setup.py`` to
explain what the extension does and which entry point names a user of the
extension will need to add to their ``ckan.plugins`` configuration.

Once you are happy, run the following commands to register your extension on
the Python Package Index:

::

    python setup.py register
    python setup.py sdist upload

You'll then see your extension at http://pypi.python.org/pypi. Others will
be able to install your plugin with ``pip``.

Finally, please also add a summary of your extension and its entry points to the Extensions page at
http://wiki.ckan.org/Extensions.


Writing a Plugin Interface
--------------------------

This describes how to add a plugin interface to make core CKAN code pluggable. 

Suppose you have a class such as this::

    class DataInput(object):

        def accept_new_data(self, data):
            self.data = data

And you want plugins to hook into ``accept_new_data`` to modify the data.

You would start by declaring an interface specifying the methods that plugin
classes must provide. You would add the following code to
``ckan/plugins/interfaces.py``::

    class IDataMunger(Interface):

        def munge(self, data):
            return data

Now you can tell this class that its plugins are anything that implements ``IDataMunger`` like this::

    from ckan.plugins import PluginImplementations, IDataMunger

    class DataInput(object):

        plugins = PluginImplementations(IDataMunger)

        def accept_new_data(self, data):
           for plugin in self.plugins:
               data = plugin.munge(data)
           self.data = data

Any registered plugins that implement ``IDataMunger`` will then be available in
your class via ``self.plugin``.

See the pyutilib_ documentation for more information on creating interfaces and
plugins. However, be aware that pyutilib uses slightly different terminology. It
calls ``PluginImplementations`` ``ExtensionPoint`` and it calls instances of a
plugin object a *service*.


Testing
-------


Testing CKAN Extensions
~~~~~~~~~~~~~~~~~~~~~~~

CKAN extensions ordinarily have their own ``test.ini`` that refers to the CKAN ``test.ini``, so you can run them in exactly the same way. For example::

    cd ckanext-dgu
    nosetests ckanext/dgu/tests --ckan
    nosetests ckanext/dgu/tests --ckan --with-pylons=test-core.ini

To test your changes you'll need to use the ``paster serve`` command from the ``ckan`` directory:

::

    paster serve --reload -c <path to your CKAN config file>

You should also make sure that your CKAN installation passes the developer tests, as described in :doc:`test`.


Testing Plugins
~~~~~~~~~~~~~~~

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

The exception to using ``plugins.load()`` is for when your plug-in is for routes.
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

At this point you should be able to write your own plugins and extensions
together with their tests.


Ordering of Extensions
----------------------

.. caution ::
 
  The order in which extensions are initially loaded is **different** to the order that their plugins are run.

The order in which extensions are initially loaded is as follows:

1. System plugins (in setup.py under ``ckan.system_plugins``).

2. In order of the plugins specified in the config file: ``plugins =``.

3. If more than one module has a plugin with the same name specified in the config, then all those are loaded, in the order the modules appear in ``sys.path``.

The order that a plugins are run in, for example the order that IRoutes extensions have their ``before_map`` method run, is alphabetical by the plugin class.

e.g. here is the order for these four extensions: ``<Plugin DguInventoryPlugin>``, ``<Plugin FormApiPlugin>``, ``<Plugin StatsPlugin>``, ``<Plugin WalesThemePlugin>``

(This alphabetical ordering is done by ``pyutilib.component.core:ExtensionPoint.extensions()``)


Plugin API Documentation
------------------------

Libraries Available To Extensions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As well as using the variables made available to them by implementing various
plugin hooks, extensions will likely want to be able to use parts of the CKAN
core library.  To allow this, CKAN provides a stable set of modules that
extensions can use safe in the knowledge the interface will remain stable,
backward-compatible and with clear deprecation guidelines as development of
CKAN core progresses.  This interface is available in
``ckan.plugins.toolkit.toolkit``.

Guidelines for writing extensions:

- Use the plugins toolkit, described above.

- Extensions should use actions where possible via ``get_action()``.

- No foreign key constraints into core as these cause problems.
  
.. Did we decide upon this, this seems like quite a restriction?

- The ``Session`` object is available through the toolkit.

.. todo:: Anything else?

Core Plugin Reference
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: ckan.plugins.core
        :members:

CKAN Interface Reference
~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: ckan.plugins.interfaces
        :members:
