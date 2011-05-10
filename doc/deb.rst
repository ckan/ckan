CKAN's Approach to Dependencies
+++++++++++++++++++++++++++++++

WARNING: This document is still under development, use only if you are a member
of the CKAN team who wishes to be an early adopter and are interested in
experimenting with Debian packaging.

.. contents ::

Abstract
========

A typical CKAN install can have many dependencies, in the form of required
system software such as PostgreSQL, Python libraries such as SQLAlchemy and
other CKAN extensions such as ``ckanext-qa`` or ``ckanext-harvest``.

As such we have to deal with lots of interdependencies which are often
different depending on the combinations of features a particular CKAN install
requires.

There are three audiences we are primarily targetting that our dependency
approach is designed to support:

* Interested parties who just want to get a CKAN instance installed quickly
  and easily to test it or to begin contributing
* CKAN developers who want to have editable versions of all of the dependant
  libraries so that they can improve them
* System administrators who want to be able to deploy and upgrade CKAN 
  instances quickly, easily and reliably
* Deployment and test managers who want to be confident that the live system
  is running off exactly the libraries they have tested and configured in
  exactly the same way

In order to support these three groups, we allow installation of CKAN in two ways:

* Development install via ``pip`` as described in the `README.rst <../README.html>`_ file
* Production install on Ubuntu Lucid 10.04 LTS via ``apt-get install``

The old instructions for a `production deployment <../deployment.html>`_ can
also be followed but these will be deprecated over time as the ``.deb``
packaging approach becomes better documented and understood.

Virutally all CKAN instances currently run on Ubuntu Lucid 10.04 LTS so we have
decided that this is the only officially supported production deployment
platform. Of course CKAN will also run on any modern Mac or Linux distribution
but if you go down this route you'll need to do a development install.

In this document I'll explain in detail how and why we package CKAN the way we
do.


Overview of CKAN's Structure from a Packaging Point of View
===========================================================

There are conceptually two main parts to any CKAN installation:

* Python libraries such as CKAN itself, SQLAlchemy, owslib and all the CKAN
  extensions libraries that a particular CKAN or customized CKAN rely on
