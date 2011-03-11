Packaging CKAN as Debian Files
++++++++++++++++++++++++++++++

Dependencies
============

In order to pacakge CKAN and dependencies as Debian files you'll need the
following tools:

::

    sudo apt-get install -y python wget dh-make devscripts build-essential fakeroot cdbs

And depending on the source repositories of the things you are packaging you'll
probably need:

::

    sudo apt-get install -y mercurial git-core subversion


Preparation
===========

In order to build packages you'll need a directory with all of the source code
for the various packages you want to pacakge checked out in a directory. You'll
also need a copy of BuildKit installed.

The easiest way to achieve this is to set up a virtual environment with
BuildKit installed and use ``pip`` to install the dependencies in it for you.

::

    wget http://pylonsbook.com/virtualenv.py 
    python virtualenv.py missing
    cd missing
    bin/easy_install pip
    bin/pip install BuildKit

The idea is that all the dependencies you want to package are in a
``lucid_missing.txt`` file as editable requirements with exact revisions
specified. For example, if we want to package ApacheMiddleware we would have this line:

::

    -e hg+https://hg.3aims.com/public/ApacheMiddleware@c5ab5c3169a5#egg=ApacheMiddleware

Once your requirements are in place, install them like this:

::

    bin/pip install -r lucid_missing.txt

.. tip ::

   You can't just do this because pip ignores the ``-e`` for code that is
   installed from a package and fails to put it in ``src``:

   ::

       # Won't work
       -e ApacheMiddleware

   You can put the source directory manually in your virtual environment's
   ``src`` directory though if you need to though.

Automatic Packaging
===================

The BuildKit script will build and place Debian packages in your ``missing``
directory. Make sure there is nothing in there that shouldn't be overwritten by
this script.

To package everything automatically, run it like this:

::

    cd missing
    bin/python -m buildkit.update_all .

For each pacakge you'll be loaded into ``vim`` to edit the changelog. Save and
quit when you are done. Names, version numbers and dependencies are
automatically generated.

You should find all your packages nicely created now.

Manual Packaging
================

If you want more control over version numbers and dependencies or you just want
to package one thing you can do so like this:

::

    python -m buildkit.deb /path/to/virtualenv ckan-deps 1.3 http://ckan.org python-dep-1 python-dep-2 ... etc

Version Numbers
===============

To release an upgrade of a package it must have a higher version number. There
is a chance you may want to release a more recent version of a package despite
the fact the underlying version number hasn't changed. For this reason, we
always add a ``~`` character followed by a two digit number to the end of the
actual version number as specified in ``setup.py`` for the package. 

For example, the version number for CKAN may be ``1.4.0a~01``, producing a
package named ``python-ckan_1.4.0a~01_amd64.deb``.

Relase Process
==============

For any instance of CKAN, the following release process occurs:

* Import from each 

::

    sudo reprepro includedeb lucid /home/ubuntu/*.deb
    sudo reprepro remove lucid python2.4-pgsql

Here's what a directory looks like:

::

    $ find /var/packages/debian/pool/universe/ | grep "\.deb"
    $ ls /home/ubuntu/release/2011030701/
    python-apachemiddleware_0.1.0-1_amd64.deb  python-ckanext-dgu_1.3-1_amd64.deb    python-pyutilib.component.core_4.1-1_amd64.deb
    python-ckan_1.4a4-1_amd64.deb              python-formalchemy_1.3.6-1_amd64.deb  python-solrpy_0.9.3-1_amd64.deb
    python-ckanclient_0.6-1_amd64.deb          python-licenses_0.6-1_amd64.deb       python-vdm_0.9-1_amd64.deb
    python-ckan-deps_1.3.4-1_amd64.deb         python-markupsafe_0.9.2-1_amd64.deb
    
Setting up the Repositories
===========================

Convert a Python package installed into a virtualenv into a Debian package automatically

Usage:

::

    python -m buildkit.deb /home/okfn/pyenv ckan 1.3 http://ckan.org python-routes python-vdm python-pylons python-genshi python-sqlalchemy python-repoze.who python-repoze.who-plugins python-pyutilib.component.core python-migrate python-formalchemy python-sphinx

For this to work you need a modern Ubuntu with these packages installed:

::

    sudo apt-get install -y python wget dh-make devscripts build-essential fakeroot cdbs

There's a dependency on postfix. Choose internet site and the default hostname unless you know better.

Once you have packages you'll want to put them in a repo. You can do that as described here:

http://joseph.ruscio.org/blog/2010/08/19/setting-up-an-apt-repository/

Then add them like this:

::

    cd /var/packages/debian/
    sudo reprepro includedeb lucid ~/*.deb

Todo

* Make this convert all files in a virtualenv recursively
* Automatically extract the dependencies using buildkit
* Save the changelogs somewhere and put them back once they are updated

Testing in a VM
===============

If you aren't running Lucid, you may need to test in a VM. You can create one like this:

::

    sudo vmbuilder kvm ubuntu --suite lucid --flavour virtual --arch amd64  -o --mirror http://localhost:9999/ubuntu

This assumes you already have an apt mirror set up on port 9999 and that you
can build bridged networks yourself. I'll document both in due course, but for
now, just ask.


Next Steps
==========

* Write a ``ckan`` command.
* Add the ``debian`` directories
* Agree a naming convention and paths
* Delayed updates

Install Guide with 

dpkg-deb -b . ..

