====================
Doing a CKAN release
====================

This section documents the steps followed by the development team to do a
new CKAN release.

.. seealso::

   :doc:`/maintaining/upgrading/index`
     An overview of the different kinds of CKAN release, and the process for
     upgrading a CKAN site to a new version.

----------------
Process overview
----------------

The process of a new release starts with the creation of a new release branch.
A release branch is the one that will be stabilized and eventually become the actual
released version. Release branches are always named ``release-vM.m.p``, after the
:ref:`major, minor and patch versions <releases>` they include. Major and minor versions are
always branched from master. Patch releases are always branched from the most recent tip
of the previous patch release branch.

 ::

     +--+---------------------------------------+------------->  Master
        |                                       |
        +----------------->  release-v2.4.0     +---------->  release-v2.5.0
                          |
                          +--------->  release-v2.4.1
                                    |
                                    +------>  release-v2.4.2

Once a release branch has been created there is generally a three-four week period until
the actual release. During this period the branch is tested and fixes cherry-picked. The whole
process is described in the following sections.


.. _beta-release:

--------------------
Doing a beta release
--------------------

Beta releases are branched off a certain point in master and will eventually
become stable releases.

#. Create a new release branch::

        git checkout -b release-v2.5.0

   Update ``ckan/__init__.py`` to change the version number to the new version
   with a *b* after it, e.g. *2.5.0b*.
   Commit the change and push the new branch to GitHub::

        git commit -am "Update version number"
        git push origin release-v2.5.0

   You will probably need to update the same file on master to increase the
   version number, in this case ending with an *a* (for alpha).

#. Once the release branch is created, send an annoucement email with an
   initial call for translations, warning that at this point strings can still
   change, but hopefully not too much.

#. During the beta process, all changes to the release branch must be
   cherry-picked from master (or merged from special branches based on the
   release branch if the original branch was not compatible).

#. As in the master branch, if some commits involving CSS changes are
   cherry-picked from master, the less compiling command needs to be run on
   the release branch. This will update the ``main.css`` file::

        ./bin/less --production
        git commit -am "Rebuild CSS"
        git push

   There will be a final front-end build before the actual release.

#. The beta staging site (http://beta.ckan.org, currently on s084) must be
   set to track the latest beta release branch to allow user testing. This site
   is updated nightly.

#. Once a week create a deb package with the latest release branch, using ``betaX``
   iterations. Deb packages are built using Ansible_ scripts located at the
   following repo:

    https://github.com/ckan/ckan-packaging

   The repository contains furhter instructions on how to run the scripts, but essentially
   you will need access to the packaging server, and then run something like::

     ansible-playbook package.yml -u your_user -s

   You will be prompted for the CKAN version to package (eg ``2.4.0``), the iteration (eg ``beta1``)
   and whether to package the DataPusher (always do it on release packages).

   Packages are created by default on the `/build` folder of the publicly accessible directory of
   the packaging server.