* The configuration and deployment scripts that lead to a running CKAN
  application (which may be a vanilla CKAN or a client-specific version (eg
  CKAN, CKAN-DGU, CKAN-DATANL etc)
* Third party servers that CKAN relies on (eg Apache, PostgreSQL etc)

Luckily all third party servers that CKAN relies on are all ready packaged in
Ubuntu Lucid for us so we don't need to worry about packaging them. We do need
to worry about configuring them though. Let's look more at the other two.

Python Libraries
    The Python libraries CKAN relies on all have their own interdependencies.
    If the libraries have already been packaged as ``.deb`` files we don't need to worry about 
    them because their dependencies will already be specified in the package.
    Other libraries usually have their dependencies specified as the ``install_requires`` line in their
    ``setup.py`` files. For the sorts of libraries that are already available
    

Configuration and Deployment


Understanding The Dependency Difficulty
---------------------------------------

In the past 



The Three Different Requires Files for CKAN
===========================================

In order to support both a development install and a package-based install it
is important that we package the same versions of libraries that we develop
against. There are three categories of dependant Python libraries:

``present``
    Those that already exist as packages in Ubuntu Lucid

``missing``
    Those that don't exist as packages in Ubuntu Lucid

``conflict``
    Those that have a version which is different from the version in Ubuntu
    Lucid

For each of these categories we have a file in the ``ckan`` source tree's
``requires`` directory which you can view `here
<https://bitbucket.org/okfn/ckan/src/default/requires/>`_.


Understanding the ``lucid_present.txt`` File
--------------------------------------------

The Python dependencies listed in the ``lucid_present.txt`` file are ``pip``
installable links to the source tree holding the exact versions of the Python
dependencies that Ubuntu uses. By running the command below you get development
copies of the same software that Ubuntu has packaged:

::

    pip install --ignore-installed -r lucid_present.txt

We never need to package software in the ``lucid_present.txt`` file because it
already exists so most of the time you would just install it directly rather
than running the command above to get source versions. You can see the packages
you would need to install by looking at the comment at the top of the file. At
the time of writing it reads:

::

    # The CKAN dependencies are already in Lucid and should be installed via
    # apt-get if you are on that platform. If you are using a different platform
    # you can install these dependencies via pip instead.
    #
    # sudo apt-get install python-psycopg2 python-lxml python-sphinx 
    # sudo apt-get install python-pylons python-formalchemy python-repoze.who
    # sudo apt-get install python-repoze.who-plugins python-tempita python-zope.interface

Packaging Dependencies Listed in ``lucid_missing.txt``
------------------------------------------------------

.. note ::

   These are already packaged, so you don't need to package them yourself, this
   section just describes how you *could* do if you wanted to.

Python dependencies listed in the ``lucid_missing.txt`` file are ``pip``
installable links to the source tree holding the exact versions of the Python
dependencies that CKAN requries. We have an automatic build process which can
take these entries and automatically generate Ubuntu packages for them. The
resulting packages are then published to our CKAN apt repository so that they
can be automatically installed in production environments. 

To follow the automatic build process to build the missing packages you can do this:


::

    sudo apt-get install -y python wget dh-make devscripts build-essential fakeroot cdbs mercurial git-core subversion python-virtualenv
    virtualenv missing
    bin/pip install --ignore-installed -r lucid_missing.txt
    bin/pip install Buildkit

BuildKit script will build and place Debian packages in your ``missing``
directory. Make sure there is nothing in there that shouldn't be overwritten by
this script.

Now run the BuildKit command like this:

::

    cd missing
    bin/python -m buildkit.update_all .

For each package you'll be loaded into ``vim`` to edit the changelog. Save and
quit when you are done. Names, version numbers and dependencies are
automatically generated.

.. caution ::

   Most of the time you will never use the automatic process above for lazy
   batch packaging. You'll more likely generate a single package with explicit
   version numbers using the ``buildkit.deb`` command or build your package
   manually. Both approaches are described later.

Packaging Conflicting Python dependencies from ``lucid_conflicts.txt``
----------------------------------------------------------------------

.. note ::

   These are already packaged, so you don't need to package them yourself, this
   section just describes how you *could* do if you wanted to.

Python packages where CKAN depends on a version that is different from the one
in the Ubuntu Lucid repositories are handled slightly differently. If we were
to simply package them up and make them available the same way we do with
missing packages there is a slim chance that any existing software which used
the other version of the library would stop working. To avoid the risk of
interfering with other software on the system we take the following approach:

* Create a ``python-ckan-deps`` package with copies of all the libraries we need
* Change the ``python-ckan`` library to automatically try to import
  ``ckan_deps`` if it can and then adjust the Python's ``sys.path`` just for
  this instance to use the versions of the libraries in ``python-ckan-deps`` in
  preference to any other versions installed.

In this way we can use any arbitrary versions, without introducing conflicts.

.. caution ::

   The ``repoze.who`` sets of libraries are nigh-on impossible to package in
   this way so we don't actually package ``repoze.who.openid`` at all, even
   though we need a slightly more recent version. This is such an edge case
   though that you should just install it manually into the system Python
   and not worry too much for the time being.

To actually build the ``python-ckan-deps`` package we follow the semi-manual
Python packaging approach described next. (The example in the next section is
actually for a CKAN Python extension called ``python-ckanext-qa`` but the same
process applies).


Semi-Manual Python Packaging
============================

The easiest way to package a Python library is with a tool called BuildKit I
wrote specfically for the purpose. This section describes how to use it, but
even if you don't want to use BuildKit and prefer to understand the
complexities yourself by reading the `Understanding .deb files`_ section,
please read this section too so you at least understand the naming conventions
we are using.
   
:: 
   
    pip install buildkit
       
For each Python package you wish to build a ``.deb`` file for you run the
``buildkit.deb`` command. Here's an example:

::
  
    python -m buildkit.deb /path/to/virtualenv ckanext-qa 1.3~01+lucid http://ckan.org python-owslib python-ckanext-csw
  
Let's break this down.

``python -m buildkit.deb``
    This is just how you invoke the command from the command line

``/path/to/virtualenv``
    I think this can just be the path to the directory containing the 
    installed source code directory you wish to package, it doesn't
    have to be a virtualenv does it?

``ckanext-qa``
    The lowercase Python package name of the ``.deb`` file to be created. 


``1.3~01+lucid``
    The version number of the package. There are three parts to this:
x
    ``1.3``
        This should always match exactly the version number specified in the 
        ``setup.py`` file for the library being packaged.

    ``~01``
        This is an incrementing number (starting at 01 each time the version
        number above changes) which you change every time you re-package the
        same version of the code to force apt to recognise your new package 
        as being more recent than the old one, even if the underlying code 
        hasn't changed.

    ``+lucid``
        This is a string representing the Debian/Ubuntu distribution that the
        package targets. The apt repository doesn't assign any meaning to it,
        it is just that in order to eventually support more than one flavour
        of Debian or Ubuntu, the packages for each must have different 
        filenames *in addition* to being in a separate part of the apt repo
        so we begin this convention now.
 
``http://ckan.org``
    The homepage for the package, usually ckan.org for ckan extensions.

``python-owslib python-ckanext-csw ... etc``

    Any extra arguments are treated as the Debian names of dependencies.  These
    always begin ``python-`` for Python libraries and would usually follow
    ``ckanext-`` for all CKAN extensions. 

    .. tip ::

        You can also specify any other Debian
        packages here that are dependcies of the software you are packaging but as
        you'll see later it is usually best to add such dependencies to the 
        *packaged application*. See "Packaging CKAN Extensions" for more information.
    
When you run the command you will get your ``.deb`` file created. 
    
To release an upgrade of a package it must have a higher version number. There
is a chance you may want to release a more recent version of a package despite
the fact the underlying version number hasn't changed. For this reason, we
always add a ``~`` character followed by a two digit number to the end of the
actual version number as specified in ``setup.py`` for the package.

For example, if the version number for the ``ckanext-qa`` package in the
example above is ``1.3~01``, a package named
``python-ckanext-qa_1.3~01_amd64.deb`` would be produced by the command we've
looked at.

.. note ::
   
    All packages that CKAN itself depends on are already packaged according to
    the settings in the three ``requires`` files that from part of the ``ckan``
    source distribution so you shouldn't need to use the approach above to 
    package any of them, you should only need to do this for your own extensions
    or libraries they rely on which aren't already CKAN dependencies. See 
    "The Three Different Requires Files" for more information on how packaging
    of the core CKAN dependencies is managed.

Understanding ``.deb`` files
============================

Broad Structure
---------------

Naming Conventions
------------------

The base naming conventions we use for packages are as follows:

``ckan``
    Unstalls CKAN, PostgreSQL, Apache etc. It adds the ``ckan-instance-create`` command which is then the only thing you need to create a new instance.

``python-ckan``
    The CKAN Python library packaged from code at http://bitbucket.org/okfn/ckan

``python-ckanext-*``
    Any CKAN extensions (can be application extensions or library extensions)

``ckan-*``
    Installs a client specific CKAN application



The ``postinst`` and ``postrm`` files
-------------------------------------

The ``control`` file
--------------------

Extra scripts and permissions
-----------------------------

Packaging Python libraries
--------------------------



Packaging CKAN Extensions
=========================

There are two types of CKAN extension:

* Client Applications (eg ``ckanext-dgu``, ``ckanext-datanl`` etc)
* Helpful libraries (eg ``ckanext-qa``, ``ckanext-harvest``, ``ckanext-queue`` etc)

All CKAN extensions (whether client applications or helpful libraries) are
Python libraries and therefore need packaging. Their ``.deb`` filenames are the
same as the Python package names but are always prefixed with ``python-`` so
that ``ckanext-dgu`` becomes ``python-ckanext-dgu`` when packaged as a ``.deb``
and ``ckanext-harvest`` becomes ``python-ckanext-harvest`` etc.

CKAN extensions which are also client applications generally need to be
deployed and therefore need require Apache and PostgreSQL to be installed and
configured correctly too. In addition to the *python* package we therefore also
create an *application* package for the extension which is named ``ckan-``
followed by the last part of the extension name. So for ``ckanext-dgu`` two
packages are created named ``python-ckanext-dgu`` and ``ckan-dgu``. This naming
may sound slightly inconsistent but it allows a user who wishes to install a
DGU CKAN instance to just type the command below:

::

    sudo apt-get install ckan-dgu

Usually the ``ckan`` package will be a dependency of the your client
application CKAN extension. When the ``ckan`` package is installed it installs
``python-ckan`` as a dependency as well as a series of scripts in ``/usr/bin``
such as:

``ckan-create-instance``
    create a new CKAN instance 

``ckan-maintenance-mode``
    put a CKAN intance into or out of maintenence mode (prevent POSTs from
    the web user interface)

In the simple cases, these scripts can then be used in your client application
CKAN extension's ``posinst`` script to set up the custom instance. In more
complex cases you may write a ``postinst`` script from scratch. The
``postinst`` script then forms part of the package and is run by the apt system
as part of the package installation or upgrade process to configure your CKAN
instance.












Before we look at how to actually create an apt repository for your packages
and how to publish your packages to it, let's understand what a user of your
package will do to install it.

Understaning How a User Installs from an apt repository
=======================================================

A user will follow the following process:

First create the file ``/etc/apt/sources.list.d/okfn.list`` with this line, replacing ``lucid`` with the correct repo you want to use:

::

    echo "deb http://apt-alpha.ckan.org/lucid lucid universe" | sudo tee /etc/apt/sources.list.d/okfn.list

Then add the package key to say you trust packages from this repository:

::

    sudo apt-get install wget
    wget -qO-  http://apt-alpha.ckan.org/packages.okfn.key | sudo apt-key add -
    sudo apt-get update

Now you can not install a CKAN extension application, just like any other Debian package:

::

    sudo apt-get install ckan-dgu

At this point you should have a running instance. You may need to copy across
an existing database if you need your instance pre-populated with data.


Setting up a CKAN Apt Repository
================================

Now you've seen what a user expects to be able to do, let's set up the
infrastructure to make to make it happen.


From Scratch
------------

Our set up is based on `Joseph Ruscio's set up
<http://joseph.ruscio.org/blog/2010/08/19/setting-up-an-apt-repository/>`_ and
will allow us to support multiple operating systems if we want to as well as
multiple architectures. At the moment we only support Ubuntu Lucid amd64.

To help with repository management we use the ``reprepro`` tool. Despite the fact that the repositories could be set up for different OSs and versions (eg ``lenny``, ``lucid`` etc) we need to make sure that the package names are still unique. This means that we always add the distribution to the version number when we package.


The most important detail that AFAIK isn’t covered in any of the tutorials had to do with package naming conventions. The naive assumption (at least on my part) is that you’ll have a different build of your package for each distro/arch combination, and import them into your repository as such. In other words reprepro should track the distro/arch of each import. In actuality, each build’s <PACKAGE>_<VERSION>_<ARCH> must be unique, even though you specify the distro during the includedeb operation.




The Easy Way
------------

Log into the existing CKAN apt repository server and copy an existing directory
that already contains the packages you need. For example, to create a
repository for a new ``ckanext-dgu`` instance you might do:

::

    cd /var/packages/
    cp -pr lucid dgu-new

At this point you have a brand new repo, you can add new packages to it like this:

::

    cd dgu-new
    sudo reprepro includedeb lucid ~/*.deb

You can remove them like this from the same directory:

::

    sudo reprepro remove lucid python-ckan

Any time a change is made you will need to enter the passphrase for the key.


Automatic Packaging
===================

The BuildKit script will build and place Debian packages in your ``missing``
directory. Make sure there is nothing in there that shouldn't be overwritten by
this script.


Adding a Package to a Repository
================================


Packaging CKAN Itself
=====================




Why We use ``pip`` rather than ``install_requires``
===================================================


Packaging CKAN and its dependencies for a production install
============================================================

Installing a Packaged CKAN-based Site
=====================================

Testing Your Packaging in a VM
==============================

The Release Process
===================





Creating the CKAN Command
=========================

Create a directory named ``ckan``. Then within it create a ``DEBIAN`` directory with three files:

``control``:

    ::

        Package: ckan
        Version: 1.3.2~09
        Architecture: amd64
        Maintainer: James Gardner <james.gardner@okfn.org>
        Installed-Size: 0
        Depends: python-ckan
        Recommends: postgresql, curl
        Section: main/web
        Priority: extra
        Homepage: http://ckan.org
        Description: ckan
         The Data Hub

``postinst``:

    ::

        #!/bin/sh
        set -e
        # Any commands that happen after install or upgrade go here

``postrm``

    ::

        #!/bin/sh
        set -e
        # Any commands that happen after removal or before upgrade go here

Then in the ``ckan`` directory you add any files you want copied. In this case
we want a ``/usr/bin/ckan-create-instance`` script so we create the ``usr``
directory in the ``ckan`` directory at the same level as the ``DEBIAN``
directory, then create the ``bin`` directory within it and add the script in
there.

Finally we want to package up the ``.deb`` file. From within the ``ckan``
directory run this:

::

    dpkg-deb -b . ..

This will create the ``../ckan_1.3.2~09_amd64.deb`` package ready for you to
upload to the repo.

The ``ckan`` package is already created so in reality you will usually be
packaging ``ckan-<instance>``. If you make sure your package depends on
``ckan`` and ``python-ckanext-<instance>`` you can then call the ``ckan``
package's ``ckan-create-instance`` command in your ``ckan-<instance>``'s
``postinst`` command to set up Apache and PostgreSQL for the instance
automatically.


Setting up the Repositories
===========================

Build individual dependencies like this:

::

    python -m buildkit.deb . ckanext-importlib 0.1~02 http://ckan.org python-ckan
    python -m buildkit.deb . owslib 0.3.2beta~03 http://ckan.org python-lxml

    python -m buildkit.deb . ckanext-inspire 0.1~03 http://ckan.org python-ckan
    python -m buildkit.deb . ckanext-spatial 0.1~04 http://ckan.org python-ckan
    python -m buildkit.deb . ckanext-harvest 0.1~15 htthp://ckan.org python-ckan python-ckanext-spatial python-carrot
    python -m buildkit.deb . ckanext-csw 0.3~10 http://ckan.org python-ckanext-harvest python-owslib python-ckan
    python -m buildkit.deb . ckanext-dgu 0.2~11 http://ckan.org python-ckan python-ckanext-importlib python-ckanext-dgu python-ckanext-csw python-ckan python-ckanext-spatial python-ckanext-inspire
    python -m buildkit.deb . ckanext-qa 0.1~19 http://ckan.org python-ckan
    python -m buildkit.deb . ckan 1.3.4~02 http://ckan.org python-routes python-vdm python-pylons python-genshi python-sqlalchemy python-repoze.who python-repoze.who-plugins python-pyutilib.component.core python-migrate python-formalchemy python-sphinx python-markupsafe python-setuptools python-psycopg2 python-licenses python-ckan-deps

There's a dependency on postfix. Choose internet site and the default hostname unless you know better.

Once you have packages you'll want to put them in a repo. You can do that as described here:

* http://joseph.ruscio.org/blog/2010/08/19/setting-up-an-apt-repository/

Then add them like this:

::

    cd /var/packages/lucid/
    sudo reprepro includedeb lucid ~/*.deb

You can remove them like this from the same directory:

::

    sudo reprepro remove lucid python-ckan

Automatic Packaging
===================

The BuildKit script will build and place Debian packages in your ``missing``
directory. Make sure there is nothing in there that shouldn't be overwritten by
this script.

To package everything automatically, run it like this:

::

    cd missing
    bin/python -m buildkit.update_all .

For each package you'll be loaded into ``vim`` to edit the changelog. Save and
quit when you are done. Names, version numbers and dependencies are
automatically generated.

You should find all your packages nicely created now.


Next Steps
==========

* Delayed updates


Proposed Changes to CKAN
========================

* Change the config file to support file based logging by default
* Move who.ini into the config
* Add a ckan/wsgi.py for standard DGU deployment
* Modify __init__.py to change 


* No __init__.py in test directory



ubuntu@ip-10-226-226-132:/var/packages/dgu-uat$ sudo reprepro includedeb lucid /home/ubuntu/release/2011-04-18_01/*.deb
/home/ubuntu/release/2011-04-18_01/ckan_1.3.2~10_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan' '1.3.2~10' in 'lucid|universe|amd64', as it has already '1.3.4~03'.
/home/ubuntu/release/2011-04-18_01/ckan_1.3.2~11_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan' '1.3.2~11' in 'lucid|universe|amd64', as it has already '1.3.4~03'.
/home/ubuntu/release/2011-04-18_01/ckan_1.3.4~01_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan' '1.3.4~01' in 'lucid|universe|amd64', as it has already '1.3.4~03'.
/home/ubuntu/release/2011-04-18_01/ckan_1.3.4~02_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan' '1.3.4~02' in 'lucid|universe|amd64', as it has already '1.3.4~03'.
/home/ubuntu/release/2011-04-18_01/ckan_1.3.4~03_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan' '1.3.4~03' in 'lucid|universe|amd64', as it has already '1.3.4~03'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~06_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~06' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~07_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~07' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~08_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~08' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~09_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~09' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~11_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~11' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~12_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~12' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~13_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~13' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~14_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~14' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~15_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~15' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/python-ckan_1.3.4~01-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckan' '1.3.4~01-1' in 'lucid|universe|amd64', as it has already '1.3.4~02-1'.
/home/ubuntu/release/2011-04-18_01/python-ckan_1.3.4~02-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckan' '1.3.4~02-1' in 'lucid|universe|amd64', as it has already '1.3.4~02-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-csw_0.3~10-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-csw' '0.3~10-1' in 'lucid|universe|amd64', as it has already '0.3~10-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-dgu_0.2~08-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-dgu' '0.2~08-1' in 'lucid|universe|amd64', as it has already '0.2~11-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-dgu_0.2~09-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-dgu' '0.2~09-1' in 'lucid|universe|amd64', as it has already '0.2~11-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-dgu_0.2~10-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-dgu' '0.2~10-1' in 'lucid|universe|amd64', as it has already '0.2~11-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-dgu_0.2~11-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-dgu' '0.2~11-1' in 'lucid|universe|amd64', as it has already '0.2~11-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-harvest_0.1~13-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-harvest' '0.1~13-1' in 'lucid|universe|amd64', as it has already '0.1~15-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-harvest_0.1~14-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-harvest' '0.1~14-1' in 'lucid|universe|amd64', as it has already '0.1~15-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-harvest_0.1~15-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-harvest' '0.1~15-1' in 'lucid|universe|amd64', as it has already '0.1~15-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-inspire_0.1~01-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-inspire' '0.1~01-1' in 'lucid|universe|amd64', as it has already '0.1~03-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-inspire_0.1~02-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-inspire' '0.1~02-1' in 'lucid|universe|amd64', as it has already '0.1~03-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-inspire_0.1~03-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-inspire' '0.1~03-1' in 'lucid|universe|amd64', as it has already '0.1~03-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-qa_0.1~19-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-qa' '0.1~19-1' in 'lucid|universe|amd64', as it has already '0.1~19-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-spatial_0.1~01-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-spatial' '0.1~01-1' in 'lucid|universe|amd64', as it has already '0.1~04-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-spatial_0.1~03-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-spatial' '0.1~03-1' in 'lucid|universe|amd64', as it has already '0.1~04-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-spatial_0.1~04-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-spatial' '0.1~04-1' in 'lucid|universe|amd64', as it has already '0.1~04-1'.
/home/ubuntu/release/2011-04-18_01/python-owslib_0.3.2beta~03-1_amd64.deb: component guessed as 'universe'
ERROR: '/home/ubuntu/release/2011-04-18_01/python-owslib_0.3.2beta~03-1_amd64.deb' cannot be included as 'pool/universe/p/python-owslib/python-owslib_0.3.2beta~03-1_amd64.deb'.
Already existing files can only be included again, if they are the same, but:
md5 expected: 3f38d2e844c8d6ec15da6ba51910f3e2, got: ee48427eb11f8152f50f6dc93aeb70d4
sha1 expected: 87cd7724d8d8f0aaeaa24633abd86e02297771d7, got: 8476b1b0e022892ceb8a35f1848818c31d7441bf
sha256 expected: 4c9937c78be05dfa5b9dfc85f3a26a51ca4ec0a2d44e8bca530a0c85f12ef400, got: ad3f7458d069a9dd268d144577a7932735643056e45d0a30b7460c38e64057d7
size expected: 57658, got: 57656
/home/ubuntu/release/2011-04-18_01/python-owslib_0.3.2beta~04-1_amd64.deb: component guessed as 'universe'
Exporting indices...
19A05DDEB16777A2 James Gardner (thejimmyg) <james.gardner@okfn.org> needs a passphrase
Please enter passphrase:
Deleting files just added to the pool but not used (to avoid use --keepunusednewfiles next time)
deleting and forgetting pool/universe/c/ckan/ckan_1.3.2~10_amd64.deb
deleting and forgetting pool/universe/c/ckan/ckan_1.3.2~11_amd64.deb
deleting and forgetting pool/universe/c/ckan/ckan_1.3.4~01_amd64.deb
deleting and forgetting pool/universe/c/ckan/ckan_1.3.4~02_amd64.deb
deleting and forgetting pool/universe/c/ckan-dgu/ckan-dgu_0.2~06_amd64.deb
deleting and forgetting pool/universe/c/ckan-dgu/ckan-dgu_0.2~07_amd64.deb
deleting and forgetting pool/universe/c/ckan-dgu/ckan-dgu_0.2~08_amd64.deb
deleting and forgetting pool/universe/c/ckan-dgu/ckan-dgu_0.2~09_amd64.deb
deleting and forgetting pool/universe/c/ckan-dgu/ckan-dgu_0.2~11_amd64.deb
deleting and forgetting pool/universe/c/ckan-dgu/ckan-dgu_0.2~12_amd64.deb
deleting and forgetting pool/universe/c/ckan-dgu/ckan-dgu_0.2~13_amd64.deb
deleting and forgetting pool/universe/c/ckan-dgu/ckan-dgu_0.2~14_amd64.deb
deleting and forgetting pool/universe/p/python-ckan/python-ckan_1.3.4~01-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-dgu/python-ckanext-dgu_0.2~08-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-dgu/python-ckanext-dgu_0.2~09-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-dgu/python-ckanext-dgu_0.2~10-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-harvest/python-ckanext-harvest_0.1~13-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-harvest/python-ckanext-harvest_0.1~14-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-inspire/python-ckanext-inspire_0.1~01-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-inspire/python-ckanext-inspire_0.1~02-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-spatial/python-ckanext-spatial_0.1~01-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-spatial/python-ckanext-spatial_0.1~03-1_amd64.deb
Not deleting possibly left over files due to previous errors.
(To keep the files in the still existing index files from vanishing)
Use dumpunreferenced/deleteunreferenced to show/delete files without references.
1 files lost their last reference.
(dumpunreferenced lists such files, use deleteunreferenced to delete them.)
There have been errors!
(reverse-i-search)`delete': cat src/pip-^Clete-this-directory.txt 
ubuntu@ip-10-226-226-132:/var/packages/dgu-uat$ sudo reprepro deleteunreferenced  --help
Error: Too many arguments for command 'deleteunreferenced'!
Syntax: reprepro deleteunreferenced
There have been errors!
ubuntu@ip-10-226-226-132:/var/packages/dgu-uat$ sudo reprepro deleteunreferenced 
deleting and forgetting pool/universe/p/python-owslib/python-owslib_0.3.2beta~03-1_amd64.deb
ubuntu@ip-10-226-226-132:/var/packages/dgu-uat$ 
ubuntu@ip-10-226-226-132:/var/packages/dgu-uat$ sudo reprepro includedeb lucid /home/ubuntu/release/2011-04-18_01/*.deb
/home/ubuntu/release/2011-04-18_01/ckan_1.3.2~10_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan' '1.3.2~10' in 'lucid|universe|amd64', as it has already '1.3.4~03'.
/home/ubuntu/release/2011-04-18_01/ckan_1.3.2~11_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan' '1.3.2~11' in 'lucid|universe|amd64', as it has already '1.3.4~03'.
/home/ubuntu/release/2011-04-18_01/ckan_1.3.4~01_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan' '1.3.4~01' in 'lucid|universe|amd64', as it has already '1.3.4~03'.
/home/ubuntu/release/2011-04-18_01/ckan_1.3.4~02_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan' '1.3.4~02' in 'lucid|universe|amd64', as it has already '1.3.4~03'.
/home/ubuntu/release/2011-04-18_01/ckan_1.3.4~03_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan' '1.3.4~03' in 'lucid|universe|amd64', as it has already '1.3.4~03'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~06_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~06' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~07_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~07' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~08_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~08' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~09_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~09' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~11_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~11' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~12_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~12' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~13_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~13' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~14_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~14' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/ckan-dgu_0.2~15_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'ckan-dgu' '0.2~15' in 'lucid|universe|amd64', as it has already '0.2~15'.
/home/ubuntu/release/2011-04-18_01/python-ckan_1.3.4~01-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckan' '1.3.4~01-1' in 'lucid|universe|amd64', as it has already '1.3.4~02-1'.
/home/ubuntu/release/2011-04-18_01/python-ckan_1.3.4~02-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckan' '1.3.4~02-1' in 'lucid|universe|amd64', as it has already '1.3.4~02-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-csw_0.3~10-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-csw' '0.3~10-1' in 'lucid|universe|amd64', as it has already '0.3~10-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-dgu_0.2~08-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-dgu' '0.2~08-1' in 'lucid|universe|amd64', as it has already '0.2~11-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-dgu_0.2~09-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-dgu' '0.2~09-1' in 'lucid|universe|amd64', as it has already '0.2~11-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-dgu_0.2~10-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-dgu' '0.2~10-1' in 'lucid|universe|amd64', as it has already '0.2~11-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-dgu_0.2~11-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-dgu' '0.2~11-1' in 'lucid|universe|amd64', as it has already '0.2~11-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-harvest_0.1~13-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-harvest' '0.1~13-1' in 'lucid|universe|amd64', as it has already '0.1~15-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-harvest_0.1~14-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-harvest' '0.1~14-1' in 'lucid|universe|amd64', as it has already '0.1~15-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-harvest_0.1~15-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-harvest' '0.1~15-1' in 'lucid|universe|amd64', as it has already '0.1~15-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-inspire_0.1~01-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-inspire' '0.1~01-1' in 'lucid|universe|amd64', as it has already '0.1~03-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-inspire_0.1~02-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-inspire' '0.1~02-1' in 'lucid|universe|amd64', as it has already '0.1~03-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-inspire_0.1~03-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-inspire' '0.1~03-1' in 'lucid|universe|amd64', as it has already '0.1~03-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-qa_0.1~19-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-qa' '0.1~19-1' in 'lucid|universe|amd64', as it has already '0.1~19-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-spatial_0.1~01-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-spatial' '0.1~01-1' in 'lucid|universe|amd64', as it has already '0.1~04-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-spatial_0.1~03-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-spatial' '0.1~03-1' in 'lucid|universe|amd64', as it has already '0.1~04-1'.
/home/ubuntu/release/2011-04-18_01/python-ckanext-spatial_0.1~04-1_amd64.deb: component guessed as 'universe'
Skipping inclusion of 'python-ckanext-spatial' '0.1~04-1' in 'lucid|universe|amd64', as it has already '0.1~04-1'.
/home/ubuntu/release/2011-04-18_01/python-owslib_0.3.2beta~03-1_amd64.deb: component guessed as 'universe'
ERROR: '/home/ubuntu/release/2011-04-18_01/python-owslib_0.3.2beta~03-1_amd64.deb' cannot be included as 'pool/universe/p/python-owslib/python-owslib_0.3.2beta~03-1_amd64.deb'.
Already existing files can only be included again, if they are the same, but:
md5 expected: 3f38d2e844c8d6ec15da6ba51910f3e2, got: ee48427eb11f8152f50f6dc93aeb70d4
sha1 expected: 87cd7724d8d8f0aaeaa24633abd86e02297771d7, got: 8476b1b0e022892ceb8a35f1848818c31d7441bf
sha256 expected: 4c9937c78be05dfa5b9dfc85f3a26a51ca4ec0a2d44e8bca530a0c85f12ef400, got: ad3f7458d069a9dd268d144577a7932735643056e45d0a30b7460c38e64057d7
size expected: 57658, got: 57656
/home/ubuntu/release/2011-04-18_01/python-owslib_0.3.2beta~04-1_amd64.deb: component guessed as 'universe'
Exporting indices...
19A05DDEB16777A2 James Gardner (thejimmyg) <james.gardner@okfn.org> needs a passphrase
Please enter passphrase:
Deleting files just added to the pool but not used (to avoid use --keepunusednewfiles next time)
deleting and forgetting pool/universe/c/ckan/ckan_1.3.2~10_amd64.deb
deleting and forgetting pool/universe/c/ckan/ckan_1.3.2~11_amd64.deb
deleting and forgetting pool/universe/c/ckan/ckan_1.3.4~01_amd64.deb
deleting and forgetting pool/universe/c/ckan/ckan_1.3.4~02_amd64.deb
deleting and forgetting pool/universe/c/ckan-dgu/ckan-dgu_0.2~06_amd64.deb
deleting and forgetting pool/universe/c/ckan-dgu/ckan-dgu_0.2~07_amd64.deb
deleting and forgetting pool/universe/c/ckan-dgu/ckan-dgu_0.2~08_amd64.deb
deleting and forgetting pool/universe/c/ckan-dgu/ckan-dgu_0.2~09_amd64.deb
deleting and forgetting pool/universe/c/ckan-dgu/ckan-dgu_0.2~11_amd64.deb
deleting and forgetting pool/universe/c/ckan-dgu/ckan-dgu_0.2~12_amd64.deb
deleting and forgetting pool/universe/c/ckan-dgu/ckan-dgu_0.2~13_amd64.deb
deleting and forgetting pool/universe/c/ckan-dgu/ckan-dgu_0.2~14_amd64.deb
deleting and forgetting pool/universe/p/python-ckan/python-ckan_1.3.4~01-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-dgu/python-ckanext-dgu_0.2~08-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-dgu/python-ckanext-dgu_0.2~09-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-dgu/python-ckanext-dgu_0.2~10-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-harvest/python-ckanext-harvest_0.1~13-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-harvest/python-ckanext-harvest_0.1~14-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-inspire/python-ckanext-inspire_0.1~01-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-inspire/python-ckanext-inspire_0.1~02-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-spatial/python-ckanext-spatial_0.1~01-1_amd64.deb
deleting and forgetting pool/universe/p/python-ckanext-spatial/python-ckanext-spatial_0.1~03-1_amd64.deb
Not deleting possibly left over files due to previous errors.
(To keep the files in the still existing index files from vanishing)
Use dumpunreferenced/deleteunreferenced to show/delete files without references.
1 files lost their last reference.
(dumpunreferenced lists such files, use deleteunreferenced to delete them.)
There have been errors!
(reverse-i-search)`delete': cat src/pip-^Clete-this-directory.txt 
ubuntu@ip-10-226-226-132:/var/packages/dgu-uat$ sudo reprepro deleteunreferenced  --help
Error: Too many arguments for command 'deleteunreferenced'!
Syntax: reprepro deleteunreferenced
There have been errors!
ubuntu@ip-10-226-226-132:/var/packages/dgu-uat$ sudo reprepro deleteunreferenced 
deleting and forgetting pool/universe/p/python-owslib/python-owslib_0.3.2beta~03-1_amd64.deb
ubuntu@ip-10-226-226-132:/var/packages/dgu-uat$ 

