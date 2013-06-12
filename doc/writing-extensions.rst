.. todo::

   * Consistent title style
   * Autodoc'd auth functons reference

=======================
Writing CKAN extensions
=======================

CKAN can be modified and extended using extensions. Some **core extensions**
come packaged with CKAN. Core extensions don't need to be installed before you
can use them as they're installed when you install CKAN, they can simply be
enabled by following the setup instructions in each extension's documentation
(some core extensions are already enabled by default). For example, the
:doc:`datastore extension <datastore>`, :doc:`multilingual extension
<multilingual>`, and :doc:`stats extension <stats>` are all core extensions,
and the :doc:`data viewer <data-viewer>` also uses core extensions to enable
data previews for different file formats.

**External extensions** are CKAN extensions that do not come packaged with
CKAN, but must be downloaded and installed separately. A good place to find
external extensions is the
`list of extensions on the CKAN wiki <https://github.com/okfn/ckan/wiki/List-of-extensions>`_.
Again, follow each extension's own documentation to install, setup and use the
extension.

This document covers everything you need to know to write your own CKAN
extensions. The tutorial will introduce you to writing CKAN extensions, with a
step-by-step walkthrough of the development of an example extension. After that
comes all the reference documentation that extension developers need.


--------
Tutorial
--------

This tutorial will walk you through the process of creating a simple CKAN
extension, and introduce the core concepts that CKAN extension developers need
to know along the way. As an example, we'll use the ``iauthfunctions``
extension that's packaged with CKAN. This is a simple CKAN extension that
customizes some of CKAN's authorization rules.


Install CKAN
============

Before you can start developing a CKAN extension, you'll need a working source
install of CKAN on your system. If you don't have a CKAN source install
already, follow the instructions in :doc:`install-from-source` before
continuing.


Create a new empty extension
============================

.. topic:: Extensions

   A CKAN *extension* is a Python package that modifies or extends CKAN.
   Each extension contains one or more *plugins* that must be added to your
   CKAN config file to activate the extension's features.


You can use the ``paster create`` command to create an "empty" extension from
a template. First, activate your CKAN virtual environment:

.. parsed-literal::

   |activate|

When you run the ``paster create`` command, your new extension's directory will
be created in the current working directory by default (you can override this
with the ``-o`` option), so change to the directory that you want your
extension to be created in. Usually you'll want to track your extension code
using a version control system such as ``git``, so you wouldn't want to create
your extension in the ``ckan`` source directory because that directory already
contains the CKAN git repo. Let's use the parent directory instead:

.. parsed-literal::

   cd |virtualenv|/src

Now run the ``paster create`` command to create your extension::

    paster --plugin=ckan create -t ckanext ckanext-iauthfunctions

The command will ask you to answer a few questions. The answers you give will
end up in your extension's ``setup.py`` file (where you can edit them later if
you want).

Once this command has completed, your new CKAN extension's project
directory will have been created and will contain a few directories and files
to get you started::

    ckanext-iauthfunctions/
        ckanext/
            __init__.py
            iauthfunctions/
                __init__.py
        ckanext_iauthfunctions.egg-info/
        setup.py

``ckanext_iauthfunctions.egg_info`` is a directory containing automatically
generated metadata about your project. It's used by Python's packaging and
distribution tools. In general, you don't need to edit or look at anything in
this directory, and you should not add it to version control.

``setup.py`` is the setup script for your project. As you'll see later, you use
this script to install your project into a virtual environment. It contains
several settings that you'll update as you develop your project.

``ckanext/iauthfunctions`` is the Python package directory where we'll add the
source code files for our extension.


Create a plugin class
=====================

.. topic:: Plugins

   Each CKAN extension contains one or more plugins that provide the
   extension's features.


Now create the file ``ckanext-iauthfunctions/ckanext/iauthfunctions/plugin.py``
with the following contents:

.. literalinclude:: ../ckanext/examples/iauthfunctions/plugin_1.py

