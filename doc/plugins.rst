CKAN Extensions, Plugins Interfaces and Workers
+++++++++++++++++++++++++++++++++++++++++++++++

**Note: the terms "extension", "plugin interface" and "worker"
now have very precise meanings and that the use of the generic word "plugin" to
describe any way in which CKAN might be extended is deprecated.**

.. contents ::

Background
----------

The CKAN codebase is open source so that different organisations can customise
it for their own needs. As CKAN has grown in popularity it has become
especially important to organise the code in a way that can accommodate the
customisations which different organisations require without those changes
interfering with customizations required by other organisations. 

To meet this need we have introduced the concepts of CKAN extensions, plugin
interfaces and workers. These work together to provide a simple mechanism to
extend core CKAN functionality.

Let's start by looking at extensions.

CKAN Extensions
---------------

CKAN currently has the following extensions:

* disqus_ extension for user comments
* Solr extension for full text search and result faceting
* Asyncronous queue extension based on AMQP for model update, harvesting and other operations
* Custom form extensions for different governments

.. note ::

   The form extension does not currently behave quite the same way as the other
   extensions, it will do soon.

All CKAN extensions have package names of the form ``ckanext-name`` so the
queue extension code is stored in the package ``ckanext-queue`` for example.
Extensions are implemented as *namespace packages* under the ``ckanext``
package which means that they can be imported like this:

::

    $ python
    >>> import ckanext.queue

Extensions are used for any code that is not required for the core CKAN code to
operate but which are nethertheless and important part of one or more CKAN
instances.

Individual CKAN *extensions* may implement one or more *plugin interfaces* or
*workers* to provide their functionality. You'll learn about these later on.
All CKAN extensions are described on the CKAN public wiki at
http://wiki.okfn.org/ckan/extensions. If you write an extension then do share
details of it there but also document the plugin interfaces the extension
implements so that when people install it, they will know which plugin
interfaces they need to set up in their config file.

Installing an extension
~~~~~~~~~~~~~~~~~~~~~~~

To install an extension on a CKAN instance:

1. Install the extension package code using pip. The -E parameter is for your
CKAN python environment (e.g. ``~/var/srvc/ckan.net/pyenv``). Prefix the source
url with the repo type (``hg+`` for Mercurial, ``git+`` for Git). For example::

       $ pip install -E ~/var/srvc/ckan.net/pyenv hg+http://bitbucket.org/okfn/ckanext-disqus

2. Add the names of any plugin implementations the extension uses to the CKAN
config. The config file may have a filepath something like:
``~/var/srvc/ckan.net/ckan.net.ini``. The plugins variable is in the '[app:main]'
section under 'ckan.plugins'. e.g.::

       [app:main]
       ckan.plugins = disqus

   If your extension implemented multiple different plugin interfaces, separate them with spaces::

       ckan.plugins = disqus amqp myplugin

3. Restart WSGI, which usually means restarting Apache::

       $ sudo /etc/init.d/apache2 restart


Creating your own extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~

All CKAN extensions must start with the name ``ckanext-``. You can create your
own CKAN extension like this:

::

    (pyenv)$ paster create -t ckanext ckanext-myname

You'll get prompted to complete a number of variables which will be used in your package. You change these later by editing the generated ``setup.py`` file. Here's some example output:

::

    Selected and implied templates:
      ckan#ckanext  CKAN extension project template
    
    Variables:
      egg:      ckanext_myname
      package:  ckanextmyname
      project:  ckanext-myname
    Enter version (Version (like 0.1)) ['']: 0.4
    Enter description (One-line description of the package) ['']: Great extension package
    Enter author (Author name) ['']: James Gardner
    Enter author_email (Author email) ['']: james.gardner@okfn.org
    Enter url (URL of homepage) ['']: http://jimmyg.org
    Enter license_name (License name) ['']: GPL
    Creating template ckanext
    Creating directory ./ckanext-myname
      Directory ./ckanext-myname exists
      Skipping hidden file pyenv/src/ckan/ckan/pastertemplates/template/.setup.py_tmpl.swp
      Recursing into ckanext
        Creating ./ckanext-myname/ckanext/
        .svn/ does not exist; cannot add directory
        Recursing into +project+
          Creating ./ckanext-myname/ckanext/myname/
          .svn/ does not exist; cannot add directory
          Copying __init__.py to ./ckanext-myname/ckanext/myname/__init__.py
          .svn/ does not exist; cannot add file
        Copying __init__.py to ./ckanext-myname/ckanext/__init__.py
        .svn/ does not exist; cannot add file
      Copying setup.py_tmpl to ./ckanext-myname/setup.py
      .svn/ does not exist; cannot add file
    Running pyenv/bin/python setup.py egg_info

