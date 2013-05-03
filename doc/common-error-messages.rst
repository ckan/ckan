=====================
Common error messages
=====================

There are a number of errors that might happen when a someone tries to install or upgrade CKAN. As people experience them, please add them to the list here.

These instructions assume you have the python virtual environment enabled (``. pyenv/bin/activate``) and the current directory is the top of the ckan source, which is probably: ``../pyenv/src/ckan/``.


ImportError
===========

``ImportError: No module named worker``
   The python entry point for the worker has not been generated. This occurs during the 'pip install' of the CKAN source, and needs to be done again if switching from older code that didn't have it. To recitify it::

        python setup.py egg_info

``ImportError: cannot import name get_backend``
   This can be caused by an out of date pyc file. Delete all your pyc files and start again::

        find . -name "*.pyc" | xargs rm

``ImportError: No module named genshi.template``
  This is seen when running a paster command. The problem is paster is not recognising the python virtual environment where genshi (and other CKAN libraries) are installed. To resolve this, supply the path to the copy of paster in the virtual environment. e.g.::

    pyenv/bin/paster ...


NoSectionError
==============

``ConfigParser.NoSectionError: No section: 'formatters'``
  This suggests that the config file specified with the paster ``--config`` parameter (e.g. ``myconfig.ini``) is incorrectly formatted. This may be true, but this error is also printed if you specify an incorrect filename for the config file!


PluginNotFoundException
=======================

``ckan.plugins.core.PluginNotFoundException: stats``
  After the CKAN 1.5.1 release, the Stats and Storage extensions were merged into the core CKAN code, and the ckanext namespace needs registering before the tests will run::

           cd pyenv/src/ckan
           python setup.py develop

  Otherwise, this problem may be because of specifying an extension in the CKAN config but having not installed it. See: :doc:`extensions`.


AssertionError
==============

``AssertionError: There is no script for 46 version``
  This sort of message may be seen if you swap between different branches of CKAN. The .pyc file for database migration 46 exists, but the .py file no longer exists by swapping to an earlier branch. The solution is to delete all pyc files (which is harmless)::

      find . -name "*.pyc" |xargs rm

``AssertionError: Unexpected files/directories in pyenv/src/ckan``
  This occurs when installing CKAN source to a virtual environment when using an old version of pip. (e.g. pip 0.3.1 which comes with Ubuntu). Instead you should use pip 1.0.2 or higher, which will be found in your virtual environment: ``pyenv/bin/pip``


IntegrityError
==============

``sqlalchemy.exc.IntegrityError: (IntegrityError) could not create unique index "user_name_key``
  This occurs when upgrading to CKAN 1.5.1 with a database with duplicate user names. See :ref:`upgrading`


ERROR
=====

``ERROR:  must be member of role "okfn"`` & ``WARNING:  no privileges could be revoked for "public"``
  These are seen when loading a CKAN database from another machine. It is the result of the database tables being owned by a user that doesn't exist on the new machine. The owner of the table is not important, so this error is harmless and can be ignored.


IOError
=======

``IOError: [Errno 13] Permission denied: '/var/log/ckan/colorado/colorado.log'``
  This is usually seen when you run the paster command with one user, and CKAN is deployed on Apache (for example) which runs as another user. The usual remedy is to run the paster command as user ``www-data``. i.e..::

    sudo -u www-data paster ...


Type does not exist
===================

``type "geometry" does not exist`` (also ``function public.multipolygonfromtext(text) does not exist`` ``permission denied for language c``)
  This may occur when you are using psql or ``paster db load``. It means that the database dump was taken from a Postgres database that was spatially enabled (PostGIS installed) and you are loading it into one that is not.

  To make your Postgres cluster spatially enabled, see the instructions here: https://github.com/okfn/ckanext-spatial/blob/master/README.rst