Our plugin is a normal Python class, named ``IAuthFunctionsPlugin`` in this
example, that inherits from CKAN's
:py:class:`~ckan.plugins.core.SingletonPlugin` class.

.. todo:: Improve the note about Plugin vs SingletonPlugin.

   *Why* should you use SingletonPlugin? What does it get you?  eg. Can you
   save stuff against self? Is it really one object instance or is it one per
   thread? What does "when CKAN starts up" mean in the context of Apache? Does
   CKAN start up for each http request? Or only when you restart Apache?

   And why might you inherit from Plugin/why might you need multiple instances
   of your class?

.. note::

   Every CKAN plugin class must inherit from either
   :py:class:`~ckan.plugins.core.Plugin`
   or :py:class:`~ckan.plugins.core.SingletonPlugin`
   If you inherit from ``SingletonPlugin`` then only one object instance of
   your plugin class will be created when CKAN starts up, and whenever CKAN
   calls one of your plugin class's methods the method will be called on this
   single object instance. Most plugin classes should inherit from
   ``SingletonPlugin``, only inherit from ``Plugin`` if you need multiple
   instances of your class to be created.


.. _setup.py:

Add the plugin to ``setup.py``
==============================

Now let's add our class to the ``entry_points`` in ``setup.py``.  This
identifies the plugin class to CKAN once the extension is installed in CKAN's
virtualenv, and associates a plugin name with the class.  Edit
``ckanext-iauthfunctions/setup.py`` and add a line to
the ``entry_points`` section like this::

    entry_points='''
        [ckan.plugins]
        iauthfunctions=ckanext.iauthfunctions.plugin:ExampleIAuthFunctionsPlugin
    ''',


Install the extension
=====================

When you :doc:`install CKAN <installing>`, you create a Python `virtual
environment <http://www.virtualenv.org>`_ in a directory on your system
(|virtualenv| by default) and install the CKAN Python package and the other
packages that CKAN depends on into this virtual environment.
Before we can use our plugin, we must install our extension into our CKAN
virtual environment.
Make sure your virtualenv is activated, change to the extension's
directory, and run ``python setup.py develop``:

.. parsed-literal::

   |activate|
   cd |virtualenv|/src/ckanext-iauthfunctions
   python setup.py develop

.. todo::

   Explain the difference between ``python setup.py develop``,
   ``python setup.py install`` and ``pip install``.


Enable the plugin
=================

An extension's plugins must be added to the :ref:`ckan.plugins` setting your
CKAN config file so that CKAN will call the plugins' methods.  The name that
you gave to your plugin class in the :ref:`left-hand-side of the assignment in
the setup.py file <setup.py>` (``iauthfunctions`` in this example) is the name
you'll use for your plugin in CKAN's config file::

    ckan.plugins = stats text_preview recline_preview iauthfunctions

You should now be able to start CKAN in the development web server and have it
start up without any problems:

.. parsed-literal::

    $ paster serve |development.ini|
    Starting server in PID 13961.
    serving on 0.0.0.0:5000 view at http://127.0.0.1:5000

If your plugin is in the :ref:`ckan.plugins` setting and CKAN starts without
crashing, then your plugin is installed and CKAN can find it. Of course, your
plugin doesn't *do* anything yet.

Troubleshooting
===============

``PluginNotFoundException``
---------------------------

If CKAN crashes with a ``PluginNotFoundException`` like this::

    ckan.plugins.core.PluginNotFoundException: iauthfunctions

then:

* Check that the name you've used for your plugin in your CKAN config file is
  the same as the name you've used in your extension's ``setup.py`` file

* Check that you've run ``python setup.py develop`` in your extension's
  directory, with your CKAN virtual environment activated. Every time you add
  a new plugin to your extension's ``setup.py`` file, you need to run
  ``python setup.py develop`` again before you can use the new plugin.

``ImportError``
---------------

If you get an ``ImportError`` from CKAN relating to your plugin, it's probably
because the path to your plugin class in your ``setup.py`` file is wrong.


Implement the IAuthFunctions plugin interface
=============================================

.. topic:: Plugin interfaces

   CKAN provides a number of
   :ref:`plugin interfaces <plugin-interfaces-reference>` that plugins must
   implement to hook into CKAN and modify or extend it. Each plugin interface
   defines a number of methods that a plugin that implements the interface must
   provide. CKAN will call your plugin's implementations of these methods, to
   allow your plugin to do its stuff.

To modify CKAN's authorization behavior, we'll implement the
:py:class:`~ckan.plugins.interfaces.IAuthFunctions` plugin interface.  This
interface defines just one method, that takes no parameters and returns a
dictionary:

.. autosummary::

   ~ckan.plugins.interfaces.IAuthFunctions.get_auth_functions

.. topic:: Action functions and authorization functions

   At this point, it's necessary to take a short diversion to explain how
   authorization is implemented in CKAN.

   Every action that can be carried out using the CKAN web interface or API is
   implemented by an *action function* in one of the four files
   ``ckan/logic/action/{create,delete,get,update}.py``.

   For example, when creating a dataset either using the web interface or using
   the ``package_create`` API call,
   ``ckan/logic/action/create.py:package_create()`` is called. There's also
   ``package_show()`` and ``package_delete()``.

   Each action function has a corresponding authorization function in one of
   the four files ``ckan/logic/auth/{create,delete,get,update}.py``,
   CKAN calls this authorization function to decide whether
   the user is authorized to carry out the requested action. For example, when
   creating a new package using the web interface or API,
   ``ckan/logic/auth/create.py:package_create()`` is called.

   The ``IAuthFunctions`` plugin interface allows CKAN plugins to hook into
   this authorization system to add their own authorization functions or
   override the default authorization functions. In this way, plugins have
   complete control to customize CKAN's auth.

Whenever a user tries to create a new group via the web interface or the API,
CKAN calls ``ckan/logic/auth/create.py:group_create()`` to decide whether to
allow the action. Let's override this function and simply prevent anyone from
creating new groups. Edit your ``plugin.py`` file so that it looks like this:

.. literalinclude:: ../ckanext/examples/iauthfunctions/plugin_2.py

.. todo::

   ``inherit=False`` or ``True`` or not at all?


Our ``ExampleIAuthFunctionsPlugin`` class now calls
:func:`~ckan.plugins.core.implements` to tell CKAN that it implements the
:class:`~ckan.plugins.interfaces.IAuthFunctions` interface, and provides an
implementation of the interface's
:func:`~ckan.plugins.interfaces.IAuthFunctions.get_auth_functions`
method that overrides the default ``group_create`` function with a custom
one. This custom function simply returns ``{'success': False}`` to refuse to
let anyone create a new group.

