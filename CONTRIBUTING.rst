.. External links in this file are done manually instead of using Sphinx stuff
   like :doc:, :ref:, toctree etc.  because GitHub also renders this file as
   reStructuredText when it shows its "guidelines for contributing" link when
   you make a new issue or pull request, and Sphinx things like toctree don't
   work there. See: https://github.com/blog/1184-contributing-guidelines

====================
Contributing to CKAN
====================

.. _CKAN repo on GitHub: https://github.com/okfn/ckan
.. _CKAN issue tracker: https://github.com/okfn/ckan/issues
.. _docs.ckan.org: http://docs.ckan.org

CKAN is free open source software and code contributions are welcome, whether
they're bug reports, source code, documentation or translations. The sections
below will walk you through our processes for making different kinds of
contributions to CKAN.

.. contents::
   :local:
   :depth: 1


----------------
Reporting issues
----------------

If you've found a bug in CKAN, open a new issue on CKAN's `GitHub Issues`_ (try
searching first to see if there's already an issue for your bug).

.. _GitHub Issues: https://github.com/okfn/ckan/issues


----------------
Translating CKAN
----------------

For contributing translations to CKAN, see
`Translating CKAN <http://docs.ckan.org/en/latest/i18n.html>`_.

.. toctree::
   :hidden:

   i18n

.. _coding standards:

----------------
Coding standards
----------------

When writing code for CKAN, try to respect our coding standards:

.. toctree::
   :hidden:

   ckan-coding-standards
   python-coding-standards
   html-coding-standards
   css-coding-standards
   javascript-coding-standards
   testing-coding-standards
   upgrading-dependencies

* `CKAN coding standards <http://docs.ckan.org/en/latest/ckan-coding-standards.html>`_
* `Python coding standards <http://docs.ckan.org/en/latest/python-coding-standards.html>`_
* `HTML coding standards <http://docs.ckan.org/en/latest/html-coding-standards.html>`_
* `CSS coding standards <http://docs.ckan.org/en/latest/css-coding-standards.html>`_
* `JavaScript coding standards <http://docs.ckan.org/en/latest/javascript-coding-standards.html>`_
* `Testing coding standards <http://docs.ckan.org/en/latest/testing-coding-standards.html>`_
* `Upgrading CKAN's dependencies <http://docs.ckan.org/en/latest/upgrading-dependencies.html>`_


---------------
Commit messages
---------------

Generally, follow the `commit guidelines from the Pro Git book`_:

- Try to make each commit a logically separate, digestible changeset.

- The first line of the commit message should concisely summarise the
  changeset.

- Optionally, follow with a blank line and then a more detailed explanation of
  the changeset.

- Use the imperative present tense as if you were giving commands to the
  codebase to change its behaviour, e.g. *Add tests for...*, *make xyzzy do
  frotz...*, this helps to make the commit message easy to read.

.. _commit guidelines from the Pro Git book: http://git-scm.com/book/en/Distributed-Git-Contributing-to-a-Project#Commit-Guidelines

If your commit has an issue in the `CKAN issue tracker`_ put the issue number
at the start of the first line of the commit message like this: ``[#123]``.
This makes the CKAN release manager's job much easier!

Here's an example of a good CKAN commit message::

 [#2505] Update source install instructions

 Following feedback from markw (see #2406).




-------------------------------
Frontend development guidelines
-------------------------------

.. toctree::
   :hidden:

   frontend-development
   templating
   resources
   template-tutorial
   template-blocks
   javascript-module-tutorial

* `Frontend Development <http://docs.ckan.org/en/latest/frontend-development.html>`_
* `Templating <http://docs.ckan.org/en/latest/templating.html>`_
* `Resources <http://docs.ckan.org/en/latest/resources.html>`_
* `Template Tutorial <http://docs.ckan.org/en/latest/template-tutorial.html>`_
* `Template Blocks <http://docs.ckan.org/en/latest/template-blocks.html>`_
* `JavaScript Module Tutorial <http://docs.ckan.org/en/latest/javascript-module-tutorial.html>`_


---------------------
Writing documentation
---------------------

The quickest and easiest way to contribute documentation to CKAN is to sign up
for a free GitHub account and simply edit the `CKAN Wiki <https://github.com/okfn/ckan/wiki>`_.
Docs started on the wiki can make it onto `docs.ckan.org`_ later.

**Tip**: Use the reStructuredText markup format when creating a wiki page,
since reStructuredText is the format that docs.ckan.org uses, this will make
moving the documentation from the wiki into docs.ckan.org later easier.

For how to contribute to the offical CKAN documentation at docs.ckan.org, see
the `documentation guidelines <http://docs.ckan.org/en/latest/documentation-guidelines.html>`_.

.. toctree::
   :hidden:

   documentation-guidelines


.. _making a pull request:

---------------------
Making a pull request
---------------------

Once you've written some CKAN code or documentation, you can submit it for
review and merge into the central CKAN git repository by making a pull request.
This section will walk you through the steps for making a pull request.


#. Create a git branch

   Each logically separate piece of work (e.g. a new feature, a bug fix, a new
   docs page, or a set of improvements to a docs page) should be developed on
   its own branch forked from the master branch.

   The name of the branch should include the issue number (if this work has an
   issue in the `CKAN issue tracker`_), and a brief one-line synopsis of the work,
   for example::

    2298-add-sort-by-controls-to-search-page


#. Fork CKAN on GitHub

   Sign up for a free account on GitHub and
   `fork CKAN <https://help.github.com/articles/fork-a-repo>`_, so that you
   have somewhere to publish your work.

   Add your CKAN fork to your local CKAN git repo as a git remote. Replace
   ``USERNAME`` with  your GitHub username::

       git remote add my_fork https://github.com/USERNAME/ckan


#. Commit and push your changes

   Commit your changes on your feature branch, and push your branch to GitHub.
   For example, make sure you're currently on your feature branch then run
   these commands::

     git add doc/my_new_feature.rst
     git commit -m "Add docs for my new feature"
     git push my_fork my_branch

   When writing your git commit messages, try to follow the `Commit Messages`_
   guidelines.


#. Send a pull request

   Once your work on a branch is complete and is ready to be merged into the
   master branch, `create a pull request on GitHub`_.  A member of the CKAN
   team will review your work and provide feedback on the pull request page.
   The reviewer may ask you to make some changes. Once your pull request has
   passed the review, the reviewer will merge your code into the master branch
   and it will become part of CKAN!

   When submitting a pull request:

   - Your branch should contain one logically separate piece of work, and not
     any unrelated changes.

   - You should have good commit messages, see `Commit Messages`_.

   - Your branch should contain new or changed tests for any new or changed
     code, and all the CKAN tests should pass on your branch, see
     `Testing CKAN <http://docs.ckan.org/en/latest/test.html>`_.

   - Your branch should contain new or updated documentation for any new or
     updated code, see `Writing Documentation`_.

   - Your branch should be up to date with the master branch of the central
     CKAN repo, so pull the central master branch into your feature branch
     before submitting your pull request.

     For long-running feature branches, it's a good idea to pull master into
     the feature branch periodically so that the two branches don't diverge too
     much.

.. _create a pull request on GitHub: https://help.github.com/articles/creating-a-pull-request


Merging a pull request
======================

If you're reviewing a pull request for CKAN, when merging a branch into master:

- Use the ``--no-ff`` option in the ``git merge`` command,
