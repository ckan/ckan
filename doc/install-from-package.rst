==============================
Option 1: Package Installation
==============================

This section describes how to install CKAN from packages. This is the recommended and by far the easiest way to install CKAN.

Package install requires you to use Ubuntu 10.04: either locally, through a virtual machine or Amazon EC2. Your options are as follows:

* Using Ubuntu 10.04 directly.
* :ref:`using-virtualbox`. This is suitable if you want to host your CKAN instance on a machine running any other OS. 
* :ref:`using-amazon`. This is suitable if you want to host your CKAN instance in the cloud, on a ready-made Ubuntu OS.
* :ref:`upgrading`. If you've already got a CKAN 1.5 installed from packages, follow this guide to upgrade to CKAN 1.5.1

.. note:: We recommend you use package installation unless you are a core CKAN developer or have no access to Ubuntu 10.04 through any of the methods above, in which case, you should use :doc:`install-from-source`.

For support during installation, please contact `the ckan-dev mailing list <http://lists.okfn.org/mailman/listinfo/ckan-dev>`_. 

Prepare your System
--------------------

CKAN runs on Ubuntu 10.04. If you are already using Ubuntu 10.04, you can continue straight to :ref:`run-package-installer`.

However, if you're not, you can either use VirtualBox to set up an Ubuntu VM on Windows, Linux, Macintosh and Solaris. Alternatively, you can use an Amazon EC2 instance.

.. _using-virtualbox:


Option A: Using VirtualBox
++++++++++++++++++++++++++

This option is suitable if you want to install CKAN on a machine running an OS other than Ubuntu 10.04. `VirtualBox <http://www.virtualbox.org>`_ lets you set up a virtual machine to run Ubuntu 10.04. 

Pre-requisites and Downloads
****************************

First, check your machine meets `the pre-requisites for VirtualBox <http://www.virtualbox.org/wiki/End-user_documentation>`_. These include a fairly recent processor and some spare memory.

Then download the installation files. 

* `Download the VirtualBox installer <http://www.virtualbox.org/wiki/Downloads>`_.
* `Download the Ubuntu image <http://www.ubuntu.com/download/ubuntu/download>`_ - make sure you choose Ubuntu 10.04.

Install VirtualBox
******************

.. note::

  This tutorial is for a Mac, but you can find instructions for installing VirtualBox on any OS `in the VirtualBox Manual <http://www.virtualbox.org/manual/ch02.html>`_.

To install, double-click on the VirtualBox installer:

.. image:: images/virtualbox1-package.png
   :width: 807px
   :alt: The VirtualBox installer - getting started

Click Continue to begin the installation process. Enter your password when required, and wait for the installation to finish.

Create Your Virtual Machine
***************************

Go to Applications and open VirtualBox, then click New:

.. image:: images/virtualbox4-newvm.png
   :alt: The VirtualBox installer - the New Virtual Machine Wizard

Give your VM a name - we'll call ours ``ubuntu_ckan``. Under **OS Type**, choose **Linux** and **Ubuntu (32 or 64-bit)**.

.. image:: images/virtualbox5-vmtype.png
   :alt: The VirtualBox installer - choosing your operating system

Leave the memory size as 512MB, and choose **Create new hard disk** (be aware that for production use you should probably allow 1.5GB RAM). This will open a new wizard:

.. image:: images/virtualbox6-vmloc.png
   :alt: The VirtualBox installer - creating a new hard disk

You can leave the defaults unchanged here too - click **Continue**, and then **Done**, and **Done** again, to create a new VM. 

Next, choose your VM from the left-hand menu, and click **Start**:

.. image:: images/virtualbox7-startvm.png
   :alt: Starting your new VM

This will open the First Run Wizard:

.. image:: images/virtualbox8-firstrun.png
   :alt: The VirtualBox First Run Wizard

After clicking **Continue**, you'll see **Select Installation Media**. This is where we need to tell our VM to boot from Ubuntu. Click on the file icon, and find your Ubuntu ``.iso`` file: 

.. image:: images/virtualbox9-iso.png
   :alt: When you get to Select Installation Media, choose your Ubuntu .iso file

Click **Done**, wait for a few seconds, and you will see your Ubuntu VM booting. 

