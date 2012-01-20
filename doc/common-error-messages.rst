Common error messages
---------------------

Whether a developer runs CKAN using paster or going through CKAN test suite, there are a number of error messages seen that are the result of setup problems. As people experience them, please add them to the list here.

These instructions assume you have the python virtual environment enabled (``. pyenv/bin/activate``) and the current directory is the top of the ckan source, which is probably: ``../pyenv/src/ckan/``.

``nose.config.ConfigError: Error reading config file 'setup.cfg': no such option 'with-pylons'``
================================================================================================

   This error can result when you run nosetests for two reasons:

   1. Pylons nose plugin failed to run. If this is the case, then within a couple of lines of running `nosetests` you'll see this warning: `Unable to load plugin pylons` followed by an error message. Fix the error here first.

   2. The Python module 'Pylons' is not installed into you Python environment. Confirm this with::

        python -c "import pylons"

``OperationalError: (OperationalError) no such function: plainto_tsquery ...``
==============================================================================

   This error usually results from running a test which involves search functionality, which requires using a PostgreSQL database, but another (such as SQLite) is configured. The particular test is either missing a `@search_related` decorator or there is a mixup with the test configuration files leading to the wrong database being used.

``ImportError: No module named worker``
=======================================

   The python entry point for the worker has not been generated. This occurs during the 'pip install' of the CKAN source, and needs to be done again if switching from older code that didn't have it. To recitify it::

        python setup.py egg_info

``ImportError: cannot import name get_backend``
===============================================

   This can be caused by an out of date pyc file. Delete all your pyc files and start again::

        find . -name "*.pyc" | xargs rm

``ImportError: cannot import name UnicodeMultiDict``
====================================================

   This is caused by using a version of WebOb that is too new (it has deprecated UnicodeMultiDict). Check the version like this (ensure you have activated your python environment first)::

         pip freeze | grep -i webob

   Now install the version specified in requires/lucid_present.txt. e.g.::

         pip install webob==1.0.8

``nosetests: error: no such option: --ckan``
============================================

   Nose is either unable to find ckan/ckan_nose_plugin.py in the python environment it is running in, or there is an error loading it. If there is an error, this will surface it::

         nosetests --version

   There are a few things to try to remedy this:

   Commonly this is because the nosetests isn't running in the python environment. You need to have nose actually installed in the python environment. To see which you are running, do this::

         which nosetests

   If you have activated the environment and this still reports ``/usr/bin/nosetests`` then you need to::

         pip install --ignore-installed nose

   If ``nose --version`` still fails, ensure that ckan is installed in your environment::

         cd pyenv/src/ckan
         python setup.py develop

   One final check - the version of nose should be at least 1.0. Check with::

         pip freeze | grep -i nose

``AttributeError: 'unicode' object has no attribute 'items'`` (Cookie.py)
=========================================================================

This can be caused by using repoze.who version 1.0.18 when 1.0.19 is required. Check what you have with::

         pip freeze | grep -i repoze.who=

See what version you need with::

         grep -f requires/*.txt |grep repoze\.who=

Then install the version you need (having activated the environment)::

         pip install repoze.who==1.0.19

``AttributeError: 'module' object has no attribute 'BigInteger'``
=================================================================

The sqlalchemy module version is too old.

``ConfigParser.NoSectionError: No section: 'formatters'``
=========================================================

This suggests that the config file specified with the paster ``--config`` parameter (e.g. ``myconfig.ini``) is incorrectly formatted. This may be true, but this error is also printed if you specify an incorrect filename for the config file!

``ImportError: No module named exceptions``
===========================================

This occurs when trying to ``import migrate.exceptions`` and is due to the version of sqlalchemy-migrate being used is too old - check the requires files for the version needed.

``ckan.plugins.core.PluginNotFoundException: stats``
====================================================

After the CKAN 1.5.1 release, the Stats extension was merged into the core CKAN code, and the ckanext namespace needs registering before the tests will run::

         cd pyenv/src/ckan
         python setup.py develop

Otherwise, this problem may be to enabling an extension which is not installed. See: :doc:`extensions`_.

``AssertionError: There is no script for 46 version``
=====================================================

This sort of message may be seen if you swap between different branches of CKAN. The .pyc file for database migration 46 exists, but the .py file no longer exists by swapping to an earlier branch. The solution is to delete all pyc files (which is harmless)::

    find . -name "*.pyc" |xargs rm

``AssertionError: Unexpected files/directories in pyenv/src/ckan``
==================================================================

This occurs when installing CKAN source to a virtual environment when using an old version of pip. (e.g. pip 0.3.1 which comes with Ubuntu). Instead you should use pip 1.0.2 or higher, which will be found in your virtual environment: ``pyenv/bin/pip``

``sqlalchemy.exc.IntegrityError: (IntegrityError) could not create unique index "user_name_key``
================================================================================================

This occurs when upgrading to CKAN 1.5.1 with a database with duplicate user names. See :ref:`upgrading`