Once you've run this you should find your extension is already set up in your
virtual environment so you can import it:

::

    (pyenv)$ python
    Python 2.6.6 (r266:84292, Oct  6 2010, 16:19:55)
    [GCC 4.1.2 20080704 (Red Hat 4.1.2-48)] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import ckanext.myname
    >>>

To build useful extensions you need to be able to "hook into" different parts
of CKAN in order to extend its functionality. You do this using CKAN's plugin
architeture. We'll look at this in the next section. If you do write a CKAN
extension you may well want to publish it publicly so others can use it too.
See the `Publishing your extension`_ section below to find out how.

Plugins
-------

Plugin interfaces provide a specification which extensions can implement in
order to "hook into" core CKAN functionality. 

Summary
~~~~~~~

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


``IMapper``

    Listens and react to every database change

``IRoutes`` and ``IController``

    Provide an implementation to handle a particular URL

``IGenshiStreamFilter``

    Intercept template rendering to modify the output

``ISession``

``IDomainObjectModification``

``IGroupController``

    Plugins for in the groups controller. These will 
    usually be called just before committing or returning the
    respective object, i.e. all validation, synchronization 
    and authorization setup are complete. 

``IConfigurable``
    Pass configuration to plugins and extensions

If you look in `ckan/plugins/interfaces.py
<https://bitbucket.org/okfn/ckan/src/default/ckan/plugins/interfaces.py>`_ you
will see the latest plugin interfaces. Alternativlly see the `Plugin API
documentation`_ below.

.. note ::

   The existing 'IRoutesExtension', 'IMapperExtension' and 'ISessionExtension'
   should be renamed in the code to not have the word 'Extension' in their names.

An Example
~~~~~~~~~~

Plugin interfaces are basically just Python classes where each method is a hook
which allows a plugin that uses the interface to be notified when it is called.

As an example, let's look at a plugin which gets configuration options from a
config file and is called each time a template is rendered in order to add some
HTML to the page.

.. tip ::

   This example is based on real code used to implement the ``ckanext-discus`` plugin
   to add commenting to packages. You can see the latest version of this code at
   http://bitbucket.org/okfn/ckanext-disqus/src/tip/ckanext/plugins/disqus/__init__.py.

First we set up logging and some helpers we'll need from Genshi to transfor the stream:

::

    import logging
    log = logging.getLogger(__name__)
    
    import html
    from genshi.core import TEXT
    from genshi.input import HTML
    from genshi.filters import Transformer

Then we import the CKAN plugin code:

::

    from ckan.plugins.core import SingletonPlugin, implements
    from ckan.plugins.interfaces import IConfigurable, IGenshiStreamFilter

In this case we are implementing both the ``IConfigurable`` and
``IGenshiStreamFilter`` plugin interfaces in out plugin class. The
``IConfigurable`` plugin interface defines a ``configure()`` method which will
be is called on out plugin to let it know about configuration options. The
``IGenshiStreamFilter`` plugin interface defines a ``filter()`` method which
will be called on the plugin to give it the oppurtunity to change the template
before the HTML is returned to the browser.

Let's have a look at the code:

