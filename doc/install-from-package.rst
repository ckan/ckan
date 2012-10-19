==============================
Option 1: Package Installation
==============================

This section describes how to install CKAN from packages. This is the recommended and by far the easiest way to install CKAN.

The overall process is the following:

* :ref:`prepare-your-system`
* :ref:`run-package-installer`
* :ref:`upgrading`

.. note:: We recommend you use package installation unless you are a core CKAN developer or have no access to Ubuntu 10.04 through any of the methods above, in which case, you should use :doc:`install-from-source`.

For support during installation, please contact `the ckan-dev mailing list <http://lists.okfn.org/mailman/listinfo/ckan-dev>`_.

.. _prepare-your-system:

Prepare your system
-------------------

Package install requires you to use Ubuntu 10.04: either locally, through a virtual machine or Amazon EC2.

You can:

* Use Ubuntu 10.04 directly.
* :doc:`install-from-package-virtualbox`. This is suitable if you want to host your CKAN instance on a machine running any other OS.
* :doc:`install-from-package-amazon`. This is suitable if you want to host your CKAN instance in the cloud, on a ready-made Ubuntu OS.


.. _run-package-installer:

Run the Package Installer
-------------------------

On your Ubuntu 10.04 system, open a terminal and run these commands to prepare your system (replace `MAJOR_VERSION` with a suitable value):

::

    sudo apt-get update
    sudo apt-get install -y wget
    echo "deb http://apt.ckan.org/ckan-1.MAJOR_VERSION lucid universe" | sudo tee /etc/apt/sources.list.d/ckan.list
    wget -qO- "http://apt.ckan.org/packages_public.key" | sudo apt-key add -
    sudo apt-get update

Now you are ready to install. If you already have a PostgreSQL and Solr
instance that you want to use set up on a different server you don't need to install
``postgresql-8.4`` and ``solr-jetty`` locally. For most cases you'll need CKAN,
PostgreSQL and Solr all running on the same server so run:

::

    sudo apt-get install -y ckan postgresql-8.4 solr-jetty

The install will whirr away. With ``ckan``, ``postgresql-8.4`` and
``solr-jetty`` chosen, over 180Mb of packages will be downloaded (on a clean
install). This will take a few minutes, then towards the end
you'll see this:

::

    Setting up solr-jetty (1.4.0+ds1-1ubuntu1) ...
     * Not starting jetty - edit /etc/default/jetty and change NO_START to be 0 (or comment it out).

If you've installed ``solr-jetty`` locally you'll also need to configure your
local Solr server for use with CKAN. You can do so like this:

::

    sudo ckan-setup-solr

This changes the Solr schema to support CKAN, sets Solr to start automatically
and then starts Solr. You shouldn't be using the Solr instance for anything
apart from CKAN because the command above modifies its schema.

You can now create CKAN instances as you please using the
``ckan-create-instance`` command. It takes these arguments:

Instance name

    This should be a short letter only string representing the name of the CKAN
    instance. It is used (amongst other things) as the basis for:

    * The directory structure of the instance in ``/var/lib/ckan``, ``/var/log/ckan``, ``/etc/ckan`` and elsewhere
    * The name of the PostgreSQL database to use
    * The name of the Solr core to use

Instance Hostname/domain name

    The hostname that this CKAN instance will be hosted at. It is
    used in the Apache configuration virutal host in
    ``/etc/apache2/sites-available/<INSTANCE_NAME>.common`` so that Apache can resolve
    requests directly to CKAN.

    If you are using Amazon EC2, you will use the public DNS of your server as
    this argument. These look something like
    ``ec2-79-125-86-107.eu-west-1.compute.amazonaws.com``. If you are using a VM,
    this will be the hostname of the VM you have configured in your ``/etc/hosts``
    file.

    If you install more than one CKAN instance you'll need to set different
    hostnames for each. If you ever want to change the hostname CKAN responds on
    you can do so by editing ``/etc/apache2/sites-available/<INSTANCE_NAME>.common`` and
    restarting apache with ``sudo /etc/init.d/apache2 restart``.