Set Up Ubuntu
*************

During boot, you will be asked if you want to try Ubuntu, or install it. Choose **Install Ubuntu**:

.. image:: images/virtualbox11-ubuntu.png
   :width: 807px
   :alt: Booting Ubuntu - choose the Install Ubuntu option

You can then follow the usual Ubuntu installation process. 

After Ubuntu is installed, from the main menu, choose **System > Administration > Update Manager**. You'll be asked if you want to install updates - say yes. 

When all the updates have been downloaded and installed, you'll be prompted to reboot Ubuntu. 

At this point, you can proceed to :ref:`run-package-installer`.

.. _using-amazon:

Option B: Using Amazon EC2
++++++++++++++++++++++++++

If you prefer to run your CKAN package install in the cloud, you can use an Amazon EC2 instance, which is a fairly cheap and lightweight way to set up a server.

Create an Amazon Account
************************

If you don't already have an Amazon AWS account you'll need to create one first.  You can `create an Amazon AWS account for EC2 here <http://aws.amazon.com/ec2/>`_.

Configure EC2
*************

Once you have an EC2 account, you'll need to configure settings for your CKAN instance. 

Start by logging into your `Amazon AWS Console <https://console.aws.amazon.com/s3/home>`_ and click on the EC2 tab. 

Select the region you want to run your CKAN instance in - the security group you set up is region-specific. In this tutorial, we use EU West, so it will be easier to follow if you do too.

.. image :: images/1.png
 
Set up a Security Group
^^^^^^^^^^^^^^^^^^^^^^^

Click the **Security Groups** link in the **My Resources** section in the right-hand side of the dashboard.

.. image :: images/2.png
   :width: 807px

Create a security group called ``web_test`` that gives access to ports 22, 80 and 5000 as shown below. This is needed so that you'll actually be able to access your server once it is created. You can't change these settings once the instance is running, so you need to do so now.

.. image :: images/3a.png
   :width: 807px

.. image :: images/3b.png
   :width: 807px

Create a Keypair
^^^^^^^^^^^^^^^^

Now create a new keypair  ``ckan_test`` to access your instance:

.. image :: images/4.png
   :width: 807px

When you click **Create**, your browser will prompt you to save a keypair called ``ckan_test.pem``:

.. image :: images/5.png
   :width: 807px

In this tutorial, we save the keypair in ``~/Downloads/ckan_test.pem``, but you should save it
somewhere safe. 

.. note :: If you plan to boot your EC2 instance from the command line, you need to remember where you've put this file. 


Boot the EC2 Image
******************

CKAN requires Ubuntu 10.04 to run (either the i386 or amd64
architectures). Luckily Canonical provide a `range of suitable images <http://uec-images.ubuntu.com/releases/10.04/release/>`_.

The cheapest EC2 instance is the micro one, but that isn't very powerful, so in this tutorial,
we'll use the 32-bit small version.

We're in ``eu-west-1`` and we'll use an instance-only image (i.e. all the data will be lost when you shut it down) so we need the `ami-3693a542 <https://console.aws.amazon.com/ec2/home?region=eu-west-1#launchAmi=ami-3693a542>`_ AMI. 

.. note ::

   There are more recent Ubuntu images at http://cloud.ubuntu.com/ami/ but we need the older 10.04 LTS release.

At this point, you can either boot this image from the AWS
console or launch it from the command line.


Option 1: Boot the EC2 Image AMI via the AWS Console
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

From the EC2 dashboard, choose **Launch instance >**:

.. image :: images/2.png
  :width: 807px
  :alt: Choose launch instance from the EC2 dashboard

Now work through the wizard as shown in the following screenshots.

In the first step search for ``ami-3693a542`` and select it from the results (it may take a few seconds for Amazon to find it). 

.. warning ::

   No image other than ``ami-3693a542`` will work with CKAN.

.. image :: images/i1.png
  :width: 807px
  :alt: Search for image ami-3693a542

You can keep the defaults for all of the following screens:

.. image :: images/i2.png
  :width: 807px
  :alt: Keep the defaults while setting up your instance
.. image :: images/i3.png
  :width: 807px
  :alt: Keep the defaults while setting up your instance
.. image :: images/i4.png
  :width: 807px
  :alt: Keep the defaults while setting up your instance
.. image :: images/i5.png
  :width: 807px
  :alt: Keep the defaults while setting up your instance

Choose the ``web_test`` security group you created earlier:

.. image :: images/i6.png
  :width: 807px
  :alt: Choose the web_test security group you created earlier

Then finish the wizard:

.. image :: images/i7.png
  :width: 807px
  :alt: Finish the wizard

Finally click the **View your instances on the Instances page** link:

.. image :: images/i8.png
  :width: 807px
  :alt: View your instance

After a few seconds you'll see your instance has booted. Now skip to :ref:`log-in-to-instance`.

Option 2: Boot the EC2 Image AMI from the Command Line
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

[You can skip this section if you've just booted from the AWS console and go straight to :ref:`log-in-to-instance`]

To boot from the command line you still need the same information but you enter it in one command. I'll show you now.

Install The EC2 Tools Locally
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you are on Linux, you can just install the tools like this:

::

    sudo apt-get install ec2-ami-tools
    sudo apt-get install ec2-api-tools

If you are on Windows or Mac you'll need to `download them from the Amazon website <http://aws.amazon.com/developertools/351>`_.

Once the software is installed you can use the files you've just downloaded to do create your instance.

Get Security Certificates
~~~~~~~~~~~~~~~~~~~~~~~~~

Next click on the **Account** link, right at the top of the screen, and you'll see this screen:

.. image :: images/6.png
  :width: 807px
  :alt: The Account screen

From this screen choose **Security Credentials** from the left hand side. Once
the page has loaded scroll down and you'll see the **Access Credentials**
section. Click on the **X.509 Certificate** tab:

.. image :: images/7.png
  :width: 807px
  :alt: The Access Credentials screen

Here you'll be able to create an X.509 certificate and private key.

.. tip ::

    You can only have two X.509 certificates at any given time, so you might need
    to inactivate an old one first and then delete it before you are allowed to
    create a new one, as in the screenshot above. 

Once you click the **Create New Certificate** link you get a popup which allows
you to download the certificate and private key - do this. Once again, ours are in
``~/Downloads``, but you should save it somewhere safe. 

.. image :: images/8.png
  :width: 807px
  :alt: Download your certificate

.. tip ::

    Amazon will only give you a private key file once when you create it so
    although you can always go back to get a copy of the certificate, you can only
    get the private key once. Make sure you save it in a safe place.

You now have:

* Your private key (``pk-[ID].pem``)
* Your certificate file (``cert-[ID].pem``)
* Your new keypair (``ckan-test.pem``)

The private key and the certificate files have the same name in the ``ID`` part.

Create an Ubuntu Instance
~~~~~~~~~~~~~~~~~~~~~~~~~

Once the tools are installed, run this command:

::

    ec2-run-instances ami-3693a542 --instance-type m1.small --region eu-west-1 --group web_test \
        --key ckan_test \
        --private-key ~/Downloads/pk-[ID].pem \
        --cert ~/Downloads/cert-[ID].pem


.. note ::

   The ``--key`` argument is the name of the keypair (``ckan_test``), not the certificate
   itself (``ckan_test.pem``).

.. warning ::

   Amazon charge you for a minimum of one hour usage, so you shouldn't create and
   destroy lots of EC2 instances unless you want to be charged a lot.

.. _log-in-to-instance:

Log in to the Instance
**********************

Once your instance has booted, you will need to find out its public DNS. Give it
a second or two for the instance to load then browse to the running instance in
the AWS console. If you tick your instance you'll be able to find the public
DNS by scrolling down to the bottom of the **Description** tag.

.. image :: images/8a.png
  :width: 807px
  :alt: Find the public DNS

Here you can see that our public DNS is
``ec2-79-125-86-107.eu-west-1.compute.amazonaws.com``. The private DNS only works
from other EC2 instances so isn't any use to us.

Once you've found your instance's public DNS, ensure the key has the correct permissions:

::

    chmod 0600 "ckan_test.pem"

You can then log in like this:

::

    ssh -i ~/Downloads/ckan_test.pem ubuntu@ec2-46-51-149-132.eu-west-1.compute.amazonaws.com 

The first time you connect you'll see this, choose ``yes``:

::

    RSA key fingerprint is 6c:7e:8d:a6:a5:49:75:4d:9e:05:2e:50:26:c9:4a:71.
    Are you sure you want to continue connecting (yes/no)? yes
    Warning: Permanently added 'ec2-79-125-86-107.eu-west-1.compute.amazonaws.com,79.125.86.107' (RSA) to the list of known hosts.

When you log in you'll see a welcome message. You can now proceed to :ref:`run-package-installer`.


.. note ::

   If this is a test install of CKAN, when you have finished using CKAN, you can shut down your EC2 instance through the AWS console. 

.. warning ::

   Shutting down your EC2 instance will lose all your data. Also, Amazon charge you for a minimum usage of one hour, so don't create and  destroy lots of EC2 instances unless you want to be charged a lot!


.. _run-package-installer:

Run the Package Installer
-------------------------

On your Ubuntu 10.04 system, open a terminal and run these commands to prepare your system:

::

    sudo apt-get update
    sudo apt-get install -y wget
    echo "deb http://apt.ckan.org/ckan-1.5.1 lucid universe" | sudo tee /etc/apt/sources.list.d/okfn.list
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
    this argument. These look soemthing like
    ``ec2-46-51-149-132.eu-west-1.compute.amazonaws.com``. If you are using a VM,
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

Upgrading from CKAN 1.5
-----------------------

If you already have a CKAN 1.5 install and wish to upgrade, you can try the approach documented below.

.. caution ::

   Upgrading CKAN with packages is not well tested, so your milage may vary. Always make a backup first and be prepared to start again with a fresh 1.5.1 install.

First remove the old CKAN:

::

    sudo apt-get remove ckan

Then update the repositories:

::

    echo "deb http://apt.ckan.org/ckan-1.5.1 lucid universe" | sudo tee /etc/apt/sources.list.d/ckan.list
    wget -qO- "http://apt.ckan.org/packages_public.key" | sudo apt-key add -
    sudo apt-get update

Install the new CKAN and update all the dependencies:

::

    sudo apt-get install -y ckan
    sudo apt-get upgrade

Now you need to make some manual changes. In the following commands replace ``std`` with the name of your CKAN instance. Perform these steps for each instance you wish to upgrade.

#. Upgrade the Solr schema

   Configure ``ckan.site_url`` or ``ckan.site_id`` in ``/etc/ckan/std/std.ini`` for SOLR search-index rebuild to work. eg:

   ::

       ckan.site_id = releasetest.ckan.org

   The site_id must be unique so the domain name of the Solr instance is a good choice.

   Install the new schema:

   ::

       sudo rm /usr/share/solr/conf/schema.xml
       sudo ln -s /usr/lib/pymodules/python2.6/ckan/config/solr/schema-1.3.xml /usr/share/solr/conf/schema.xml

#. Upgrade the database

   First install pastescript:

   ::
   
       sudo -u ckanstd /var/lib/ckan/std/pyenv/bin/pip install --ignore-installed pastescript

   Then upgrade the database:

   ::

       sudo -u ckanstd /var/lib/ckan/std/pyenv/bin/paster --plugin=ckan db upgrade --config=/etc/ckan/std/std.ini

   If you get error ``sqlalchemy.exc.IntegrityError: (IntegrityError) could not create unique index "user_name_key`` then you need to rename users with duplicate names before it will work. For example::

        sudo -u ckanstd paster --plugin=pylons shell /etc/ckan/std/std.ini
        model.meta.engine.execute('SELECT name, count(name) AS NumOccurrences FROM "user" GROUP BY name HAVING(COUNT(name)>0);').fetchall()
        users = model.Session.query(model.User).filter_by(name='https://www.google.com/accounts/o8/id?id=ABCDEF').all()
        users[1].name = users[1].name[:-1]
        model.repo.commit_and_remove()

#. Rebuild the search index (this can take some time):

   ::

       sudo -u ckanstd /var/lib/ckan/std/pyenv/bin/paster --plugin=ckan search-index rebuild --config=/etc/ckan/std/std.ini

#. Restart Apache

   ::

       sudo /etc/init.d/apache2 reload