::

    class Disqus(SingletonPlugin):
        """
        Insert javascript fragments into package pages and the home page to 
        allow users to view and create comments on any package. 
        """
        
        implements(IConfigurable)
        implements(IGenshiStreamFilter)
        
        def configure(self, config):
            """ 
            Called upon CKAN setup, will pass current configuration dict
            to the plugin to read custom options. 
            """
            self.disqus_name = config.get('disqus.name', None)
            if self.disqus_name is None:
                log.warn("No disqus forum name is set. Please set \
                    'disqus.name' in your .ini!")
                self.disqus_name = 'ckan'
            
        def filter(self, stream):
            """
            Required to implement IGenshiStreamFilter; will apply some HTML 
            transformations to the page currently rendered. Depends on Pylons
            global objects, how can this be fixed without obscuring the 
            inteface? 
            """
            
            from pylons import request, tmpl_context as c 
            routes = request.environ.get('pylons.routes_dict')
            
            if routes.get('controller') == 'package' and \
                routes.get('action') == 'read' and c.pkg.id:
                data = {'name': self.disqus_name, 
                        'identifier': 'pkg-' + c.pkg.id}
                stream = stream | Transformer('body')\
                    .append(HTML(html.BOTTOM_CODE % data))
                stream = stream | Transformer('body//div[@id="comments"]')\
                    .append(HTML(html.COMMENT_CODE % data))
            
            if routes.get('controller') == 'home' and \
                routes.get('action') == 'index':
                data = {'name': self.disqus_name}
                stream = stream | Transformer('body//\
                    div[@id="main"]//ul[@class="xoxo"]')\
                    .append(HTML(html.LATEST_CODE % data))
            
            return stream

Notice that the ``Disqus`` class explicitly states that it implements ``IConfigurable``
and ``IGenshiStreamFilter`` with these two lines:

::

        implements(IConfigurable)
        implements(IGenshiStreamFilter)

Also notice that ``Disqus`` inherits from ``SingletonPlugin``. This means that
only one instance of the plugin is needed to provide the service. There is also
a ``Plugin`` class for occasions where you need multiple instances.

.. autoclass:: ckan.plugins.core.Plugin

.. autoclass:: ckan.plugins.core.SingletonPlugin

By carefully choosing the plugin interfaces your plugin uses you can hook into
lots of parts of CKAN. Later on you'll see how to write your own plugin
interfaces to define your own "hooks". Before we can use the ``Disqus`` plugin
there is one more thing to do: add it to the extension and set an *entry point*.

Setting the entry point
~~~~~~~~~~~~~~~~~~~~~~~

Imagine the code above was saved into a file named ``disqus.py`` in the
``ckanext-myname/ckanext/myname`` directory of the extension that was created earlier by the
``paster create -t ckanext ckanext-myname`` command.

At this point CKAN still doesn't know where to find your plugin, even though
the module is installed. To find the plugin it looks up an *entry point*. An
entry point is just a feature of setuptools that links a string in the form
``package_name.entry_point_name`` to a particular object in Python code.

.. tip ::

   If you are interested in reading a tutorial about entry points see:

   * http://reinout.vanrees.org/weblog/2010/01/06/zest-releaser-entry-points.html
   * http://jimmyg.org/blog/2010/python-setuptools-egg-plugins.html


CKAN finds plugins by searching for entry points in the group ``ckan.plugin``.


Entry points are defined in a package's ``setup.py`` file. If you look in the
``setup.py`` file for the ``ckanext-myname`` extension you'll see these
lines commented out towards the end:

::

        entry_points=\
        """
        [ckan.plugins]
        # Add plugins here, eg
        # myplugin=ckanext.myname:PluginClass
        """,

The entry point will be called without any parameters and must return an
instance of ``ckan.plugins.Plugin``.

To enable the ``Disqus`` plugin uncomment the bottom line and change it to this:

::

        disqus_example=ckanext.myname:Disqus

Any time you change the ``setup.py`` file you will need to run one of these two
commands again before the change will take effect:

::

    python setup.py develop
    python setup.py egg_info

With your entry point in place and installed you can now add the extension to
your CKAN config as described earlier. To add our example Disqus plugin you
would change your ``~/var/srvc/ckan.net/ckan.net.ini`` config file like this:

::

       [app:main]
       ckan.plugins = disqus_example

Note that the name of the plugin implementation that you give to
``ckan.plugins`` is always the same as the name of the entry point you've
defined in the ``setup.py`` file. It is therefore important that you don't
choose an entry point name that is being used by in any existing extension to
refer to its plugins.

The same extension can have multiple different plugins, all implementing
different interfaces to provide useful functionality. For each new plugin your
extension implements you need to add another entry point (remembering to re-run
``python setup.py develop`` if needed). Your users will then need to add the
new entry point name to their ``ckan.plugins`` config option too.

Writing a database plugin
~~~~~~~~~~~~~~~~~~~~~~~~~

You've seen how to use ``IConfigurable`` and ``IGenshiStreamFilter``, here's
another example which implements ``IMapperExtension`` to log messages after any
record is inserted into the database.

::

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

Authorization Group Plugins
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are writing an authorization group plugin you might like to use the code
at this URL as a basis:

http://bitbucket.org/okfn/ckanextiati/src/tip/ckanext/iati/authz.py

Publishing Your Extension
~~~~~~~~~~~~~~~~~~~~~~~~~

At this point you might want to share your extension with the public. First
check you have chosen an open source license (`MIT
<http://opensource.org/licenses/mit-license.html>`_ license is fine for
example) and then update the ``long_description`` variable in ``setup.py`` to
explain what the extension does and which entry point names a user of the
extension will need to add to their ``ckan.plugins`` configuration.

Once you are happy, run the following commands to register your extension on
the Python Package Index:

::

    python setup.py register
    python setup.py sdist upload

You'll then see your extension at http://pypi.python.org/pypi. Others will then
be able to install your plugin with ``pip``.

You should also add a summary of your extension and its entry points to
http://wiki.okfn.org/ckan/extensions. You can create a new account if you need
to.

Writing a plugin interface
~~~~~~~~~~~~~~~~~~~~~~~~~~

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
plugins. Be aware though that pyutilib uses slightly different terminology. It
calls ``PluginImplementations`` ``ExtensionPoint`` and it calls instances of a
plugin object a *service*.

Testing plugins
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
together with their tests. Over time we hope to move more functionality out
into CKAN extensions.

Plugin API documentation
~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: ckan.plugins.core
        :members:

.. automodule:: ckan.plugins.interfaces
        :members:

.. _disqus: http://disqus.com/
.. _pyutilib: https://software.sandia.gov/trac/pyutilib
.. _deliverance: http://pypi.python.org/pypi/Deliverance
.. _RabbitMQ: http://www.rabbitmq.com/


The Queue Extension
-------------------

** Note: the queue extension currently isn't working correctly. These docs
may not work for you**

Certain tasks that CKAN performs lend themselves to the use of a queue system.
Queue systems can be very simple. At their heart is the idea that you have two
separate processes, a *publisher* and a *consumer*. The publisher publishes a
message of some description to the queue and at another time, the consumer
takes that message off the queue and processes it.

By writing code that puts things on the queue and then writing workers to take
things off, you can build lots of useful functionality. At the moment we are
writing facilities to check for broken links and harvest documents from geodata
servers. 

To use the queue in CKAN you need the ``ckanext-queue`` package. To install the
latest version of ``ckanext-queue`` in editable more so that you can look at
the source code run:

::

    pip install -e hg+http://bitbucket.org/okfn/ckanext-queue#egg=ckanext-queue

You will then see the source code in ``/pyenv/src/ckanext-queue/ckanext/queue``
and ``README`` file in ``/pyenv/src/ckanext-queue/README.md``.

Installing ``ckanext-queue`` will also install a ``worker`` command you will
use in a minute to run workers against the queue.

Internally the queue extension uses the ``carrot`` library so that we could
potentially use different queue backends at some point in the future. For the
moment only the AMQP backend is supported so let's install an AMQP server
called RabbitMQ.

Installing RabbitMQ
~~~~~~~~~~~~~~~~~~~

CentOS
``````

First you need to install Erlang. To do that first install its dependencies:

::

    yum install ncurses-devel flex.x86_64 m4.x86_64 openssl-devel.x86_64 unixODBC-devel.x86_64


Install erlang like this:

::


    wget http://www.erlang.org/download/otp_src_R14B.tar.gz
    tar zxfv otp_src_R14B.tar.gz
    cd otp_src_R14B
    LANG=C; export LANG
    ./configure --prefix=/opt/erlang_R14B
    make
    make install

Next download and install RabbitMQ:

::

    wget http://www.rabbitmq.com/releases/rabbitmq-server/v2.2.0/rabbitmq-server-2.2.0-1.noarch.rpm
    rpm -Uhv --no-deps rabbitmq-server-2.2.0-1.noarch.rpm

