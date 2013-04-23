==========
Extensions
==========

CKAN extensions are a powerful way to extend and customize core CKAN
functionality, without modifying or interfering with CKAN core itself.

An extension can provide one or more plugins that can be enabled to modify
CKAN.

Core Extensions
---------------

CKAN comes with some extensions built-in.  We call these `Core Extensions`
and you can just enable the plugins they provide.  There is no need to
install them first.

These are the available plugins

* datastore - ???
* jsonpreview - Preview json resources
* multilingual - ???
* pdfpreview - Preview pdf resources via JavaScript library
* reclinepreview - Preview resources via recline library, graphs etc
* resourceproxy - ????
* stats - Show stats and visuals about datasets

Non-Core Extensions
-------------------

Many other extensions are available and may be used with CKAN.  These will
need to be installed.  Every extension should include instructions on how to
install and configure it.  `Extension listing on the CKAN-wiki
<https://github.com/okfn/ckan/wiki/List-of-extensions>`_.


Enabling a Plugin
-----------------

1. Add the names of the extension's plugins to the CKAN config file in the
   ``[app:main]`` section under ``ckan.plugins``. If your extension implements
   multiple different plugin interfaces, separate them with spaces e.g.::

       [app:main]
       ckan.plugins = stats jsonpreview

2. To have this configuration change take effect it CKAN should be
   restarted, which usually means restarting Apache::

       sudo /etc/init.d/apache2 restart

Your extension should now be enabled. You can disable it at any time by
removing it from the list of ``ckan.plugins`` in the config file and
restarting CKAN.

Plugins are processed in the order they are defined in the config.


==================
Writing Extensions
==================

Plugins: An Overview
--------------------

CKAN provides a number of plugin interfaces.  An extension can use one or
more of these interfaces to interact with CKAN.  Each interface specifies
one or more methods that CKAN will call to use the extension.

Extensions are created as classes inheriting from either the `Plugin` or
`SingletonPlugin` base classes.  Most Extensions use the `SingletonPlugin`
base class and we advise you to use this if possible.

Having created your class you need to inherit from one or more plugin
interfaces to allow CKAN to interact with your extension.  When specifying
the interfaces that will be implemented you must remember to either (a)
define all methods required by the interface or (b) use the `inherits=True`
parameter which will use the interfaces default methods for any that you
have not defined.

.. Note::
    When writing extensions it is important to keep your code separate from
    CKAN by not importing ckan modules, so that internal CKAN changes do not
    break your code between releases.  You can however import ckan.plugins
    without this risk.

Libraries Available To Extensions
---------------------------------

As well as using the variables made available to them by implementing
various plugin hooks, extensions will likely want to be able to use parts of
the CKAN core library.  To allow this, CKAN provides a stable set of modules
that extensions can use safe in the knowledge the interface will remain
stable, backward-compatible and with clear deprecation guidelines as
development of CKAN core progresses.  This interface is available in
:doc:`toolkit`.

Guidelines for writing extensions:
----------------------------------

- Use the plugins toolkit, described above.

- Extensions should use actions where possible via ``get_action()``. This
  function is available in the toolkit.

- No foreign key constraints into core as these cause problems.

.. Did we decide upon this, this seems like quite a restriction?

.. todo:: Anything else?


Creating CKAN Extensions
------------------------

All CKAN extensions must start with the name ``ckanext-``. You can create
your own CKAN extension like this (you must be in your CKAN pyenv):

::

    (pyenv)$ paster create -t ckanext ckanext-myextension

You'll get prompted to complete a number of variables which will be used in
your dataset. You change these later by editing the generated ``setup.py``
file.

Once you've run this, you should now install the extension in your virtual environment:

::

    (pyenv)$ cd ckanext-myextension
    (pyenv)$ python setup.py develop

.. note::
    Running ``python setup.py develop`` will add a ``.egg-link`` file to
    your python site-packages directory (which is on your python path).
    This allows your extension to be imported and used, with any changes
    made to the extension source code showing up immediately without needing
    to be reinstalled, which is very useful during development.

    To instead install a python package by copying all of the files to the
    site-packages directory run ``python setup.py install``.


Testing
=======

Testing CKAN Extensions
~~~~~~~~~~~~~~~~~~~~~~~

CKAN extensions ordinarily have their own ``test.ini`` that refers to the CKAN ``test.ini``, so you can run them in exactly the same way. For example::

    cd ckanext-dgu
    nosetests ckanext/dgu/tests --ckan
    nosetests ckanext/dgu/tests --ckan --with-pylons=test-core.ini


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

    from pylons import config
    import paste.fixture
    from ckan.config.middleware import make_app

    class TestMyRoutesPlugin(TestCase):

        @classmethod
        def setup_class(cls):
            cls._original_config = config.copy()
            config['ckan.plugins'] = 'my_routes_plugin'
            wsgiapp = make_app(config['global_conf'], **config.local_conf)
            cls.app = paste.fixture.TestApp(wsgiapp)

        @classmethod
        def teardown_class(cls):
            config.clear()
            config.update(cls._original_config)

At this point you should be able to write your own plugins and extensions
together with their tests.


Plugin API Documentation
========================

Core Plugin Reference
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: ckan.plugins.core
        :members:

CKAN Interface Reference
~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: ckan.plugins.interfaces
        :members:
