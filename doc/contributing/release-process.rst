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

.. versionchanged:: 2.6

The process of a new release starts with the creation of a new release development branch.
A release development branch is the one that will be stabilized and eventually become the actual
released version. Release branches are always named ``dev-vM.m``, after the
:ref:`major and minor versions <releases>` they include. Major and minor versions are
always branched from master. When the release is actually published a patch version number is added
and the release is tagged in the form ``ckan-M.m.p``. All backports are cherry-picked on the ``dev-vM.m`` branch.


 ::

     +--+-----------------------------------------+------------->  Master
        |                                         |
        +-----+-------------+------>  dev-v2.6    +------->  dev-v2.7
              |             |
          ckan-2.6.0    ckan-2.6.1       


Additionally, the ``release-vM.m-latest`` branches always contain the latest
published release for that version (eg ``2.6.1`` on the example above).


.. note::

    Prior to CKAN 2.6, release branches were named ``release-vM.m.p``, after the
    :ref:`major, minor and patch versions <releases>` they included, and patch releases 
    were always branched from the most recent tip of the previous patch release branch
    (tags were created with the same convention).
    Starting from CKAN 2.6, the convention is the one described above.

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

----------------------
Doing the beta release
----------------------

Beta releases are branched off a certain point in master and will eventually
become stable releases.

Turn this file into a github issue with a checklist using this command::

   echo 'Full instructions here: https://github.com/ckan/ckan/blob/master/doc/contributing/release-process.rst'; egrep '^(\#\.|Doing|Leading|Preparing)' doc/contributing/release-process.rst | sed 's/^\([^#]\)/\n## \1/g' | sed 's/\#\./* [ ]/g' |sed 's/::/./g'

#. Create a new release branch::

        git checkout -b dev-v2.7

   Update ``ckan/__init__.py`` to change the version number to the new version
   with a *b* after it, e.g. *2.7.0b* (Make sure to include 0 as the patch version number).
   Commit the change and push the new branch to GitHub::

        git commit -am "Update version number"
        git push origin dev-v2.7

   You will probably need to update the same file on master to increase the
   version number, in this case ending with an *a* (for alpha).

   During the beta process, all changes to the release branch must be
   cherry-picked from master (or merged from special branches based on the
   release branch if the original branch was not compatible).

   As in the master branch, if some commits involving CSS changes are
   cherry-picked from master, the less compiling command needs to be run on
   the release branch. This will update the ``main.css`` file::

        ./bin/less --production
        git commit -am "Rebuild CSS"
        git push

   There will be a final front-end build before the actual release.

#. Update beta.ckan.org to run new branch.

   The beta staging site
   (http://beta.ckan.org, currently on s084) must be set to track the latest beta
   release branch to allow user testing. This site is automatically updated nightly.

   Check the message on the front page reflects the current version. Edit it as
   a syadmin here: http://beta.ckan.org/ckan-admin/config

#. Announce the branch and ask for help testing on beta.ckan.org on ckan-dev.

#. Create the documentation branch from the release branch. This branch should be named
   just with the minor version and nothing else (eg ``2.7``, ``2.8``, etc). We will use
   this branch to build the documentation in Read the Docs on all patch releases for 
   this version.

#. Make latest translation strings available on Transifex.

   During beta, a translation freeze is in place (ie no changes to the translatable
   strings are allowed). Strings need to be extracted and uploaded to
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

   c. Get the latest translations (of the previous CKAN release) from
      Transifex, in case any have changed since::

        tx pull --all --minimum-perc=5 --force

      (This ignores any language files which less than 5% translation - which
      is the bare minimum we require)

   e. Update the ``ckan.po`` files with the new strings from the ``ckan.pot`` file::

        python setup.py update_catalog --no-fuzzy-matching

      Any new or updated strings from the CKAN source code will get into the po
      files, and any strings in the po files that no longer exist in the source
      code will be deleted (along with their translations).

      We use the ``--no-fuzzy-matching`` option because fuzzy matching often
      causes problems with Babel and Transifex.

      If you get this error for a new translation:

          babel.core.UnknownLocaleError: unknown locale 'crh'

      then it's Transifex appears to know about new languages before Babel
      does. Just delete that translation locally - it may be ok with a newer Babel in
      later CKAN releases.

   f. Run msgfmt checks::

          find ckan/i18n/ -name "*.po"| xargs -n 1 msgfmt -c

      You must correct any errors or you will not be able to send these to Transifex.

      A common problem is that Transifex adds to the end of a po file as
      comments any extra strings it has, but msgfmt doesn't understand them. Just
      delete these lines.

   g. Run our script that checks for mistakes in the ckan.po files::

        paster check-po-files ckan/i18n/*/LC_MESSAGES/ckan.po

      If the script finds any mistakes then at some point before release you
      will need to correct them, but it doesn't need to be done now, since the priority
      is to announce the call for translations.

      When it is done, you must do the correction on Transifex and then run
      the tx pull command again, don't edit the files directly. Repeat until the
      script finds no mistakes.

   h. Edit ``.tx/config``, on line 4 to set the Transifex 'resource' to the new
      major release name (if different), using dashes instead of dots.
      For instance v2.4.0, v2.4.1 and v2.4.2 all share: ``[ckan.2-4]``.

   i. Create a new resource in the CKAN project on Transifex by pushing the new
      pot and po files::

        tx push --source --translations --force

      Because it reads the new version number in the ``.tx/config`` file, tx will
      create a new resource on Transifex rather than updating an existing
      resource (updating an existing resource, especially with the ``--force``
      option, can result in translations being deleted from Transifex).

      If you get a 'msgfmt' error, go back to the step where msgfmt is run.

   j. On Transifex give the new resource a more friendly name. Go to the
      resource e.g. https://www.transifex.com/okfn/ckan/2-5/ and the settings are
      accessed from the triple dot icon "...". Keep the slug like "2-4", but change
      the name to be like "CKAN 2.5".

   k. Update the ``ckan.mo`` files by compiling the po files::

        python setup.py compile_catalog

      The mo files are the files that CKAN actually reads when displaying
      strings to the user.

   l. Commit all the above changes to git and push them to GitHub::

        git add ckan/i18n/*.mo ckan/i18n/*.po
        git commit -am "Update strings files before CKAN X.Y.Z call for translations"
        git push

#. Send an annoucement email with a call for translations.

   Send an email to the ckan-dev list, tweet from @CKANproject and send a
   transifex announcement from: https://www.transifex.com/okfn/ckan/announcements/
   . Make sure to post a link to the correct Transifex resource (like `this one
   <https://www.transifex.com/okfn/ckan/2-5/>`_) and tell users that they can
   register on Transifex to contribute. Give a deadline in two weeks time.

#. Create deb packages.

   Ideally do this once a week. Create the deb package with the latest release
   branch, using ``betaX`` iterations. Deb packages are built using Ansible_
   scripts located at the following repo:

       https://github.com/ckan/ckan-packaging

   The repository contains further instructions on how to run the scripts, but
   essentially you need to generate the packages (one for precise and one for
   trusty) on your local machine and upload them to the Amazon S3 bucket.

   To generate the packages, run::

     ./ckan-package -v 2.x.y -i betaX

   To upload the files to the S3 bucket, you will need the relevant credentials and
   to install the `Amazon AWS command line interface <http://docs.aws.amazon.com/cli/latest/userguide/installing.html>`_

   Make sure to upload them to the `build` folder, so they are not mistaken by
   the stable ones::

     aws s3 cp python-ckan_2.5.0-precisebeta1_amd64.deb s3://packaging.ckan.org/build/python-ckan_2.5.0-precisebeta1_amd64.deb

   Now the .deb files are available at http://packaging.ckan.org/build/ invite
   people on ckan-dev to test them.

-------------------------
Leading up to the release
-------------------------

#. Update the CHANGELOG.txt with the new version changes.

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

     But dread found changed the first step slightly to get it to work::

        git log --pretty=format:%s --reverse --no-merges release-v2.4.2...release-v2.5.0 -- | grep -Pzo "^\[#\K[0-9]+" | sort -u -n > issues_2.5.txt

#. A week before the translations will be closed send a reminder email.

#. Once the translations are closed, sync them from Transifex.

   Pull the updated strings from Transifex::

        tx pull --all --minimum-perc=5 --force

   Check and compile them as before::

        paster check-po-files ckan/i18n/*/LC_MESSAGES/ckan.po
        python setup.py compile_catalog

    The compilation shows the translation percentage. Compare this with the new
    languages directories added to ckan/i18n::

        git status

   ``git add`` any new ones. (If all is well, you won't see any that are under
   5% translated.)

   Now push::

        git commit -am "Update translations from Transifex"
        git push

#. A week before the actual release, announce the upcoming release(s).

   Send an email to the
   `ckan-announce mailing list <http://lists.okfn.org/mailman/listinfo/ckan-announce>`_,
   so CKAN instance maintainers can be aware of the upcoming releases. List any
   patch releases that will be also available. Here's an `example
   <https://lists.okfn.org/pipermail/ckan-announce/2015-July/000013.html>`_ email.

-----------------------
Doing the final release
-----------------------

Once the release branch has been thoroughly tested and is stable we can do
a release.

#. Run the most thorough tests::

        nosetests ckan/tests --ckan --ckan-migration --with-pylons=test-core.ini

#. Do a final build of the front-end, add the generated files to the repo and
   commit the changes::

        paster front-end-build
        git add ckan ckanext
        git commit -am "Rebuild front-end"

#. Review the CHANGELOG to check it is complete.

#. Check that the docs compile correctly::

        rm build/sphinx -rf
        python setup.py build_sphinx

#. Remove the beta letter in the version number.

   The version number is in ``ckan/__init__.py``
   (eg 2.5.0b -> 2.5.0) and commit the change::

        git commit -am "Update version number for release X.Y.Z"

#. Tag the repository with the version number.

   Make sure to push it to GitHub afterwards::

        git tag -a -m '[release]: Release tag' ckan-X.Y.Z
        git push --tags

#. Create and deploy the final deb package.

   Move it to the root of the
   `publicly accessible folder <http://packaging.ckan.org/>`_ of
   the packaging server from the `/build` folder.

   Make sure to rename it so it follows the deb packages name convention::

    python-ckan_Major.minor_amd64.deb

   Note that we drop any patch version or iteration from the package name.

#. Upload the release to PyPI::

        python setup.py sdist upload

   You will need a PyPI account with admin permissions on the ckan package,
   and your credentials should be defined on a ``~/.pypirc`` file such as::

        [distutils]
        index-servers =
            pypi

        [pypi]
        username: <user-name>
        password: <password>

   For more info, see:
   `here <http://docs.python.org/distutils/packageindex.html#pypirc>`_

   If running in Vagrant you may get error ``error: Operation not permitted``
   due to failure to create a hard link. The solution is to add a line at the top
   of setup.py::

        # Avoid problem releasing to pypi from vagrant
        import os
        if os.environ.get('USER', '') == 'vagrant':
            del os.link

   as described here: https://stackoverflow.com/questions/7719380/python-setup-py-sdist-error-operation-not-permitted

   If you upload a bad package, then you can remove it from PyPI however you
   must use a new version number next time.


#. Enable the new version of the docs on Read the Docs.

   (You will need an admin account.)

   a. Make sure the documentation branch is up to date with the latest changes in the 
      corresponding ``dev-vX.Y`` branch.

   b. If this is the first time a minor version is released, go to the
      `Read The Docs versions page <https://readthedocs.org/projects/ckan/versions/>`_
      and make the relevant release 'active' (make sure to use the documentation branch, ie X.Y,
      not the development branch, ie dev-vX.Y).

   c. If it is the latest stable release, set it to be the Default Version and
      check it is displayed on http://docs.ckan.org.

#. Write a CKAN blog post and announce it to ckan-announce & ckan-dev & twitter.

   CKAN blog here: <http://ckan.org/wp-admin>`_

   * `Example blog <http://ckan.org/2015/07/22/ckan-2-4-release-and-patch-releases/>`_
   * `Example email <https://lists.okfn.org/pipermail/ckan-dev/2015-July/009141.html>`_

   Tweet from @CKANproject

#. Cherry-pick the i18n changes from the release branch onto master.

   We don't generally merge or cherry-pick release branches into master, but
   the files in ckan/i18n are an exception. These files are only ever changed
   on release branches following the :ref:`beta-release` instructions above,
   and after a release has been finalized the changes need to be cherry-picked
   onto master.

   To find out what i18n commits there are on the release-v* branch that are
   not on master, do::

     git log master..dev-v* ckan/i18n

   Then ``checkout`` the master branch, do a ``git status`` and a ``git pull``
   to make sure you have the latest commits on master and no local changes.
   Then use ``git cherry-pick`` when on the master branch to cherry-pick these
   commits onto master. You should not get any merge conflicts. Run the
   ``check-po-files`` command again just to be safe, it should not report any
   problems. Run CKAN's tests, again just to be safe.  Then do ``git push
   origin master``.

------------------------
Preparing patch releases
------------------------

#. Announce the release date & time with a week's notice on ckan-announce.

   Often this will be part of the announcement of a CKAN major/minor release.
   But if patches go out separately then they will need their own announcement.

#. Update ``ckan/__init__.py`` with the incremented patch number e.g. `2.5.1` becomes `2.5.2`.
   Commit the change and push the new branch to GitHub::

        git commit -am "Update version number"
        git push origin release-v2.5.2

#. Cherry-pick PRs marked for back-port.

   These are usually marked on Github using the ``Backport Pending`` `labels`_ and the
   relevant labels for the versions they should be cherry-picked to (eg ``Backport 2.5.3``).
   Remember to look for PRs that are closed i.e. merged. Remove the ``Backport Pending`` label once the 
   cherry-picking has been done (but leave the version ones).

#. Ask the tech team if there are security fixes or other fixes to include.

#. Update the CHANGELOG.

------------------------
Doing the patch releases
------------------------

#. If there have been any CSS or JS changes, rebuild the front-end.

   Rebuild the front-end, add new files and commit with::

        paster front-end-build
        git add ckan ckanext
        git commit -am "Rebuild front-end"

#. Review the CHANGELOG to check it is complete.

#. Tag the repository with the version number.

   Make sure to push it to GitHub afterwards::

        git tag -a -m '[release]: Release tag' ckan-X.Y.Z
        git push --tags

#. Create and deploy the final deb package.

   Create using ckan-packaging checkout e.g.::

     ./ckan-package -v 2.5.2 -i 1

   Make sure to rename the deb files so it follows the deb packages name convention::

     python-ckan_Major.minor_amd64.deb

   Note that we drop the patch version and iteration number from the package name.

   Move it to the root of the
   `publicly accessible folder <http://packaging.ckan.org/>`_ of
   the packaging server from the `/build` folder, replacing the existing file
   for this minor version.

#. Upload the release to PyPI::

        python setup.py sdist upload

#. Make sure the documentation branch (``X.Y``) is up to date with the latest changes in the 
   corresponding ``dev-vX.Y`` branch.

#. Write a CKAN blog post and announce it to ckan-announce & ckan-dev & twitter.

   Often this will be part of the announcement of a CKAN major/minor release.
   But if patches go out separately then they will need their own announcement.

.. _Transifex: https://www.transifex.com/projects/p/ckan
.. _`Read The Docs`: http://readthedocs.org/dashboard/ckan/versions/
.. _labels: https://github.com/ckan/ckan/labels
.. _Ansible: http://ansible.com/
