==========================
Writing CKAN Documentation
==========================

..
  https://docs.djangoproject.com/en/1.5/internals/contributing/writing-documentation/


This section describes how the CKAN documentation is written and structured
from a documentation writer's point of view, and explains how writers can best
craft their CKAN documentation changes.

The aim of this document is to make it easy for CKAN developers to write CKAN documentation:

* Know how to start, it can be overwhelming
* Know where the new docs should go in the overall docs
* Know what the new docs should look like: structure, and what should be
  included
* Know how detailed the docs should be, how they should be written are,
  what are standards for good documentation are
* Know who their audience is (different audiences for different docs)


.. todo::
   How to get the docs source.
   Explain the the docs are written in Sphinx, which uses docutils.
    http://sphinx-doc.org/
    http://docutils.sourceforge.net/
   How to build the docs locally (including installing sphinx and the submodule).
   How to submit a github pull request (cross-ref to CONTRIBUTING)
   Symlink README  from docs

---------
Audiences
---------

Jacob Kaplan Moss:
Why do people read documentation? What are they looking for?

- Overviews
- Examples
- You have a problem you need to solve
- It's broken how do I fix it?

- **First contact** for new users
- Ongoing **education** for existing users (eg. how to use specific parts of
ckan)
- **Support** for experienced users who've run into problems
- CKAN devs should find it useful to consult CKAN's docs frequently!
    Even for code they wrote themselves!
- **Troubleshooting** for annoyed users (it's broken and I don't know why)
- **Developers** who want documentation of internals, how to contribute, etc.
- **Reference**

----------
Hard Rules
---------

Don't fuck up the structure.
Don't paste long code examples into the docs.
Don't implement undocumented features
TO BE DOCUMENTED - features should _never_ be missing from the docs! If docs
cannot be written, a stub page should be added.

---------
Structure
---------

The overall structure of the CKAN documentation is as follows::

- Intro (to the docs)
- Overview (of CKAN)
- Contact
- Installation
- Upgrading
- Features
- Extensions
- Theming
- Writing Extensions
- API
- Config
- Changelog
- Release Cycle
- Development

This structure is meant to be clear, simple and extendable.

--------------------------
What should be documented?
--------------------------

TO BE DOCUMENTED - features should _never_ be missing from the docs! If docs
cannot be written, a stub page should be added.

- Overviews (of CKAN as a whole, of a feature or topic)
- Tutorials (success within 30 mins)
- Topic guides (conceptual understanding, give the _why_)
- Reference
- Troubleshooting

The recursive/fractal structure of documentation: Each project (ie. the docs as
whole), each document within a project, each section within a document, and
each element within a section, breaks down into the same four-part structure
(at smaller and smaller scale): Tutorials, Topic Guides, Reference,
Troubleshooting. (See slide at 22:00)

-------------------
Commonly Used Terms
-------------------

Here are some style guidelines on commonly used terms throughout the docs:

* CKAN config file (not settings file, ini file, etc.)
* The default location for the config file is /etc/ckan/production.ini
  (define a substitute for this?)
* Config options have settings. The option is set.
* PostgreSQL
* SQLite
* Python (capitalized)


------------------------
General Style Guidelines
------------------------

.. 
    http://jacobian.org/writing/great-documentation/technical-style/

* American spelling: realize, customize, initialize, etc. (-ize not -ise)

* In section titles, capitalize only initial words and `proper nouns
  <http://en.wikipedia.org/wiki/Proper_noun>`_ (nouns that refer to unique
  entities or unique groups of entities, not classes of entities). For example,
  you would capitalize London, Jupiter, Sarah or Microsoft, but not city,
  planet, person or corporation.
* Wrap at 80 chars, unless for a good reason
* Use semantic line breaks?
* Be concrete not abstract, for example::

    organizations give permissions to users to perform actions on datasets
    -> organizations control who can see, create and update datasets
    (removed abstract/jargon terms "permissions", "actions")

* Be concise, rewrite sentences to remove unnecessary words, for example::

    the datasets belonging to an organization
    -> an organization's datasets
    all users -> everyone

* Small code snippets can help to make the docs clearer, but once you get to
  complete classes or functions put working code with tests in ``examples/``
  then include it

* Facilitate skimming and quickly identifying what's important/finding what
  they need:

  - Use inline markup liberally: italics, bold, code, etc.
  - Short paragraphs, 5-6 sentences max, break into small pieces not walls of
    text.
  - Use a variety of tables, lists and callouts (notes etc)
  - Visualise structure with headers, lets people skim pages and quickly find
    what they're looking for

- Be conversational: contractions, starting sentences with conjunctions
- Personal tone, use "I" (or "we", but be consistent)
- Use the second person, future tense as you would if you were giving verbal
  instructions to someone who was in the room with you: "First, you'll need to
  do X. Then, when you've done Y, you can start working on Z."
- Keep it short, remove unnecessary or vague words



-----------
Sphinx Tips
-----------

* Use versionadded and versionchanged
* Use deprecated
* Add as much semantic markup as possible: code, italics, bold, proper
  cross-refs like :mod: and :setting: etc.
* Cross-ref config options
* Use .. include:: to avoid duplication
* Use definition lists
* Explain how to do different types of link and cross-ref, including different
  link text
* Use autodoc
* :doc: is for linking to a whole page, :ref: for something within a page
* Labels on all options in configuration.rst
* .. code-block:: <lang>
* Make class names shorter in output with ~: :class:`~django.contrib.contenttypes.models.ContentType`


Headings
========

Use:

    =================
    Top-Level Heading
    =================

    --------------------
    Second-Level Heading
    --------------------

    Third-Level Heading
    ===================

    Fourth-Level Heading
    --------------------

If you need more than four levels of headings, you're probably doing something
wrong, but see:
http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#sections


Cross-referencing config options
================================

Each config option should be defined in `doc/configuration.rst` and should have
a reST label for cross-referencing, e.g.:

    .. _ckan.site_title:

    ckan.site_title
    ^^^^^^^^^^^^^^^

    Example::

    ckan.site_title = Open Data Scotland

    Default value:  ``CKAN``

    This sets the name of the site, as displayed in the CKAN web interface.

The label should be the same as the name of the config option (including the
same use of . and _). You can cross-reference any config option from any file
in `docs/` with `:ref:`:

    This is combined with your :ref:`ckan.site_title` to form the ``From:``
    header of the email that are sent,


Deprecating things
==================

Use Sphinx's ```deprecated`` directive
<http://sphinx-doc.org/markup/para.html#directive-deprecated>`_ to mark things
as deprecated in the docs::

    .. deprecated:: 3.1
       Use :func:`spam` instead.


Use Intersphinx to link to docs of other projects
=================================================


Use ..include:: to avoid duplicating docs
=========================================

In ``configuration.rst``::

    .. start_config-authorization

    blah blah blah

    .. end_config-authorization

Then in ``authorization.rst``::

    .. include:: /configuration.rst
        :start-after: start_config-authorization
        :end-before: end_config-authorization


--------------------------------
Documentation Driven Development
--------------------------------

Document first, share docs with others before the code is written.
Don't document your code, code your documentation.

Writing good documentation first will make you write good (simple, logical,
consistent, easy-to-use, easy-to-explain) code in the first place.  
(What the hell were we thinking, when we wrote this code??)  
The developer who writes some code, should write the docs for that code, so
that they'll realise if they're screwing the users by writing bad code.

Save time: Write code; write docs; rewrite code (this has happened several
times with CKAN features) becomes: write docs; write code.

Avoid writing code that is functional, but not usable.