If you now restart CKAN and reload the ``/group`` page, as long as you're not a
sysadmin user you should see the ``Add Group`` button disappear. The CKAN web
interface automatically hides buttons that the user is not authorized to use.
Visiting ``/group/new``  directly will redirect you to the login page. If you
try to call ``group_create`` via the API, you'll receive an
``AuthorizationError`` from CKAN::

    $ http 127.0.0.1:5000/api/3/action/group_create Authorization:f0c9ba9a-3211-4c9d-be3c-aca412ca31e0 name=my_group
    HTTP/1.0 403 Forbidden
    Access-Control-Allow-Headers: X-CKAN-API-KEY, Authorization, Content-Type
    Access-Control-Allow-Methods: POST, PUT, GET, DELETE, OPTIONS
    Access-Control-Allow-Origin: *
    Cache-Control: no-cache
    Content-Length: 2866
    Content-Type: application/json;charset=utf-8
    Date: Wed, 12 Jun 2013 13:38:01 GMT
    Pragma: no-cache
    Server: PasteWSGIServer/0.5 Python/2.7.4

    {
        "error": {
            "__type": "Authorization Error",
            "message": "Access denied"
        },
        "help": "Create a new group.\n\n    You must be authorized to create groups.\n\n    Plugins may change the parameters of this function depending on the value\n    of the ``type`` parameter, see the ``IGroupForm`` plugin interface.\n\n    :param name: the name of the group, a string between 2 and 100 characters\n        long, containing only lowercase alphanumeric characters, ``-`` and\n        ``_``\n    :type name: string\n    :param id: the id of the group (optional)\n    :type id: string\n    :param title: the title of the group (optional)\n    :type title: string\n    :param description: the description of the group (optional)\n    :type description: string\n    :param image_url: the URL to an image to be displayed on the group's page\n        (optional)\n    :type image_url: string\n    :param type: the type of the group (optional), ``IGroupForm`` plugins\n        associate themselves with different group types and provide custom\n        group handling behaviour for these types\n        Cannot be 'organization'\n    :type type: string\n    :param state: the current state of the group, e.g. ``'active'`` or\n        ``'deleted'``, only active groups show up in search results and\n        other lists of groups, this parameter will be ignored if you are not\n        authorized to change the state of the group (optional, default:\n        ``'active'``)\n    :type state: string\n    :param approval_status: (optional)\n    :type approval_status: string\n    :param extras: the group's extras (optional), extras are arbitrary\n        (key: value) metadata items that can be added to groups, each extra\n        dictionary should have keys ``'key'`` (a string), ``'value'`` (a\n        string), and optionally ``'deleted'``\n    :type extras: list of dataset extra dictionaries\n    :param packages: the datasets (packages) that belong to the group, a list\n        of dictionaries each with keys ``'name'`` (string, the id or name of\n        the dataset) and optionally ``'title'`` (string, the title of the\n        dataset)\n    :type packages: list of dictionaries\n    :param groups: the groups that belong to the group, a list of dictionaries\n        each with key ``'name'`` (string, the id or name of the group) and\n        optionally ``'capacity'`` (string, the capacity in which the group is\n        a member of the group)\n    :type groups: list of dictionaries\n    :param users: the users that belong to the group, a list of dictionaries\n        each with key ``'name'`` (string, the id or name of the user) and\n        optionally ``'capacity'`` (string, the capacity in which the user is\n        a member of the group)\n    :type users: list of dictionaries\n\n    :returns: the newly created group\n    :rtype: dictionary\n\n    ",
        "success": false
    }

If you're logged in as a sysadmin user however, you'll still be able to create
new groups. Sysadmin users can always carry out any action, they bypass the
authorization functions.


The plugins toolkit
===================

Let's make our custom ``group_create`` authorization function a little
smarter, and allow only users who are members of a particular group named
``curators`` to create new groups. Edit ``plugin.py`` so that it looks like
this:

.. literalinclude:: ../ckanext/examples/iauthfunctions/plugin_3.py

``context``
-----------

The ``context`` parameter of our ``group_create()`` function is a dictionary
that CKAN passes to all authorization and action functions containing some
computed variables. Our function gets the name of the logged-in user from
``context``:

.. literalinclude:: ../ckanext/examples/iauthfunctions/plugin_3.py
    :start-after: # Get the user name of the logged-in user.
    :end-before: # Get a list of the members of the 'curators' group.


``data_dict``
-------------

The ``data_dict`` parameter of our ``group_create()`` function is another
dictionary that CKAN passes to all authorization and action functions.
``data_dict`` contains any data posted by the user to CKAN, eg. any fields
they've completed in a web form they're submitting or any ``JSON`` fields
they've posted to the API. If we inspect the contents of the ``data_dict``
passed to our ``group_create()`` authorization function, we'll see that it
contains the details of the group the user wants to create::

       {'description': u'A really cool group',
        'image_url': u'',
        'name': u'my_group',
        'title': u'My Group',
        'type': 'group',
        'users': [{'capacity': 'admin', 'name': u'seanh'}]}

The plugins toolkit
-------------------

CKAN's :ref:`plugins toolkit <plugins-toolkit>` is a Python module containing
core CKAN functions, classes and exceptions for use by CKAN extensions.