Local PostgreSQL support (``"yes"`` or ``"no"``)

    If you specify ``"yes"``, CKAN will also set up a local database user and
    database and create its tables, populating them as necessary and saving the
    database password in the config file. You would normally say ``"yes"`` unless
    you plan to use CKAN with a PostgreSQL on a remote machine.

    If you choose ``"no"`` as the third parameter to tell the install command not
    to set up or configure the PostgreSQL database for CKANi you'll then need to
    perform any database creation and setup steps manually yourself.

For production use the second argument above is usually the domain name of the
CKAN instance, but in our case we are testing, so we'll use the default
hostname buildkit sets up to the server which is ``default.vm.buildkit`` (this
is automatically added to your host machine's ``/etc/hosts`` when the VM is
started so that it will resovle from your host machine - for more complex
setups you'll have to set up DNS entries instead).

Create a new instance like this:

::

    sudo ckan-create-instance std default.vm.buildkit yes

You'll need to specify a new instance name and different hostname for each CKAN
instance you set up.

Don't worry about warnings you see like this during the creation process, they are harmless:

::

    /usr/lib/pymodules/python2.6/ckan/sqlalchemy/engine/reflection.py:46: SAWarning: Did not recognize type 'tsvector' of column 'search_vector' ret = fn(self, con, *args, **kw)

You can now access your CKAN instance from your host machine as http://default.vm.buildkit/

.. tip ::

    If you get taken straight to a login screen it is a sign that the PostgreSQL
    database initialisation may not have run. Try running:

    ::

        INSTANCE=std
        sudo paster --plugin=ckan db init --config=/etc/ckan/${INSTANCE}/${INSTANCE}.ini

    If you specified ``"no"`` as part of the ``create-ckan-instance`` you'll
    need to specify database and solr settings in ``/etc/ckan/std/std.ini``. At the
    moment you'll see an "Internal Server Error" from Apache. You can always
    investigate such errors by looking in the Apache and CKAN logs for that
    instance.

Sometimes things don't go as planned so let's look at some of the log files.

This is the CKAN log information (leading data stripped for clarity):

::

    $ sudo -u ckanstd tail -f /var/log/ckan/std/std.log
    WARNI [vdm] Skipping adding property Package.all_revisions_unordered to revisioned object
    WARNI [vdm] Skipping adding property PackageTag.all_revisions_unordered to revisioned object
    WARNI [vdm] Skipping adding property Group.all_revisions_unordered to revisioned object
    WARNI [vdm] Skipping adding property PackageGroup.all_revisions_unordered to revisioned object
    WARNI [vdm] Skipping adding property GroupExtra.all_revisions_unordered to revisioned object
    WARNI [vdm] Skipping adding property PackageExtra.all_revisions_unordered to revisioned object
    WARNI [vdm] Skipping adding property Resource.all_revisions_unordered to revisioned object
    WARNI [vdm] Skipping adding property ResourceGroup.resources_all to revisioned object

No error here, let's look in Apache (leading data stripped again) in the case
where we chose ``"no"`` to PostgreSQL installation:

::

    $ tail -f /var/log/apache2/std.error.log
        self.connection = self.__connect()
      File "/usr/lib/pymodules/python2.6/ckan/sqlalchemy/pool.py", line 319, in __connect
        connection = self.__pool._creator()
      File "/usr/lib/pymodules/python2.6/ckan/sqlalchemy/engine/strategies.py", line 82, in connect
        return dialect.connect(*cargs, **cparams)
      File "/usr/lib/pymodules/python2.6/ckan/sqlalchemy/engine/default.py", line 249, in connect
        return self.dbapi.connect(*cargs, **cparams)
    OperationalError: (OperationalError) FATAL:  password authentication failed for user "ckanuser"
    FATAL:  password authentication failed for user "ckanuser"
     None None

There's the problem. If you don't choose ``"yes"`` to install PostgreSQL, you
need to set up the ``sqlalchemy.url`` option in the config file manually. Edit
it to set the correct settings:

::

    sudo -u ckanstd vi /etc/ckan/std/std.ini

Notice how you have to make changes to CKAN config files and view CKAN log files
using the username set up for your CKAN user.

Each instance you create has its own virtualenv that you can install extensions
into at ``/var/lib/ckan/std/pyenv`` and its own system user, in this case
``ckanstd``.  Any time you make changes to the virtualenv, you should make sure
you are running as the correct user otherwise Apache might not be able to load
CKAN.  For example, say you wanted to install a ckan extension, you might run:

::

    sudo -u ckanstd /var/lib/ckan/std/pyenv/bin/pip install <name-of-extension>

You can now configure your instance by editing ``/etc/ckan/std/std.ini``:

::

    sudo -u ckanstd vi /etc/ckan/std/std.ini

After any change you can touch the ``wsgi.py`` to tell Apache's mod_wsgi that
it needs to take notice of the change for future requests:

::

    sudo touch /var/lib/ckan/std/wsgi.py

Or you can of course do a full restart if you prefer:

::

    sudo /etc/init.d/apache2 restart

.. caution ::

    CKAN has etag caching enabled by default which encourages your browser to cache
    the homepage and all the dataset pages. This means that if you change CKAN's
    configuration you'll need to do a 'force refresh' by pressing ``Shift + Ctrl +
    F5`` together or ``Shift + Ctrl + R`` (depending on browser) before you'll see
    the change.

One of the key things it is good to set first is the ``ckan.site_description``
option. The text you set there appears in the banner at the top of your CKAN
instance's pages.

You can enable and disable particular CKAN instances by running:

::

    sudo a2ensite std
    sudo /etc/init.d/apache2 reload

or:

::

    sudo a2dissite std
    sudo /etc/init.d/apache2 reload

respectively.

Now you should be up and running. Don't forget you there is the a help page for
dealing with :doc:`common-error-messages`.

Visit your CKAN instance - either at your Amazon EC2 hostname, or at on your
host PC or virtual machine. You'll be redirected to the login screen because
you won't have set up any permissions yet, so the welcome screen will look
something like this.

.. image :: images/9.png
  :width: 807px

You can now proceed to :doc:`post-installation`.

.. warning ::

    If you use the ``ckan-create-instance`` command to create more than one
    instance there are a couple of things you need to be aware of. Firstly, you
    need to change the Apache configurations to put ``mod_wsgi`` into *daemon* mode
    and secondly you need to watch your Solr search index carefully to make sure
    that the different instances are not over-writing each other's data.

    To change the Apache configuration uncomment the following lines for each
    instance in ``/etc/apache2/sites-available/std.common`` and make sure
    ``${INSTANCE}`` is replaced with your instance name:

    ::

        # Deploy as a daemon (avoids conflicts between CKAN instances)
        # WSGIDaemonProcess ${INSTANCE} display-name=${INSTANCE} processes=4 threads=15 maximum-requests=10000
        # WSGIProcessGroup ${INSTANCE}

    If you don't do this and you install different versions of the same Python
    packages into the different pyenvs in ``/var/lib/ckan`` for each instance,
    there is a chance the CKAN instances might use the wrong package.

    If you want to make sure that you CKAN instances are using different Solr indexes, you can
    configure Solr to run in multi-core mode. See :ref:`solr-multi-core` for more details.

CKAN packaging is well tested and reliable with single instance CKAN installs.
Multi-instance support is newer, and whilst we believe will work well, hasn't
had the same degree of testing. If you hit any problems with multi-instance
installs, do let us know and we'll help you fix them.

.. _upgrading:

Upgrading a package install
---------------------------

Starting on CKAN 1.7, the updating process is different depending on wether
the new version is a major release (e.g. 1.7, 1.8, etc) or a minor release
(e.g. 1.7.X, 1.7.Y). Major releases can introduce backwards incompatible
changes, changes on the database and the Solr schema. Each major release and
its subsequent minor versions has its own apt repository (Please note that this
was not true for 1.5 and 1.5.1 versions).

Minor versions, on the other hand contain only bug fixes, non-breaking
optimizations and new translations.

A fresh install or upgrade from another major version will install the latest minor
version.

Upgrading from another major version
************************************
If you already have a major version installed via package install and wish to upgrade, you can try the approach documented below.

.. caution ::

   Always make a backup first and be prepared to start again with a fresh install of the newer version of CKAN.

First remove the old CKAN code (it doesn't remove your data):

::

    sudo apt-get autoremove ckan

Then update the repositories (replace `MAJOR_VERSION` with a suitable value):

::

    echo "deb http://apt.ckan.org/ckan-1.MAJOR_VERSION lucid universe" | sudo tee /etc/apt/sources.list.d/ckan.list
    wget -qO- "http://apt.ckan.org/packages_public.key" | sudo apt-key add -
    sudo apt-get update

Install the new CKAN and update all the dependencies:

::

    sudo apt-get install ckan

Now you need to make some manual changes. In the following commands replace ``std`` with the name of your CKAN instance. Perform these steps for each instance you wish to upgrade.

#. Upgrade the Solr schema

    .. note ::

       This only needs to be done if the Solr schema has been updated between major releases. The CHANGELOG or the announcement
       emails will specify if this is the case.

   Configure ``ckan.site_url`` or ``ckan.site_id`` in ``/etc/ckan/std/std.ini`` for SOLR search-index rebuild to work. eg:

   ::

       ckan.site_id = yoursite.ckan.org

   The site_id must be unique so the domain name of the CKAN instance is a good choice.

   Install the new schema:

   ::

       sudo rm /usr/share/solr/conf/schema.xml
       sudo ln -s /usr/lib/pymodules/python2.6/ckan/config/solr/schema-1.4.xml /usr/share/solr/conf/schema.xml

#. Upgrade the database

   First install pastescript:

   ::

       sudo -u ckanstd /var/lib/ckan/std/pyenv/bin/pip install --ignore-installed pastescript

   Then upgrade the database:

   ::

       sudo -u ckanstd /var/lib/ckan/std/pyenv/bin/paster --plugin=ckan db upgrade --config=/etc/ckan/std/std.ini

   When upgrading from CKAN 1.5 you may experience error ``sqlalchemy.exc.IntegrityError: (IntegrityError) could not create unique index "user_name_key``. In this case then you need to rename users with duplicate names, before the database upgrade will run successfully. For example::

        sudo -u ckanstd paster --plugin=pylons shell /etc/ckan/std/std.ini
        model.meta.engine.execute('SELECT name, count(name) AS NumOccurrences FROM "user" GROUP BY name HAVING(COUNT(name)>1);').fetchall()
        users = model.Session.query(model.User).filter_by(name='https://www.google.com/accounts/o8/id?id=ABCDEF').all()
        users[1].name = users[1].name[:-1]
        model.repo.commit_and_remove()

#. Rebuild the search index (this can take some time - e.g. an hour for 5000 datasets):

   ::

       sudo -u ckanstd /var/lib/ckan/std/pyenv/bin/paster --plugin=ckan search-index rebuild --config=/etc/ckan/std/std.ini

#. Restart Apache

   ::

       sudo /etc/init.d/apache2 restart


Upgrading from the same major version
*************************************

If you want to update to a new minor version of a major release (e.g. upgrade
to 1.7.1 to 1.7, or to 1.7.2 from 1.7.1), then you only need to update the
`python-ckan` package to get the latest changes::

    sudo apt-get install python-ckan

.. caution::

    This assumes that you already have installed CKAN via package install. If
    not, do not install this single package, follow the instructions on :ref:`run-package-installer`

After upgrading the package, you need to restart Apache for the effects to take
place::

   sudo /etc/init.d/apache2 restart




