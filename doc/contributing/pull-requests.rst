=====================
Making a pull request
=====================

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

   When writing your git commit messages, try to follow the
   :doc:`commit-messages` guidelines.


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

   - You should have good commit messages, see :doc:`commit-messages`.

   - Your branch should contain new or changed tests for any new or changed
     code, and all the CKAN tests should pass on your branch, see
     :doc:`test`.

   - Your pull request shouldn't lower our test coverage. You can check it at
     our `coveralls page <https://coveralls.io/r/ckan/ckan>`. If for some
     reason you can't avoid lowering it, explain why on the pull request.

   - Your branch should contain new or updated documentation for any new or
     updated code, see :doc:`documentation`.

   - Your branch should be up to date with the master branch of the central
     CKAN repo, so pull the central master branch into your feature branch
     before submitting your pull request.

     For long-running feature branches, it's a good idea to pull master into
     the feature branch periodically so that the two branches don't diverge too
     much.

.. _create a pull request on GitHub: https://help.github.com/articles/creating-a-pull-request