The toolkit's :func:`~ckan.plugins.toolkit.get_action` function returns a CKAN
action function. The action functions available to extensions are the same
functions that CKAN uses internally to carry out actions when users make
requests to the web interface or API. Our code uses
:func:`~ckan.plugins.toolkit.get_action` to get the
:func:`~ckan.logic.action.get.member_list` action function, which it uses to
get a list of the members of the ``curators`` group:

.. literalinclude:: ../ckanext/examples/iauthfunctions/plugin_3.py
    :start-after: # Get a list of the members of the 'curators' group.
    :end-before: # 'members' is a list of (user_id, object_type, capacity) tuples, we're

Calling :func:`~ckan.logic.action.get.member_list` in this way is equivalent to
posting the same data dict to the ``/api/3/action/member_list`` API endpoint.
For other action functions available from
:func:`~ckan.plugins.toolkit.get_action`, see :ref:`api-reference`.

The toolkit's :func:`~ckan.plugins.toolkit.get_converter` function returns
converter functions from :mod:`ckan.logic.converters` for plugins to use.  This
is the same set of converter functions that CKAN's action functions use to
convert user-provided data. Our code uses
:func:`~ckan.plugins.toolkit.get_converter` to get the
:func:`~ckan.logic.converters.convert_user_name_or_id_to_id()` converter
function, which it uses to convert the name of the logged-in user to their user
``id``:

.. literalinclude:: ../ckanext/examples/iauthfunctions/plugin_3.py
    :start-after: # We have the logged-in user's user name, get their user id.
    :end-before: # Finally, we can test whether the user is a member of the curators group.

Finally, we can test whether the logged-in user is a member of the ``curators``
group, and allow or refuse the action:

.. literalinclude:: ../ckanext/examples/iauthfunctions/plugin_3.py
    :start-after: # Finally, we can test whether the user is a member of the curators group.
    :end-before: class ExampleIAuthFunctionsPlugin(plugins.SingletonPlugin):


Troubleshooting
===============

``AttributeError``
------------------

If you get an ``AttributeError`` like this one::

    AttributeError: 'ExampleIAuthFunctionsPlugin' object has no attribute 'get_auth_functions'

.. todo:: Can you user inherit=True to avoid having to implement them all?

it means that your plugin class does not implement one of the plugin
interface's methods. A plugin must implement every method of every plugin
interface that it implements.

Other ``AttributeError``\ s can happen if your method returns the wrong type of
value, check the documentation for each plugin interface method to see what
your method should return.

``TypeError``
------------

If you get a ``TypeError`` like this one::

    TypeError: get_auth_functions() takes exactly 3 arguments (1 given)

it means that one of your plugin methods has the wrong number of parameters.
A plugin has to implement each method in a plugin interface with the same
parameters as in the interface.


Publishing extensions
=====================

.. todo::

   How to publish an extension (eg. to github) with a README file
   that tells users how they can install it with pip.


Testing extensions
==================

.. todo:: Explain how to write tests for extensions.

   Write tests for the iauthfunctions example extension, and use them as an
   example.

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

Localizing extensions
=====================

.. todo:: Explain how to internationalize extensions.

   Internationalize the iauthfunctions example extension, and use it as an
   example.

-------------------------------------
Best practices for writing extensions
-------------------------------------

.. todo:: Write up best practices for writing extensions.

   * Keep your code separate from CKAN so that internal CKAN changes
     don't break your code between releases.
   * import style
   * Don't import ckan, use toolkit
   * Use the toolkit
   * get_action()
   * Don't edit or key to model tables


.. _plugin-interfaces-reference:

--------------------------------
CKAN plugin interfaces reference
--------------------------------

.. automodule:: ckan.plugins.core
        :members:  SingletonPlugin, Plugin, implements

.. automodule:: ckan.plugins.interfaces
        :members:

.. _plugins-toolkit:

-------------------------
Plugins toolkit reference
-------------------------

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

-----------------------------
Converter functions reference
-----------------------------

.. automodule:: ckan.logic.converters
   :members:
   :undoc-members:
