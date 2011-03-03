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


