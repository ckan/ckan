Common error messages
---------------------

Whether a developer runs CKAN using paster or going through CKAN test suite, there are a number of error messages seen that are the result of setup problems. As people experience them, please add them to the list here.

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

