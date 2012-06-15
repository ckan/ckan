=====================
CKAN Coding Standards
=====================

Commit Guidelines
=================

Generally, follow the `commit guidelines from the Pro Git book`_:

- Avoid committing any whitespace errors. One tool you can use to find
  whitespace errors is the ``git diff --check`` command.

- Try to make each commit a logically separate, digestible changeset.

- Try to make the first line of the commit message less than 50 characters
  long, and describe the entire changeset concisely.

- Optionally, follow with a blank line and then a more detailed explanation of
  the changeset, hard-wrapped to 72 characters, giving the motivation for the
  change and contrasting the new with the previous behaviour.

- Use the imperative present tense as if you were giving commands to the
  codebase to change its behaviour, e.g. *Add tests for*, *make xyzzy do
  frotz*, **not** *Adding tests for*, *I added tests for*, *[This patch] makes
  xyzzy do frotz* or *[I] changed xyzzy to do frotz*.

- Try to write the commit message so that a new CKAN developer could understand
  it, i.e. using plain English as far as possible, and not referring to too
  much assumed knowledge or to external resources such as mailing list
  discussions (summarize the relevant points in the commit message instead).

.. _commit guidelines from the Pro Git book: http://git-scm.com/book/en/Distributed-Git-Contributing-to-a-Project#Commit-Guidelines

In CKAN we also refer to `trac.ckan.org`_ ticket numbers in commit messages
wherever relevant. This makes the release manager's job much easier! There
should be few commits that don't refer to a trac ticket, e.g. if you find a
typo in a docstring and quickly fix it you wouldn't bother to create a ticket
for this.

Put the ticket number in square brackets (e.g. ``[#123]``) at the start of the
first line of the commit message. You can also reference other Trac tickets
elsewhere in your commit message by just using the ticket number on its own
(e.g. ``see #456``). Full example:

::

    [#2505] Update source install instructions
    
    Following feedback from markw (see #2406).

.. _trac.ckan.org: http://trac.ckan.org/

Longer example CKAN commit message:

::

 [#2304] Refactor user controller a little
 
 Move initialisation of a few more template variables into
 _setup_template_variables(), and change read(), edit(), and followers() to use
 it. This removes some code duplication and fixes issues with the followers
 count and follow button not being initialisd on all user controller pages.

 Change new() to _not_ use _setup_template_variables() as it only needs
 c.is_sysadmin and not the rest.

 Also fix templates/user/layout.html so that the Followers tab appears on both
 your own user page (when logged in) and on other user's pages.

Merging
-------

When merging a feature or bug branch into master:

- Use the ``--no-ff`` option in the ``git merge`` command
- Add an entry to the ``CHANGELOG`` file

Frontend Coding Standards
=========================

TODO

http://aron.github.com/ckan-style/styleguide/

Backend Coding Standards
========================

TODO

http://wiki.okfn.org/Coding_Standards

Docstring Standards
-------------------

We want CKAN's docstrings to be clear and easy to read for programmers who are
smart and competent but who may not know a lot of CKAN technical jargon and
whose first language may not be English. We also want it to be easy to maintain
the docstrings and keep them up to date with the actual behaviour of the code
as it changes over time. So:

- Keep docstrings short, describe only what's necessary and no more
- Keep docstrings simple, use plain English, try not to use a long word
  where a short one will do, and try to cut out words where possible
- Try to avoid repetition

PEP 257
```````

Generally, follow `PEP 257`_. We'll only describe the ways that CKAN differs
from or extends PEP 257 below.

.. _PEP 257: http://www.python.org/dev/peps/pep-0257/

CKAN docstrings deviate from PEP 257 in a couple of ways:

- We use ``'''triple single quotes'''`` around docstrings, not ``"""triple
  double quotes"""`` (put triple single quotes around one-line docstrings as
  well as multi-line ones, it makes them easier to expand later)
- We use Sphinx directives for documenting parameters, exceptions and return
  values (see below)

Sphinx
``````
Use `Sphinx directives`_ for documenting the parameters, exceptions and returns
of functions:

- Use ``:param`` and ``:type`` to describe each parameter
- Use ``:returns`` and ``:rtype`` to describe each return
- Use ``:raises`` to describe each exception raised

Example of a short docstring:

::

    @property
    def packages(self):
        '''Return a list of all packages that have this tag, sorted by name.

        :rtype: list of ckan.model.package.Package objects

        '''

Example of a longer docstring:

::

    @classmethod
    def search_by_name(cls, search_term, vocab_id_or_name=None):
        '''Return all tags whose names contain a given string.

        By default only free tags (tags which do not belong to any vocabulary)
        are returned. If the optional argument ``vocab_id_or_name`` is given
        then only tags from that vocabulary are returned.

        :param search_term: the string to search for in the tag names
        :type search_term: string
        :param vocab_id_or_name: the id or name of the vocabulary to look in
            (optional, default: None)
        :type vocab_id_or_name: string

        :returns: a list of tags that match the search term
        :rtype: list of ckan.model.tag.Tag objects

        '''


The phrases that follow ``:param foo:``, ``:type foo:``, or ``:returns:``
should not start with capital letters or end with full stops. These should be
short phrases and not full sentences. If more detail is required put it in the
function description instead.

Indicate optional arguments by ending their descriptions with (optional) in
brackets. Where relevant also indicate the default value: (optional, default:
5). It's also helpful to list all required parameters before optional ones.

.. _Sphinx directives: http://sphinx.pocoo.org/markup/desc.html#info-field-lists

You can also use a little inline `reStructuredText markup`_ in docstrings, e.g.
``*stars for emphasis*`` or ````double-backticks for literal text````.

.. _reStructuredText markup: http://docutils.sourceforge.net/docs/user/rst/quickref.html#inline-markup

CKAN Action API Docstrings
``````````````````````````

Docstrings from CKAN's action API are processed with `autodoc`_ and
included in the API chapter of CKAN's documentation. The intended audience of
these docstrings is users of the CKAN API and not (just) CKAN core developers.

In the Python source each API function has the same two arguments (``context``
and ``data_dict``), but the docstrings should document the keys that the
functions read from ``data_dict`` and not ``context`` and ``data_dict``
themselves, as this is what the user has to POST in the JSON dict when calling
the API.

Where practical, it's helpful to give examples of param and return values in
API docstrings.

CKAN datasets used to be called packages and the old name still appears in the
source, e.g. in function names like package_list(). When documenting functions
like this write dataset not package, but the first time you do this put package
after it in brackets to avoid any confusion, e.g.

::

    def package_show(context, data_dict):
        '''Return the metadata of a dataset (package) and its resources.

Example of a ckan.logic.action API docstring:

::

    def vocabulary_create(context, data_dict):
        '''Create a new tag vocabulary.

        You must be a sysadmin to create vocabularies.

        :param name: the name of the new vocabulary, e.g. ``'Genre'``
        :type name: string
        :param tags: the new tags to add to the new vocabulary, for the format of
            tag dictionaries see ``tag_create()``
        :type tags: list of tag dictionaries

        :returns: the newly-created vocabulary
        :rtype: dictionary

        '''

.. _Autodoc: http://sphinx.pocoo.org/ext/autodoc.html
