=============================
Upgrading CKAN's dependencies
=============================

The Python modules that CKAN depends on are pinned to specific versions, so we
can guarantee that whenever anyone installs CKAN, they'll always get the same
versions of the Python modules in their virtual environment.

Our dependencies are defined in three files:

requirements.in
  This file is only used to create a new version of the ``requirements.txt``
  file when upgrading the dependencies.
  Contains our direct dependencies only (not dependencies of dependencies)
  with loosely defined versions. For example, ``python-dateutil>=1.5.0,<2.0.0``.

requirements.txt
  This is the file that people actually use to install CKAN's dependencies into
  their virtualenvs. It contains every dependency, including dependencies of
  dependencies, each pinned to a specific version.
  For example, ``simplejson==3.3.1``.

dev-requirements.txt
  Contains those dependencies only needed by developers, not needed for
  production sites. These are pinned to a specific version. For example,
  ``factory-boy==2.1.1``.

We haven't created a ``dev-requirements.in`` file because we have too few dev
dependencies, we don't update them often, and none of them have a known
incompatible version.

----------------
Steps to upgrade
----------------

These steps will upgrade all of CKAN's dependencies to the latest versions that
work with CKAN:

#. Create a new virtualenv: ``virtualenv --no-site-packages upgrading``

#. Install the requirements with unpinned versions: ``pip install -r
   requirements.in``

#. Save the new dependencies versions: ``pip freeze > requirements.txt``. We
   have to do this before installing the other dependencies so we get only what
   was in ``requirements.in``

#. Install CKAN: ``python setup.py develop``

#. Install the development dependencies: ``pip install -r
   dev-requirements.txt``

#. Run the tests to make sure everything still works (see :doc:`test`).

   - If not, try to fix the problem. If it's too complicated, pinpoint which
     dependency's version broke our tests, find an older version that still
     works, and add it to ``requirements.in`` (i.e., if ``python-dateutil``
     2.0.0 broke CKAN, you'd add ``python-dateutil>=1.5.0,<2.0.0``). Go back to
     step 1.

#. Navigate a bit on CKAN to make sure the tests didn't miss anything. Review
   the dependencies changes and their changelogs. If everything seems fine, go
   ahead and make a pull request (see :doc:`/contributing/pull-requests`).
