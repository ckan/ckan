====================
Contributing to CKAN
====================

.. _CKAN repo on GitHub: https://github.com/okfn/ckan
.. _CKAN issue tracker: https://github.com/okfn/ckan/issues
.. _docs.ckan.org: http://docs.ckan.org
.. _Contributing to CKAN's Documentation: https://github.com/okfn/ckan/blob/master/CONTRIBUTING.rst#contributing-to-ckans-documentation

(This section is about contributing code, if you want to contribute
documentation see `Contributing to CKAN's Documentation`_.)

CKAN is a free software project and code contributions are welcome. To
contribute code to CKAN you should fork CKAN to your own GitHub account, push
your code to a feature branch on your fork, then make a pull request for your
branch on the central CKAN repo. We'll go through each step in detail below...


Fork CKAN on GitHub
-------------------


If you don't have access to the central `CKAN repo on GitHub`_ you should sign
up for a free account on `GitHub.com <https://github.com/>`_ and
`fork CKAN <https://help.github.com/articles/fork-a-repo>`_, so that you have somewhere to publish your CKAN code.

You can now clone your CKAN fork to your development machine, create a new
branch to commit your code on, and push your branch to your CKAN fork on GitHub
to share your code with others.


Feature Branches
----------------

Work for a feature or bug fix should be developed on a feature or bug branch
forked from master. Each individual feature or bug fix should be developed on
its own branch. The name of the branch should include the ticket number (if
this work has a ticket in the `CKAN issue tracker`_), the branch type
("feature" or "bug"), and a brief one-line synopsis of the purpose of the
ticket, for example::

 2298-feature-add-sort-by-controls-to-search-page
 1518-bug-upload-file-with-spaces

Naming branches this way makes it easy to search for a branch by its ticket
number using GitHub's web interface.


Commit Messages
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

If your commit has a ticket in the `CKAN issue tracker`_ put the ticket number
at the start of the first line of the commit message like this: ``[#123]``.
This makes the CKAN release manager's job much easier!

Here is an example CKAN commit message::

 [#2505] Update source install instructions

 Following feedback from markw (see #2406).


Keeping Up with master
----------------------

When developing on a branch you should periodically pull the latest commits
from the master branch of the central CKAN repo into your feature branch, to
prevent the two branches from diverging from each other too much and becoming
difficult to merge.

If you haven't already, add the central repo to your development repo as a
remote::

    git remote add central git://github.com/okfn/ckan.git
    git fetch central

Now, every now and then pull the latest commits from the central master branch
into your feature branch. While on your feature branch, do::

    git pull central master


Pull Requests & Code Review
---------------------------

.. _create a pull request on GitHub: https://help.github.com/articles/creating-a-pull-request

Once your work on a branch is complete and is ready to be merged into the
master branch, `create a pull request on GitHub`_.  A member of the CKAN team
will review your code and provide feedback on the pull request page. The
reviewer may ask you to make some changes to your code. Once the pull request
has passed the code review, the reviewer will merge your code into the master
branch and it will become part of CKAN!

When submitting a pull request:

- Your branch should contain code for one feature or bug fix only,
  see `Feature Branches`_.
- Your branch should contain new or changed tests for any new or changed
  code.
- Your branch should contain updates to the
  `CHANGELOG file <https://github.com/okfn/ckan/blob/master/CHANGELOG.txt>`_
  briefly summarising your code changes.
- Your branch should contain new or updated documentation for any new or
  updated code, see `Contributing to CKAN's Documentation`_.
- Your branch should be up to date with the master branch of the central
  CKAN repo, see `Keeping Up with master`_.
- All the CKAN tests should pass on your branch, see
  `Testing for Developers <http://docs.ckan.org/en/latest/test.html>`_.


Merging
-------

When merging a feature or bug branch into master:

- Use the ``--no-ff`` option in the ``git merge`` command,


Coding Standards
----------------

When writing code for CKAN, try to follow our
`coding standards <http://docs.ckan.org/en/latest/#for-ckan-developers>`_.


====================================
Contributing to CKAN's Documentation
====================================

Note: getting started with contributing to `docs.ckan.org`_ is a little
complicated.  An easier way to contribute documentation to CKAN is to
contribute to the `CKAN Wiki <https://github.com/okfn/ckan/wiki>`_. Docs
started on the wiki can make it onto `docs.ckan.org`_ later.

`docs.ckan.org`_ is created using `Sphinx <http://sphinx-doc.org/>`_. The
source files are in
`the doc directory of the CKAN git repo <https://github.com/okfn/ckan/tree/master/doc>`_.
To edit these docs:

1. If you haven't already, create a
   `Python virtual environment <http://pypi.python.org/pypi/virtualenv>`_
   (virtualenv), activate it and clone the CKAN git repo into it. In this
   example we'll create a virtualenv in a folder called ``pyenv``::

    virtualenv --no-site-packages pyenv
    . pyenv/bin/activate
    pip install -e 'git+https://github.com/okfn/ckan.git#egg=ckan'

2. Install the Python dependencies necessary for building the CKAN docs into
   your virtualenv::

    pip install -r pyenv/src/ckan/pip-requirements-docs.txt

3. Fetch the git submodule that contains CKAN's custom Sphinx theme::

    cd pyenv/src/ckan
    git submodule init
    git submodule update

   Note: you may occassionally have to run ``git submodule update`` again,
   when someone updates the submodule.

4. Make changes to the documentation by using your text editor to edit the
   ``pyenv/src/ckan/doc/*.rst`` files.

5. Build the documentation locally, to preview your changes::

    python setup.py build_sphinx

   Now you can open the built HTML files in
   ``pyenv/src/ckan/build/sphinx/html`` to see your changes, e.g.:
   ``firefox pyenv/src/ckan/build/sphinx/html/index.html``.

6. Finally, when you're ready to submit your contributions to the CKAN
   project, follow the same process as for contributing code, see
   `Contributing to CKAN`_.