Finally edit the ``/etc/init.d/rabbitmq-server`` script so that it uses the correct path for your erlang install. Change this line

::

    PATH=/sbin:/usr/sbin:/bin:/usr/bin
    
to:

::

    PATH=/sbin:/usr/sbin:/bin:/usr/bin:/opt/erlang_R14B/bin:/opt/erlang_R14B/lib

You can start it like this:

::

    /etc/init.d/rabbitmq-server start

Ubuntu
``````

Just run:

::

    sudo apt-get install rabbitmq-server

Working Directly with Carrot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As you learned earlier, CKAN uses carrot with the ``pyamqplib`` backend. Carrot is well documented at this URL:

http://ask.github.com/carrot/introduction.html

Before you learn how to use the tools that ``ckanext-queue`` uses to work with
the queue, it is instructive to see a simple example that uses carrot directly.

Save this as ``publisher.py``:

::

    from carrot.connection import BrokerConnection
    conn = BrokerConnection(
        hostname="localhost",
        port=5672,
        userid="guest", 
        password="guest",
        virtual_host="/",
    )
    
    from carrot.messaging import Publisher
    publisher = Publisher(
        connection=conn,
        exchange='local', 
        routing_key='*',
    )
    publisher.send({"import_feed": "http://cnn.com/rss/edition.rss"})
    publisher.close()

Now save this as ``consumer.py``:

::

    from carrot.connection import BrokerConnection
    conn = BrokerConnection(
        hostname="localhost",
        port=5672,
        userid="guest",
        password="guest",
        virtual_host="/",
    )
    
    from carrot.messaging import Consumer
    consumer = Consumer(
        connection=conn,
        queue='local.workerchain',
        exchange='local',
        routing_key='*',
    )
    def import_feed_callback(message_data, message):
        feed_url = message_data["import_feed"]
        print("Got message for: %s" % feed_url)
        # something importing this feed url
        # import_feed(feed_url)
        message.ack()
    consumer.register_callback(import_feed_callback)
    # Go into the consumer loop.
    consumer.wait() 

You'll notice that both examples set up a connection to the same AMQP server
with the same settings, in this case running on localhost. These also happen to
be the settings that (at the time of writing) ``ckanext-queue`` uses by default
if you don't specify other configuration settings.

Make sure you have ``ckanext-queue`` installed (so that carrot and its
dependencies are installed too) then start the consumer:

::

    python consumer.py

In a different console run the publisher:

::

    python publisher.py

The publisher will quickly exit but if you now switch back to the consumer
you'll see the message was sent to the queue and the consumer recieved it
printing this message:

::

    Got message for: http://cnn.com/rss/edition.rss    


Working with CKANext Queue
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rather than working with carrot publishers and consumers directly,
``ckanext-queue`` provides two useful Python objects to help you:

``ckanext.queue.connection.get_publisher(config)``

    This returns a ``Publisher`` instance which has a ``send()`` method for adding an item to the queue.

    The ``config`` object is the same as ``pylons.config``. If you are writing
    a standalone script, you can obtain a config object from a config file with
    code similar to this, adjusting the ``relative_to`` option as necessary:

    ::

        from paste.deploy import appconfig
        config = appconfig('config:development.ini', relative_to='pyenv/src/ckan')

``ckanext.queue.worker.Worker``

    This is a base class which you can inherit from. You can override its
    ``consume()`` method to asyncronously pull items from the queue to do useful
    things


.. note ::

   To use the queue extension you don't need to implenent any new plugin
   interfaces, you just need to use the ``get_publisher(config).send()`` method and the
   ``Worker`` class. Of course your own extension might use plugins to hook into
   other parts of CKAN to get information to put or retireve from the queue.

The worker implementation runs outside the CKAN server process, interacting
directly with both the AMQP queue and the CKAN API (to get CKAN data). The
``Worker`` class therefore subclasses both the ``carrot`` ``Consumer`` class
and the ``ckanclient`` ``CkanClient`` class so that your workers can make calls
to the running CKAN server via its API.