#. Once the translation freeze is in place (ie no changes to the translatable
   strings are allowed), strings need to be extracted and uploaded to
   Transifex_:

   a. Install the Babel and Transifex libraries if necessary::

        pip install --upgrade Babel
        pip install transifex-client

   b. Create a ``~/.transifexrc`` file if necessary with your login details
      (``token`` should be left blank)::

        [https://www.transifex.com]
        hostname = https://www.transifex.com
        username = <username>
        password = <password>
        token =

   c. Extract new strings from the CKAN source code into the ``ckan.pot``
      file. The pot file is a text file that contains the original,
      untranslated strings extracted from the CKAN source code.::

        python setup.py extract_messages

      The po files are text files, one for each language CKAN is translated to,
      that contain the translated strings next to the originals. Translators edit
      the po files (on Transifex) to update the translations. We never edit the
      po files locally.

   d. Run our script that checks for mistakes in the ckan.po files::

        pip install polib
        paster check-po-files ckan/i18n/*/LC_MESSAGES/ckan.po

      If the script finds any mistakes correct them on Transifex and then run the
      tx pull command again, don't edit the files directly. Repeat until the
      script finds no mistakes.

   e. Edit ``.tx/config``, on line 4 to set the Transifex 'resource' to the new
      major release name (if different), using dashes instead of dots.
      For instance v2.4.0, v2.4.1 and v2.4.2 all share: ``[ckan.2-4]``.

   f. Update the ``ckan.po`` files with the new strings from the ``ckan.pot`` file::

        python setup.py update_catalog --no-fuzzy-matching

      Any new or updated strings from the CKAN source code will get into the po
      files, and any strings in the po files that no longer exist in the source
      code will be deleted (along with their translations).

      We use the ``--no-fuzzy-matching`` option because fuzzy matching often
      causes problems with Babel and Transifex.

   g. Create a new resource in the CKAN project on Transifex by pushing the new
      pot and po files::

        tx push --source --translations --force

      Because it reads the new version number in the ``.tx/config`` file, tx will
      create a new resource on Transifex rather than updating an existing
      resource (updating an existing resource, especially with the ``--force``
      option, can result in translations being deleted from Transifex).

   h. Update the ``ckan.mo`` files by compiling the po files::

        python setup.py compile_catalog

      The mo files are the files that CKAN actually reads when displaying
      strings to the user.

   i. Commit all the above changes to git and push them to GitHub::

        git commit -am "Update strings files before CKAN X.Y call for translations"
        git push

   j. Announce that strings for the new release are ready for translators. Send
      an email to the mailing lists, tweet or post it on the blog. Make sure to
      post a link to the correct Transifex resource (like
      `this one <https://www.transifex.com/projects/p/ckan/resource/2-0/>`_)
      and tell users that they can register on Transifex to contribute.

   k. A week before the translations will be closed send a reminder email.

   l. Once the translations are closed, pull the updated strings from Transifex,
      check them, compile and push as described in the previous steps::

        tx pull --all --force
        paster check-po-files ckan/i18n/*/LC_MESSAGES/ckan.po
        python setup.py compile_catalog
        git commit -am " Update translations from Transifex"
        git push

#. A week before the actual release, send an email to the
   `ckan-announce mailing list <http://lists.okfn.org/mailman/listinfo/ckan-announce>`_,
   so CKAN instance maintainers can be aware of the upcoming releases. List any patch releases
   that will be also available. Here's an `example <https://lists.okfn.org/pipermail/ckan-announce/2015-July/000013.html>`_ email.


----------------------
Doing a proper release
----------------------

Once the release branch has been thoroughly tested and is stable we can do
a release.

#. Run the most thorough tests::

        nosetests ckan/tests --ckan --ckan-migration --with-pylons=test-core.ini

#. Do a final build of the front-end and commit the changes::

        paster front-end-build
        git commit -am "Rebuild front-end"

#. Update the CHANGELOG.txt with the new version changes:

   * Add the release date next to the version number
   * Add the following notices at the top of the release, reflecting whether
     updates in requirements, database or Solr schema are required or not::

        Note: This version requires a requirements upgrade on source installations
        Note: This version requires a database upgrade
        Note: This version does not require a Solr schema upgrade

   * Check the issue numbers on the commit messages for information about
     the changes. The following gist has a script that uses the GitHub API to
     aid in getting the merged issues between releases:

        https://gist.github.com/amercader/4ec55774b9a625e815bf

     Other helpful commands are::

        git branch -a --merged > merged-current.txt
        git branch -a --merged ckan-1.8.1 > merged-previous.txt
        diff merged-previous.txt merged-current.txt

        git log --no-merges release-v1.8.1..release-v2.0
        git shortlog --no-merges release-v1.8.1..release-v2.0

#. Check that the docs compile correctly::

        rm build/sphinx -rf
        python setup.py build_sphinx

#. Remove the beta letter in the version number in ``ckan/__init__.py``
   (eg 1.1b -> 1.1) and commit the change::

        git commit -am "Update version number for release X.Y"

#. Tag the repository with the version number, and make sure to push it to
   GitHub afterwards::

        git tag -a -m '[release]: Release tag' ckan-X.Y
        git push --tags

#. Create the final deb package and move it to the root of the
   `publicly accessible folder <http://packaging.ckan.org/>`_ of
   the packaging server from the `/build` folder.

   Make sure to rename it so it follows the deb packages name convention::

    python-ckan_Major.minor_amd64.deb

   Note that we drop any patch version or iteration from the package name.

#. Upload the release to PyPI::

        python setup.py sdist upload

   You will need a PyPI account with admin permissions on the ckan package,
   and your credentials should be defined on a ``~/.pypirc`` file, as described
   `here <http://docs.python.org/distutils/packageindex.html#pypirc>`_
   If you make a mistake, you can always remove the release file on PyPI and
   re-upload it.

#. Enable the new version of the docs on Read the Docs (you will need an admin
   account):

   a. Go to the `Read The Docs`_ versions page
      and enable the relevant release (make sure to use the tag, ie ckan-X.Y,
      not the branch, ie release-vX.Y).

   b. If it is the latest stable release, set it to be the Default Version and
      check it is displayed on http://docs.ckan.org.

#. Write a `CKAN Blog post <http://ckan.org/wp-admin>`_ and send an email to
   the mailing list announcing the release, including the relevant bit of
   changelog.

#. Cherry-pick the i18n changes from the release branch onto master.

   We don't generally merge or cherry-pick release branches into master, but
   the files in ckan/i18n are an exception. These files are only ever changed
   on release branches following the :ref:`beta-release` instructions above,
   and after a release has been finalized the changes need to be cherry-picked
   onto master.

   To find out what i18n commits there are on the release-v* branch that are
   not on master, do::

     git log master..release-v* ckan/i18n

   Then ``checkout`` the master branch, do a ``git status`` and a ``git pull``
   to make sure you have the latest commits on master and no local changes.
   Then use ``git cherry-pick`` when on the master branch to cherry-pick these
   commits onto master. You should not get any merge conflicts. Run the
   ``check-po-files`` command again just to be safe, it should not report any
   problems. Run CKAN's tests, again just to be safe.  Then do ``git push
   origin master``.


.. _Transifex: https://www.transifex.com/projects/p/ckan
.. _`Read The Docs`: http://readthedocs.org/dashboard/ckan/versions/
.. _Ansible: http://ansible.com/
