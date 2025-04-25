====================
Doing a CKAN release
====================

This section documents the steps followed by the development team to do a
new CKAN release.

.. seealso::

   :doc:`/maintaining/releases`
     An overview of the different kinds of CKAN release and the supported
     versions

   :doc:`/maintaining/upgrading/index`
     The process for upgrading a CKAN site to a new version.



----------------
Process overview
----------------

CKAN releases are always done from tags created in release development branches.
A release development branch is the one that will be stabilized and eventually become the actual
released version. Release branches are always named ``dev-vM.m``, after the
:ref:`major and minor versions <releases>` they include, and they are always created from the ``master``
branch. When the release is actually published a patch version number is added
and the release is tagged in the form ``ckan-M.m.p``. All backports are cherry-picked to the
relevant ``dev-vM.m`` branch (:ref:`automatically <automated_backports>` or manually).


 ::

     +--+---------------------------------------------------+------------->  Master
        |                                                   |
        +-----+------------+------> dev-v2.10               +------->  dev-v2.11
              |            |
          ckan-2.10.0   ckan-2.10.1


Most releases require the same steps, with only new major or minor versions requiring the
previous step of creating and setting up the release development branch.

The involved steps can be split in these stages:

1. `Creating a release development branch`_ (Only for new major or minor releases)
2. `Setting up a new release`_
3. `Getting ready for the release`_
4. `Release day`_
5. `Post-release actions`_

It's important that there is one designated *Release Manager* that takes care of moving the process
forward and has a final say on things like what gets merged or when the release will actually
take place.

In the reference section below you can find an `Issue template`_ and an `Illustrative timeline`_
that can help release managers with planning.


------
Stages
------


Creating a release development branch
=====================================

.. note:: If you are starting a patch release you can skip this section


#. When the Tech Team decides to start a new release branch for a new minor release it's
   always useful to try to merge any outstanding pull requests that should be included.
   This makes it easier to include them as when the release branch
   starts diverging there can appear conflicts when cherry-picking.

#. Once it's time, create a new release branch::

      git checkout -b dev-v2.12

#. Update the version number in the ``master`` branch to increase the major or minor
   version as required (versions in the ``master`` branch always include ``a`` for alpha).
   The version is defined in the ``ckan/__init__.py`` file:

   .. code:: diff

	  diff --git a/ckan/__init__.py b/ckan/__init__.py
	  index 064e5245c..d65ae7cb7 100644
	  --- a/ckan/__init__.py
	  +++ b/ckan/__init__.py
	  @@ -1,6 +1,6 @@
	   # encoding: utf-8

	  -__version__ = "2.12.0a0"
	  +__version__ = "2.13.0a0"


#. Update the version number in the Solr schema file (``ckan/config/solr/schema.xml``) and
   review the value of ``SUPPORTED_SCHEMA_VERSIONS`` in ``ckan/lib/search/__init__.py``.
   Aside from adding the new version, you might need to drop previous one if there have been
   incompatible changes in the Solr schema.

   .. code:: diff

      diff --git a/ckan/config/solr/schema.xml b/ckan/config/solr/schema.xml
      index 2a86c4ca7..d8b1e46e8 100644
      --- a/ckan/config/solr/schema.xml
      +++ b/ckan/config/solr/schema.xml
      @@ -25,7 +25,7 @@
       schema. We used to use the `version` attribute for this but this is an internal
       attribute that should not be used so starting from CKAN 2.10 we use the `name`
       attribute with the form `ckan-X.Y` -->
      -<schema name="ckan-2.11" version="1.6">
      +<schema name="ckan-2.12" version="1.6">

       <types>
           <fieldType name="string" class="solr.StrField" sortMissingLast="true" omitNorms="true"/>
      diff --git a/ckan/lib/search/__init__.py b/ckan/lib/search/__init__.py
      index 0b8fb37b6..4040f0525 100644
      --- a/ckan/lib/search/__init__.py
      +++ b/ckan/lib/search/__init__.py
      @@ -57,7 +57,7 @@ def text_traceback() -> str:
           return res


      -SUPPORTED_SCHEMA_VERSIONS = ['2.8', '2.9', '2.10', '2.11']
      +SUPPORTED_SCHEMA_VERSIONS = ['2.8', '2.9', '2.10', '2.11', '2.12']

       DEFAULT_OPTIONS = {
           'limit': 20,


#. Create the documentation branch from the release branch. This branch should be named
   just with the minor version and nothing else (e.g. ``2.10``, ``2.11``, etc). We will use
   this branch to build the documentation in Read the Docs on all patch releases for
   this version. Add the new documentation branch on
   `Read the Docs <https://app.readthedocs.org/dashboard/ckan/version/create/>`_
   so it gets automatically build whenever we push to it.

#. Create a new resource for translations in Transifex:

   .. note:: It's recommended to create individual commits for each of these steps
      with the ``[i18n]`` prefix to make it easier to cherry-pick them later

   a. :ref:`setup-transifex` locally if not already done.

   b. Extract new strings from the CKAN source code into the ``ckan.pot``
      file. The pot file is a text file that contains the original,
      untranslated strings extracted from the CKAN source code.::

        python setup.py extract_messages

   c. Get the latest translations (of the previous CKAN release) from
      Transifex, in case any have changed since::

        tx pull --all --minimum-perc=5 --force

   d. Update the ``ckan.po`` files with the new strings from the ``ckan.pot`` file.
      Any new or updated strings from the CKAN source code will get into the po
      files, and any strings in the po files that no longer exist in the source
      code will be deleted (along with their translations)::

        python setup.py update_catalog --no-fuzzy-matching

   e. Edit ``.tx/config``, on line 4 to set the Transifex 'resource' to the new
      major or minor version. For instance v2.10.0, v2.10.1, v2.10.2, etc
      all share: ``[o:okfn:p:ckan:r:2-10]``.

   f. Create a new resource in the CKAN project on Transifex by pushing the new
      pot and po files. Because it reads the new version number in the
      ``.tx/config`` file, tx will create a new resource on Transifex
      rather than updating an existing resource ::

        tx push --source --translations --force

   g. On Transifex give the new resource a more friendly name. Go to the
      resource (e.g. https://www.transifex.com/okfn/ckan/2-11/) and access the settings
      from the triple dot icon "...". Keep the slug "2-11", but change
      the name to "CKAN 2.11".

   h. Update the ``ckan.mo`` files by compiling the po files::

        python setup.py compile_catalog

#. Create a new GitHub label for the backports: ``Backport dev-vX.Y``.


Setting up a new release
========================

* Update the version number in the release branch. All (unreleased) versions
  in the release branch include ``b`` for beta. Make sure to include 0 as the patch version number
  if this is a new release branch (e.g. ``2.12.0b0``, not ``2.12b0``).
  The version is defined in the ``ckan/__init__.py`` file:

   .. code:: diff

	  diff --git a/ckan/__init__.py b/ckan/__init__.py
	  index 064e5245c..d65ae7cb7 100644
	  --- a/ckan/__init__.py
	  +++ b/ckan/__init__.py
	  @@ -1,6 +1,6 @@
	   # encoding: utf-8

	  -__version__ = "2.11.0b0"
	  +__version__ = "2.11.1b0"

Getting ready for the release
=============================

Once the release branch is ready, there will be a period when the branch will be updated
with patches and tested (this will probably be longer for bigger releases).

.. note:: The following steps might need to be repeated at various times to ensure the branch is up to date.

* **Backports** to the release branch are done via the :ref:`automated backports action <automated_backports>`
  whenever possible. If there are conflicts, the relevant commits need to be
  manually cherry-picked.

* If there are **security patches** that need to be applied there needs to be a pull request
  targeting the release branch in the private advisory fork (in addition to the one
  targeting master). **Do not merge those** until just before the release, otherwise we will
  publicise vulnerabilities, but allow some time to fix potential issues after merging.
  Request CVE identifiers with enough time so they are ready on release day (they might
  take a couple of days to be allocated)

* Check if there are **requirements** that need to be upgraded because of security issues. Check the
  relevant branch on Snyk_ to see the vulnerable packages. We only upgrade those that don't introduce
  backwards incompatible changes. In general, upgrading a Python package is just a matter of
  bumping the version number in ``requirements.in`` and running::

      pip-compile -P <package_name> requirements.in

  Make sure to also update ``package.json`` for security related upgrades. Update the relevant packages
  in ``package.json`` and run the following to update other dependencies::

      npm audit fix

* Pull the latest **translations** from Transfiex and compile them (it's best to split it
  in two separate commits)::

      tx pull --all --minimum-perc=5 --force

      git commit ckan/i18n -m "[i18n] Pull translations from Transifex"

      python setup.py compile_catalog

      git commit ckan/i18n -m "[i18n] Compile translations"

* Compile the **CSS files**::

      ckan scss

* Prepare the **Docker images** in the `ckan-docker-base <https://github.com/ckan/ckan-docker-base>`_ repo.
  Create a pull request updating the relevant version numbers (in the ``VERSION.txt`` files)
  and check that all images build fine, fixing any issues otherwise.

* Prepare the **Deb packages** in the `ckan-packaging <https://github.com/ckan/ckan-packaging>`_ repo.
  Create a pull request updating the relevant version numbers (in the ``VERSIONS.json`` file)
  and check that all packages build fine, fixing any issues otherwise.

* Update the **Changelog**. This is likely tedious but really important. We use towncrier_
  to manage the changelog entries:

   * Unless trivial or part of a bigger change, all merged pull requests should have a
     corresponding fragment file inside the ``changes/`` folder. The name of every fragment
     should be ``{PR number}.{fragment type}``, where is one of *feature*, *migration*,
     *removal*, *bugfix* or *misc* depending on the changed introduced. Missing fragments can be created
     using ``towncrier create --edit {PR number}.{fragment type}``.
   * When all fragments are ready, make a draft build::

        towncrier build --draft
   * It's very likely that you will need to tweak the changelog entries to fix typos or
     improve readability, and the migration or deprecation sections will need to be
     expanded. Remember that users with no prior context need to get a good understanding
     of what the changes are.
   * Once updated, remove all changelog fragments from the ``changes`` folder. Do this in a
     separate commit so it can be later cherry-picked to master.


Release day
===========

* If there are pending security advisories (they should have been tested and have a CVE
  number by now):

   * Merge the patches into the releases branches and master
   * Publish the advisories
   * Update the changelog to include an entry for the patch (linking to the GitHub advisory)

* Update the version number in ``ckan/__init__.py`` to remove the ``b0`` part.

   .. code:: diff

	  diff --git a/ckan/__init__.py b/ckan/__init__.py
	  index 064e5245c..d65ae7cb7 100644
	  --- a/ckan/__init__.py
	  +++ b/ckan/__init__.py
	  @@ -1,6 +1,6 @@
	   # encoding: utf-8

	  -__version__ = "2.11.1b0"
	  +__version__ = "2.11.1"

* Create a tag with the format ``ckan-{Major}.{Minor}.{Patch}``

* Push the tag. This will trigger two automated actions:

  1. :ref:`Create a GitHub Release <create_github_release>`:
     Check that the release was created fine (the changelog link won't work yet)
  2. :ref:`Publish the CKAN package in PyPI <publish_pypi>`:
     Check that the package was published and it is the latest available at https://pypi.org/project/ckan/

* Merge the release branch into the documentation branch (e.g. ``dev-v2.11`` to ``2.11``). This will
  trigger a build in Read the Docs. Check that the build worked and that the correct version is
  showing up in the relevant docs version.

* Update the `Docker images <https://github.com/ckan/ckan-docker-base?tab=readme-ov-file#release>`_:

  1. Merge the pull request and create a tag (``vYYYYMMDD``) and a new release. Creating the release
     will trigger a workflow to build and push the images to Docker Hub.
  2. Check that the workflows worked and tags were updated on `Docker Hub`_.

* Generate new `Deb packages <https://github.com/ckan/ckan-packaging/?tab=readme-ov-file#release-process>`_:

  1. Merge the pull request and create a tag (``vYYYYMMDD``). Pushing the tag will trigger the publish workflow,
     which will:

      * Upload the build packages to the Amazon S3 bucket powering https://packaging.ckan.org
      * Create a new `GitHub release <https://github.com/ckan/ckan-packaging/releases>`_,
        which also includes the packages.

  2. Check both to make sure the packages were built as expected.

* Announce the release. In most cases you can reuse previous messages or get help from the Communications team. All
  items should clearly include the new version numbers and a link to the changelog (or link to a place that has those):

  1. Send a message to Gitter
  2. Send an email to the `ckan-announce mailing list <https://groups.google.com/a/ckan.org/g/ckan-announce>`_,
  3. Ask for a new blog post on ckan.org/blog. You can help the comms team with a draft of the main changes.
  4. Ask the comms team to post it to the CKAN social channels.

Post-release actions
====================

Some maintenance things that is better to do straight after the release is out so they don't get forgotten:

* Update the version number on the release branch, increasing the patch version and adding the ``b0`` suffix again.
* Cherry pick the ``[i18n]`` commits to master (it's best to cherry pick the ones involving ``.pot`` and ``.po`` files
  and update the ``.mo`` files in master with ``python setup.py compile_catalog`` to avoid conflicts).
* Update the CHANGELOG in master to include all new versions released.
* Cherry-pick the commit that deletes the ``changes`` fragments to master so they don't get picked up in the next release.


---------
Reference
---------

.. _setup-transifex:

Set up Transifex
================

We use Transifex_ to crowd-source translations in CKAN.
To manage translations you will need the Transifex CLI.

#. Install the `Transifex CLI <https://developers.transifex.com/docs/cli#installation>`_.

#. Create a ``~/.transifexrc`` file if necessary with your login details
   (To generate the token, go to the Transifex `user settings <https://www.transifex.com/user/settings/api/>`_ page)::

      [https://www.transifex.com]
      api_hostname  = https://api.transifex.com
      hostname      = https://www.transifex.com
      username      = api
      password      = ADD_YOUR_TOKEN_HERE
      rest_hostname = https://rest.api.transifex.com
      token         = ADD_YOUR_TOKEN_HERE

#. Check you got the right permissions, you should see the current
   Transifex resource and all the available languages when running
   this in the CKAN folder::

      tx status


#. A week before the translations will be closed send a reminder email.

#. Once the translations are closed, sync them from Transifex.

   Pull the updated strings from Transifex::

        tx pull --all --minimum-perc=5 --force

   Check and compile them as before::

        ckan -c |ckan.ini| translation check-po ckan/i18n/*/LC_MESSAGES/ckan.po
        python setup.py compile_catalog

    The compilation shows the translation percentage. Compare this with the new
    languages directories added to ckan/i18n::

        git status

   ``git add`` any new ones. (If all is well, you won't see any that are under
   5% translated.)

   Now push::

        git commit -am "Update translations from Transifex"
        git push


Issue template
==============

It's a good idea to create a tracking issue in GitHub at the beginning
of the release process. Here's a template that summarizes the different
stages involved::


   This is an issue to track progress on the patch releases (2.X.Y and 2.Z.A)

   [Full docs](https://docs.ckan.org/en/latest/contributing/release-process.html)

   ### Create a new release branch (remove for patch releases)

   * [ ] Create release branch
   * [ ] Update version in master
   * [ ] Update Solr schema version
   * [ ] Create documentation branch
   * [ ] Set up translations on Transifex
   * [ ] Create GitHub label

   ### Setting up

   * [ ] Update version in release branch

   ### Getting ready

   * [ ] [Backports](https://github.com/ckan/ckan/labels/Backport%20dev-v2.X)
   * [ ] Security requirements upgrade
   * [ ] Security issues
   * [ ] Translations
   * [ ] Rebuild Frontend
   * [ ] Prepare Docker images
   * [ ] Prepare Deb packages
   * [ ] Prepare Changelog

   ### Release day
   * [ ] Change version and tag
   * [ ] Publish to PyPI (🤖)
   * [ ] Create GitHub release (🤖)
   * [ ] Update docs on Read the Docs
   * [ ] Build Docker images
   * [ ] Build and upload deb packages
   * [ ] Announce

   ### Post-release actions
   * [ ] Cherry-pick i18n changes to master
   * [ ] Cherry-pick Changelog changes to master
   * [ ] Update version on release branch


Illustrative timeline
=====================

.. important:: The timeline below is provided as a guidance only. The actual timings may vary
   depending on the size of the changes included in the release, availability of the
   release manager or other external factors. Unless there are urgent security patches that
   need to go out, it is best to err in the side of caution and make sure that what gets
   released is stable and well documented. It is fine to push the release back a week (but the
   change should be announced)

Major or minor release
----------------------

.. list-table::
   :widths: 25 50
   :header-rows: 1

   * - Days to release
     - Action
   * - 50
     - Merge all major pull requests and upgrade requirements
   * - 40
     - Start release process (release branch)
   * - 35
     - Prepare beta Docker images and Deb packages
   * - 30
     - Call for help testing the release and translations
   * - .
     - Follow with items in the "Patch release" table


Patch release
-------------

.. list-table::
   :widths: 25 50
   :header-rows: 1

   * - Days to release
     - Action
   * - 20
     - Start release process
   * - 15
     - Prepare and test Docker images and Deb packages
   * - 10
     - Most backports should be in the release branch
   * - 7
     - Announce release in the ckan-announce mailing list
   * - 5
     - Request CVE numbers if necessary, all security patches should be ready
   * - 3
     - Docker images and Deb packages should build fine
   * - 2
     - Finalize Changelog, frontend files and translations
   * - 0
     - Release day: all actions in "Release day" and "Post-release actions"


.. _Transifex: https://www.transifex.com/projects/p/ckan
.. _Snyk: https://app.snyk.io
.. _towncrier: https://towncrier.readthedocs.io/en/stable/
.. _labels: https://github.com/ckan/ckan/labels
.. _`Docker Hub`: https://hub.docker.com/r/ckan/ckan-base/tags