Writing a Publisher
```````````````````

Here's a simple publisher. Save it as ``publish_on_queue.py``:

::

    from ckanext.queue import connection
    from paste.deploy import appconfig
    
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    config = appconfig('config:ckan.ini', relative_to='.')
    publisher = connection.get_publisher(config)
    publisher.send({"import_feed": "http://cnn.com/rss/edition.rss"})
    publisher.close()
    print "Sent!"

Note that this requires a ``ckan.ini`` file relative to the current working
directory to run. Here's what a sample file will look like:

::

    [app:main]
    use = egg:ckan
    ckan.site_id = local
    queue.port = 5672 
    queue.user_id = guest
    queue.password = guest
    queue.hostnane = localhost
    queue.virtual_host = /

The idea here is that publishers you write will be able to use the same
settings as CKAN itself would. In the next section you'll see how these same
options and more to a standard CKAN install config file to enable CKAN to use
the RabbitMQ queue.

With the ``consumer.py`` script still running, execute the new script:

::

    python publish_on_queue.py

You'll see that once again the consumer picks up the message.

Writing a worker
````````````````

Now let's replace the consumer with a worker.

Each worker should have its own config file. There is an example you can use
named ``worker.cfg`` in the ``ckanext-queue`` source code. If you don't specify
a config file, the defaults will be used.

.. tip ::

   Since the ``worker.cfg`` and CKAN configuration file are both in INI file
   format you can also set these variables directly in your CKAN config file and
   point the worker directly to your CKAN config instead. It will just ignore the
   CKAN options.

In particular it is worth setting ``queue.name`` which will be used internally
by RabbitMQ.

Here's a suitable configuration for a worker:

::

    [worker]
    ckan.site_id = local_test
    ckan.site_url = http://localhost:5000
    ckan.api_key = XXX
    
    # queue.name = 
    # queue.routing_key = *
    
    # queue.port = 
    # queue.user_id =
    # queue.password = 
    # queue.hostname = 
    # queue.virtual_host =


You can run it like this:

::

    worker echo -d -c worker.cfg

The echo example comes from ``ckanext.queue.echo:EchoWorker``. It looks like this:

::

    from worker import Worker
    from pprint import pprint
    
    class EchoWorker(Worker):
    
        def consume(self, routing_key, operation, payload):
            print "Route %s, op %s" % (routing_key, operation)
            pprint(payload)
    
The ``EchoWorker`` has an entry point registered in ``ckanext-queue``'s ``setup.py`` so that the ``worker``
script in ``pyenv/bin/worker`` can find it::

    [ckan.workers]
    echo = ckanext.queue.echo:EchoWorker

When you run the ``worker`` command with the ``echo`` worker it looks up this
entry point to run the correct code.

With the worker still running, try to run the publisher again:

::

    python publish_on_queue.py

Once again the message will be output on the command line, this time via the worker.

Internally the ``worker`` script you just used uses the
``ckanext.queue.worker.WorkerChain`` class to run all workers you specify on
the command line. You can get a list of all available workers by executing
``worker`` with no arguments. 

::

    # worker
    WARNING:root:No config file specified, using worker.cfg
    ERROR:ckanext.queue.worker:No workers. Aborting.

Configuring CKAN to use the queue
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once you have installed RabbitMQ and have it running you need to enable the
CKAN queue functionality within CKAN by adding this to your CKAN config file

::

    ckan.plugins = queue

You don't need to specify configuration options to connect to RabbitMQ because
the defaults are fine.

At this point if you edit a package it should be using the queue. If you have
the echo worker running you'll see the message added to the queue.

Logging
```````

When using the queue with CKAN it is also useful to have logging set up.

To get logging working you need to modify your CKAN config file to also include
the ``queue`` logger. Here's an example:

::

    [loggers]
    keys = root, queue
    
    [handlers]
    keys = console
    
    [formatters]
    keys = generic
    
    [logger_root]
    level = INFO
    handlers = console
    
    [logger_queue]
    level = DEBUG
    handlers = console
    qualname = ckanext

You will also need to set this in your CKAN configuration and ensure any
workers and producers also set their ``ckan.site_id`` to the same value.

::

    ckan.site_id = local_test

Now that you know about extensions, plugins and workers you should be able to
extend CKAN in lots of new and interesting ways.

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

