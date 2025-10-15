=================
Maintenance tools
=================

This section describes tools and automations used by the development team to help
in the maintenance of the CKAN source and repositories.

.. _ckanbot:

----------------------------
The *ckanbot* GitHub account
----------------------------

For actions that need to be authenticated in the CKAN GitHub repository, we don't use
personal accounts but rather a dedicated automated account, `@ckanbot <https://github.com/ckanbot>`_.

This account has only write access to specific repositories needed, given via the `ckanbot team <https://github.com/orgs/ckan/teams/ckanbot/members>`_ of the *ckan* organization.


.. _automated_backports:

---------------------------
Automated backports actions
---------------------------

.. note:: The backports action was added on April 2024

To avoid havig to manually backport merged pull requests (PR) to release branches once these are merged,
a new GitHub Action (`configuration file <https://github.com/ckan/ckan/blob/master/.github/workflows/backports.yml>`_)
was added to automate this process whenever possible.

The behaviour of this action is the following:

* When a PR that has a label with the pattern ``Backport <branch>`` is merged,
  it will trigger a backport action
* If the PR commits merge cleanly into the target branch, a new PR will
  be created against it, assigned to the same user as the merged one.
  The usual checks will be run on the new PR
* If the commits don't merge cleanly, a comment will be posted on the
  orginal PR with the manual commands to fix the conflicts, and the PR
  will be labelled with "Backport failed"
* Additionally, Tech Team members can trigger a backport on open or
  already closed PRs adding a comment starting with ``/backport`` (and
  adding the relevant label)

There are two repository variables and a repository secret needed to run the action
(check the `documentation <https://docs.github.com/en/actions/learn-github-actions/variables#creating-configuration-variables-for-a-repository>`_
on how to set up these):

* The public variable ``TECH_TEAM_USER_IDS`` is a JSON list of the GitHub user ids of the Tech Team members. User ids can be found using the ``https://api.github.com/users/<user_name>`` endpoint.
* The public variable ``CKANBOT_USER_ID`` is the user id of the :ref:`ckanbot`.
* The secret ``BACKPORT_ACTION_PAT`` is a `Personal Access Token <https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens>`_ (PAT) of the ckanbot account, with enough permissions to write to the ckan/ckan repository.

When creating a new PAT, make sure to select the following settings:

* Token name: ``backports_action``
* Expiration: set it at something reasonable like 1 year
* Resource owner: *ckan* organization
* Repository access: Only select repositories (select *ckan/ckan*)
* Repository permissions: Select *Content* (Read and Write) and *Pull Requests* (Read and Write)

Once generated the token, it will have to be approved by someone with permissions in the *@ckan* organization (by going to Settings > Third-party Access > Personal access tokens > Pending requests).


.. _publish_pypi:

----------------------------
Automatic publishing to PyPI
----------------------------


.. note:: Automatic publishing to PyPI was added on November 2024

The main CKAN repo has GitHub workflows that allows to publish to
    
* `PyPI <https://github.com/ckan/ckan/blob/master/.github/workflows/publish-pypi.yml>`_ when a release tag (``ckan-*``) is pushed
* `Test PyPI <https://github.com/ckan/ckan/blob/master/.github/workflows/publish-test-pypi.yml>`_ when a PR is merged (Using test.pypi.org allows us to check that the workflow is healthy).
    
Besides the workflow file there are two additional configurations needed:
    
* `GitHub Actions environmnents`_: This allows us to define additional rules
  and limit how actions are run.
* `Trusted Publishers`_ on PyPI: This allows the actions to authenticate
  without having to share API tokens around

.. _create_github_release:

--------------------------------------
Automatic creation of a GitHub release
--------------------------------------


.. note:: Automatic publishing to PyPI was added on December 2024

The main CKAN repo has a GitHub `workflow <https://github.com/ckan/ckan/blob/master/.github/workflows/github-release.yml>`_ 
that creates a `GitHub release <https://github.com/ckan/ckan/releases>`_ whenever a release tag (``ckan-*``) is pushed.

The releases only contain a link to the full changelog in docs.ckan.org.


.. _GitHub Actions environmnents:   https://docs.github.com/en/actions/managing-workflow-runs-and-deployments/managing-deployments/managing-environments-for-deployment
.. _Trusted Publishers: https://docs.pypi.org/trusted-publishers/
