=======================
Writing commit messages
=======================

We use the version control system `git <http://git-scm.com/>`_ for our code
and documentation, so when contributing code or docs you'll have to commit
your changes to git and write a git commit message.
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

 [#607] Allow reactivating deleted datasets

 Currently if a dataset is deleted and users navigate to the edit form,
 there is no state field and the delete button is still shown.

 After this change, the state dropdown is shown if the dataset state is
 not active, and the delete button is not shown.

