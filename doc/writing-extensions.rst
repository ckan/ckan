------------------
Writing Extensions
------------------

.. note::

    A CKAN **extension** is a Python package that contains one or more
    **plugins**. A plugin is a class that implements one or more of CKAN's
    **plugin interfaces** to customize CKAN or add new features.


Plugins: An Overview
====================

Plugins are created as classes inheriting from either the `Plugin` or
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
=================================

As well as using the variables made available to them by implementing
various plugin hooks, extensions will likely want to be able to use parts of
the CKAN core library.  To allow this, CKAN provides a stable set of modules
that extensions can use safe in the knowledge the interface will remain
stable, backward-compatible and with clear deprecation guidelines as
development of CKAN core progresses.  This interface is available in
:doc:`toolkit`.

.. toctree::
   :hidden:

   toolkit


Example Extension
=================

::

    # Example Extension
    # This extension adds a new template helper function `hello_world` when
    # enabled templates can `{{ h.hello_world() }}` to add this html snippet.

    import ckan.plugins as p

    class HelloWorldPlugin(p.SingletonPlugin):

        p.implements(p.ITemplateHelpers)

        @staticmethod
        def hello_world():
            # This is our simple helper function.
            html = '<span>Hello World</span>'
            return p.toolkit.literal(html)

        def get_helpers(self):
            # This method is defined in the ITemplateHelpers interface and
            # is used to return a dict of named helper functions.
            return {'hello_world': hello_world}

Guidelines for writing extensions
=================================

- Use the plugins :doc:`toolkit`.

- Extensions should use actions via ``get_action()``. This function is
  available in the toolkit.

- No foreign key constraints into core as these cause problems.

.. Did we decide upon this, this seems like quite a restriction?

.. todo:: Anything else?


Creating CKAN Extensions
========================

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
-----------------------

CKAN extensions ordinarily have their own ``test.ini`` that refers to the CKAN ``test.ini``, so you can run them in exactly the same way. For example::

    cd ckanext-dgu
    nosetests ckanext/stats/tests --ckan
    nosetests ckanext/stats/tests --ckan --with-pylons=test-core.ini


Testing Plugins
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


.. _plugin-reference:

Plugin API Documentation
========================

Core Plugin Reference
---------------------

.. automodule:: ckan.plugins.core
        :members:  SingletonPlugin, Plugin, implements

CKAN Interface Reference
------------------------

.. automodule:: ckan.plugins.interfaces
        :members:


