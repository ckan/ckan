====================================
Reviewing and merging a pull request
====================================

Of course it's not possible to give an exact recipe for reviewing a pull
request, you simply have to assess the code and decide whether you're happy
with it. Nonetheless, here is an incomplete list of things to look for:

- Does the pull request contain one logically separate piece of work
  (e.g. one new feature, bug fix, etc. per pull request)?

- Does the pull request follow the guidelines for
  :doc:`writing commit messages <commit-messages>`?

- Is the branch up to date - have the latest commits from master been pulled
  into the branch?

- Does the pull request contain new or updated tests for any new or updated
  code, and do the tests follow
  :doc:`CKAN's testing coding standards <testing>`?

- Do all the CKAN tests pass, on the new branch?

- Does the pull request contain new or updated docs for any new or updated
  features, and do the docs follow
  :doc:`CKAN's documentation guidelines <documentation>`?

- Does the new code follow CKAN's code architecture and the various coding
  standards for Python, JavaScript, etc.?

- If the new code contains changes to the database schema, does it have a
  :doc:`database migration <database-migrations>`?

- Does the code contain any changes that break backwards-incompatibility?
  If so, is the breakage necessary or do the benefits of the change justify the
  breakage? Have the breaking changes been added to the :doc:`changelog
  </changelog>`?

  Backwards-compability needs to be considered when making changes that break
  the interfaces that CKAN provides to third-party code, including API clients,
  plugins and themes.

  In general, any code that's documented in the reference sections of the
  :doc:`API </api/index>`, :doc:`extensions </extensions/index>` or
  :doc:`theming </theming/index>`
  needs to be considered. For example this includes changes
  to the API actions, the plugin interfaces or plugins toolkit, the converter
  and validator functions (which are used by plugins), the custom Jinja2 tags
  and variables available to Jinja templates, the template helper functions,
  the core template files and their blocks, the sandbox available to JavaScript
  modules (including custom jQuery plugins and the JavaScript CKAN API client),
  etc.

- Does the new code add any dependencies to CKAN (e.g. new third-party Python
  modules imported)? If so, is the new dependency justified and has it been
  added following the right process? See :doc:`upgrading-dependencies`.


----------------------
Merging a pull request
----------------------

Once you've reviewed a pull request and you're happy with it, you need to
merge it into the master branch. You should do this using the ``--no-ff``
option in the ``git merge`` command. For example::

 git checkout feature-branch
 git pull origin feature-branch
 git checkout master
 git pull origin master
 git merge --no-ff feature-branch
 git push origin master

Before doing the ``git push``, it's a good idea to check that all the tests are
passing on your master branch (if the latest commits from master have already
been pulled into the feature branch on github, then it may be enough to check
that all tests passed for the latest commit on this branch on
`Travis <https://travis-ci.org/okfn/ckan>`_).

Also before doing the ``git push``, it's a good idea to use ``git log`` and/or
``git diff`` to check the difference between your local master branch and the
remote master branch, to make sure you only push the changes you intend to
push::

 git log ...origin/master
 git diff ..origin/master
