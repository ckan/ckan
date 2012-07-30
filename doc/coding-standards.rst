=====================
CKAN Coding Standards
=====================

Commit Guidelines
=================

Generally, follow the `commit guidelines from the Pro Git book`_:

- Try to make each commit a logically separate, digestible changeset.

- The first line of the commit message should concisely summarise the
  changeset.

- Optionally, follow with a blank line and then a more detailed explanation of
  the changeset.

- Use the imperative present tense as if you were giving commands to the
  codebase to change its behaviour, e.g. *Add tests for...*, *make xyzzy do
  frotz...*, this helps to make the commit message easy to read.

- Try to write the commit message so that a new CKAN developer could understand
  it, i.e. using plain English as far as possible, and not referring to too
  much assumed knowledge or to external resources such as mailing list
  discussions (summarize the relevant points in the commit message instead).

.. _commit guidelines from the Pro Git book: http://git-scm.com/book/en/Distributed-Git-Contributing-to-a-Project#Commit-Guidelines

In CKAN we also refer to `trac.ckan.org`_ ticket numbers in commit messages
wherever relevant. This makes the release manager's job much easier!  Of
course, you don't have to reference a ticket from your commit message if there
isn't a ticket for it, e.g. if you find a typo in a docstring and quickly fix
it you wouldn't bother to create a ticket for this.

Put the ticket number in square brackets (e.g. ``[#123]``) at the start of the
first line of the commit message. You can also reference other Trac tickets
elsewhere in your commit message by just using the ticket number on its own
(e.g. ``see #456``). For example:

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

Feature Branches
----------------

All ticketed work should be developed on a corresponding feature branch forked
from master.  The name of the branch should inlude the ticket's number, the
ticket type, and a brief one-line synopsis of the purpose of the ticket.  eg:
``2298-feature-add-sort-by-controls-to-search-page``.  This allows the ticket
number to be esaily searchable through github's web interface.

Once work on the branch has been completed and it is ready to be merged into
master, make a pull request on github.  Another member of the CKAN team will
review the changes; and provide feedback through the github pull request page.
If the piece of work touches on an area of code `owned` by another team member,
then notify them of the changes by email.

Submitting Code Patches
-----------------------

See the wiki for instructions on `how to submit a patch`_ via GitHub or email.

.. _how to submit a patch: http://wiki.ckan.org/Submitting_a_code_patch

Releases
--------

See :doc:`release-cycle` for details on the release process.

Merging
-------

When merging a feature or bug branch into master:

- Use the ``--no-ff`` option in the ``git merge`` command
- Add an entry to the ``CHANGELOG`` file

The full postgresql test suite must pass before merging into master. ::

  nosetests --ckan --with-pylons=test-core.ini ckan

See :doc:`test` for more information on running tests, including running the
core extension tests.

Python Coding Standards
=======================

For python code, we follow `PEP 8`_, plus a few of our own rules.  The
important bits are laid out below, but if in doubt, refer to `PEP 8`_ and
common sense.

Layout and formatting
---------------------

- Don't use tabs.  Use 4 spaces.

- Maximum line length is 79 characters.

- Continuation lines should align vertically within the parentheses, or with
  a hanging indent.  See `PEP 8's Indent Section`_ for more details.

- Avoid extraneous whitespace.  See `PEP 8's Whitespace Section`_ for more details.

- Clean up formatting issues in master, not on a feature branch.  Unless of
  course you're changing that piece of code anyway.  This will help avoid
  spurious merge conflicts, and aid in reading pull requests.

- Use the single-quote character, ``'``, rather than the double-quote
  character, ``"``, for string literals.

.. _PEP 8: http://www.python.org/dev/peps/pep-0008/
.. _PEP 8's Indent Section: http://www.python.org/dev/peps/pep-0008/#indentation
.. _PEP 8's Whitespace Section: http://www.python.org/dev/peps/pep-0008/#whitespace-in-expressions-and-statements

Imports
-------

- Import whole modules, rather than using ``from foo import bar``.  It's ok
  to alias imported modules to make things more concise, ie this *is*
  acceptable: ::

    import foo.bar.baz as f

- Make all imports at the start of the file, after the module docstring.
  Imports should be grouped in the following order:

  1. Standard library imports
  2. Third-party imports
  3. CKAN imports

Logging
-------

- Keep messages short.

- Don't include object representations in the log message.  It **is** useful
  to include an domain model identifier where appropriate.

- Choose an appropriate log-level:

  +----------+--------------------------------------------------------------+
  | Level    | Description                                                  |
  +==========+==============================================================+
  | DEBUG    | Detailed information, of no interest when everything is      |
  |          | working well but invaluable when diagnosing problems.        |
  +----------+--------------------------------------------------------------+
  | INFO     | Affirmations that things are working as expected, e.g.       |
  |          | "service has started" or "indexing run complete". Often      |
  |          | ignored.                                                     |
  +----------+--------------------------------------------------------------+
  | WARNING  | There may be a problem in the near future, and this gives    |
  |          | advance warning of it. But the application is able to proceed|
  |          | normally.                                                    |
  +----------+--------------------------------------------------------------+
  | ERROR    | The application has been unable to proceed as expected, due  |
  |          | to the problem being logged.                                 |
  +----------+--------------------------------------------------------------+
  | CRITICAL | This is a serious error, and some kind of application        |
  |          | meltdown might be imminent.                                  |
  +----------+--------------------------------------------------------------+

  (`Source
  <http://plumberjack.blogspot.co.uk/2009/09/python-logging-101.html>`_)

i18n
----

To construct an internationalised string, use `str.format`_, giving
meaningful names to each replacement field.  For example: ::

  _(' ... {foo} ... {bar} ...').format(foo='foo-value', bar='bar-value')

.. _str.format: http://docs.python.org/library/stdtypes.html#str.format

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
``*stars for emphasis*`` or ````double-backticks for literal text````

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

Tools
-----

Running the `PEP 8 style guide checker`_ is good for checking adherence to `PEP
8`_ formatting.  As mentioned above, only perform style clean-ups on master to
help avoid spurious merge conflicts.

`PyLint`_ is a useful tool for analysing python source code for errors and signs of poor quality.

`pyflakes`_ is another useful tool for passive analysis of python source code.
There's also a `pyflakes vim plugin`_ which will highlight unused variables,
undeclared variables, syntax errors and unused imports.

.. _PEP 8 style guide checker: http://pypi.python.org/pypi/pep8
.. _PyLint: http://www.logilab.org/857
.. _pyflakes: http://pypi.python.org/pypi/pyflakes
.. _pyflakes vim plugin: http://www.vim.org/scripts/script.php?script_id=2441

CKAN Code Areas
===============

This section describes some guidelines for making changes in particular areas
of the codebase, as well as general concepts particular to CKAN.

General
-------

Some rules to adhere to when making changes to the codebase in general.

.. todo:: Is there anything to include in this 'General' section?

Domain Models
-------------

This section describes things to bear in mind when making changes to the domain
models.  For more information about CKAN's domain models, see
:doc:`domain-model`.

The structure of the CKAN data is described in the 'model'. This is in the code
at `ckan/model`.

Many of the domain objects are Revisioned and some are Stateful. These are
concepts introduced by `vdm`_.

.. _vdm: http://okfn.org/projects/vdm/
.. _sqlalchemy migrate: http://code.google.com/p/sqlalchemy-migrate SQLAlchemy Migrate

Migration
`````````
When edits are made to the model code, then before the code can be used on a
CKAN instance with existing data, the existing data has to be migrated. This is
achieved with a migration script.

CKAN currently uses to manage these scripts.  When you deploy new code to a
CKAN instance, as part of the process you run any required migration scripts
with: ::

 paster --plugin=ckan db upgrade --config={.ini file}

The scripts give their model version numbers in their filenames and are stored
in ``ckan/migration/versions/``.

The current version the database is migrated to is also stored in the database.
When you run the upgrade, as each migration script is run it prints to the
console something like ``11->12``. If no upgrade is required because it is up
to date, then nothing is printed.

Creating a new migration script
```````````````````````````````
A migration script should be checked into CKAN at the same time as the model
changes it is related to. Before pushing the changes, ensure the tests pass
when running against the migrated model, which requires the
``--ckan-migration`` setting.

To create a new migration script, create a python file in
``ckan/migration/versions/`` and name it with a prefix numbered one higher than
the previous one and some words describing the change.

You need to use the special engine provided by the SqlAlchemy Migrate. Here is
the standard header for your migrate script: ::

  from sqlalchemy import *
  from migrate import *

The migration operations go in the upgrade function: ::

  def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine

The following process should be followed when doing a migration.  This process
is here to make the process easier and to validate if any mistakes have been
made:

1. Get a dump of the database schema before you add your new migrate scripts. ::

     paster --plugin=ckan db clean --config={.ini file}
     paster --plugin=ckan db upgrade --config={.ini file}
     pg_dump -h host -s -f old.sql dbname

2. Get a dump of the database as you have specified it in the model. ::

     paster --plugin=ckan db clean --config={.ini file}

     #this makes the database as defined in the model
     paster --plugin=ckan db create-from-model -config={.ini file}
     pg_dump -h host -s -f new.sql dbname

3. Get agpdiff (apt-get it). It produces sql it thinks that you need to run on
   the database in order to get it to the updated schema. ::

     apgdiff old.sql new.sql > upgrade.diff

(or if you don't want to install java use http://apgdiff.startnet.biz/diff_online.php)

4. The upgrade.diff file created will have all the changes needed in sql.
   Delete the drop index lines as they are not created in the model.

5. Put the resulting sql in your migrate script, e.g. ::

     migrate_engine.execute('''update table .........; update table ....''')

6. Do a dump again, then a diff again to see if the the only thing left are drop index statements.

7. run nosetests with ``--ckan-migration`` flag.

It's that simple.  Well almost.

*  If you are doing any table/field renaming adding that to your new migrate
   script first and use this as a base for your diff (i.e add a migrate script
   with these renaming before 1). This way the resulting sql won't try to drop and
   recreate the field/table!

*  It sometimes drops the foreign key constraints in the wrong order causing an
   error so you may need to rearrange the order in the resulting upgrade.diff.

*  If you need to do any data transfer in the migrations then do it between the
   dropping of the constraints and adding of new ones.

*  May need to add some tests if you are doing data migrations.

An example of a script doing it this way is ``034_resource_group_table.py``.
This script copies the definitions of the original tables in order to do the
renaming the tables/fields.

In order to do some basic data migration testing extra assertions should be
added to the migration script.  Examples of this can also be found in
``034_resource_group_table.py`` for example.

This statement is run at the top of the migration script to get the count of
rows: ::

  package_count = migrate_engine.execute('''select count(*) from package''').first()[0]

And the following is run after to make sure that row count is the same: ::

  resource_group_after = migrate_engine.execute('''select count(*) from resource_group''').first()[0]
  assert resource_group_after == package_count

The Action Layer
----------------

When making changes to the action layer, found in the four modules
``ckan/logic/action/{create,delete,get,update}`` there are a few things to bear
in mind.

Server Errors
`````````````

When writing action layer code, bear in mind that the input provided in the
``data_dict`` may be user-provided.  This means that required fields should be
checked for existence and validity prior to use.  For example, code such as ::

  id = data_dict['id']

will raise a ``KeyError`` if the user hasn't provided an ``id`` field in their
data dict.  This results in a 500 error, and no message to explain what went
wrong.  The correct response by the action function would be to raise a
``ValidationError`` instead, as this will be caught and will provide the user
with a `bad request` response, alongside an error message explaining the issue.

To this end, there's a helper function, ``logic.get_or_bust()`` which can be
used to safely retrieve a value from a dict: ::

  id = _get_or_bust(data_dict, "id")

Function visibility
```````````````````

**All** publicly visible functions in the
``ckan.logic.action.{create,delete,get,update}`` namespaces will be exposed
through the :doc:`apiv3`.  **This includes functions imported** by those
modules, **as well as any helper functions** defined within those modules.  To
prevent inadvertent exposure of non-action functions through the action api,
care should be taken to:

1. Import modules correctly (see `Imports`_).  For example: ::

     import ckan.lib.search as search

     search.query_for(...)

2. Hide any locally defined helper functions: ::

     def _a_useful_helper_function(x, y, z):
        '''This function is not exposed because it is marked as private```
        return x+y+z

3. Bring imported convenience functions into the module namespace as private
   members: ::

     _get_or_bust = logic.get_or_bust

Documentation
`````````````

Please refer to `CKAN Action API Docstrings`_ for information about writing
docstrings for the action functions.  It is **very** important that action
functions are documented as they are not only consumed by CKAN developers but
by CKAN users.

Controllers
-----------

Guidelines when writing controller actions:

- Use ``get_action``, rather than calling the action directly; and rather than
  calling the action directly, as this allows extensions to overide the action's
  behaviour. ie use ::

    ckan.logic.get_action('group_activity_list_html')(...)

  Instead of ::

    ckan.logic.action.get.group_activity_list_html(...)

- Controllers have access to helper functions in ``ckan.lib.helpers``.  When
  developing for ckan core, only use the helper functions found in
  ``ckan.lib.helpers.__allowed_functions__`` because any instance may set the
  ``ckan.restrict_template_vars`` configuration value to ``True``.

.. todo:: Anything else for contrllers?

Templating
----------

Helper Functions
````````````````

Templates have access to a set of helper functions in ``ckan.lib.helpers``.
When developing for ckan core, only use the helper functions found in
``ckan.lib.helpers.__allowed_functions__`` because any instance may set the
``ckan.restrict_template_vars`` configuration value to ``True``.

.. todo:: Jinja2 templates

Testing
-------

- Functional tests which test the behaviour of the web user interface, and the
  APIs should be placed within ``ckan/tests/functional``.  These tests can be a
  lot slower to run that unit tests which don't access the database or solr.  So
  try to bear that in mind, and attempt to cover just what is neccessary, leaving
  what can be tested via unit-testing in unit-tests.

- ``nose.tools.assert_in`` and ``nose.tools.assert_not_in`` are only available
  in Python>=2.7.  So import them from ``ckan.tests``, which will provide
  alternatives if they're not available.

- the `mock`_ library can be used to create and interrogate mock objects.

See :doc:`test` for further information on testing in CKAN.

.. _mock: http://pypi.python.org/pypi/mock

Writing Extensions
------------------

Please see :doc:`writing-extensions` for information about writing ckan
extensions, including details on the API available to extensions.

Deprecation
-----------

- Anything that may be used by extensions (see :doc:`writing-extensions`) needs
  to maintain backward compatibility at call-site.  ie - template helper
  functions and functions defined in the plugins toolkit.

- The length of time of deprecation is evaluated on a function-by-function
  basis.  At minimum, a function should be marked as deprecated during a point
  release.

- To mark a helper function, use the ``deprecated`` decorator found in
  ``ckan.lib.maintain`` eg: ::

    
    @deprecated()
    def facet_items(*args, **kwargs):
        """
        DEPRECATED: Use the new facet data structure, and `unselected_facet_items()`
        """
        # rest of function definition.

Javascript Coding Standards
===========================

Formatting
----------

.. _OKFN Coding Standards: http://wiki.okfn.org/Coding_Standards#Javascript
.. _idiomatic.js: https://github.com/rwldrn/idiomatic.js/
.. _Douglas Crockford's: http://javascript.crockford.com/code.html

All JavaScript documents must use **two spaces** for indentation and files
should have no trailing whitespace. This is contrary to the `OKFN Coding
Standards`_ but matches what's in use in the current code base.

Coding style must follow the `idiomatic.js`_ style but with the following
exceptions.

.. note:: Idiomatic is heavily based upon `Douglas Crockford's`_ style
          guide which is recommended by the `OKFN Coding Standards`_.

White Space
```````````

Two spaces must be used for indentation at all times. Unlike in idiomatic
whitespace must not be used _inside_ parentheses between the parentheses
and their Contents. ::

    // BAD: Too much whitespace.
    function getUrl( full ) {
      var url = '/styleguide/javascript/';
      if ( full ) {
        url = 'http://okfn.github.com/ckan' + url;
      }
      return url;
    }

    // GOOD:
    function getUrl(full) {
      var url = '/styleguide/javascript/';
      if (full) {
        url = 'http://okfn.github.com/ckan' + url;
      }
      return url;
    }

.. note:: See section 2.D.1.1 of idiomatic for more examples of this syntax.

Quotes
``````

Single quotes should be used everywhere unless writing JSON or the string
contains them. This makes it easier to create strings containing HTML. ::

    jQuery('<div id="my-div" />').appendTo('body');

Object properties need not be quoted unless required by the interpreter. ::

    var object = {
      name: 'bill',
      'class': 'user-name'
    };

Variable declarations
`````````````````````

One ``var`` statement must be used per variable assignment. These must be
declared at the top of the function in which they are being used. ::

    // GOOD:
    var good = "string";
    var alsoGood = "another;

    // GOOD:
    var good = "string";
    var okay = [
      "hmm", "a bit", "better"
    ];

    // BAD:
    var good = "string",
        iffy = [
      "hmm", "not", "great"
    ];

Declare variables at the top of the function in which they are first used. This
avoids issues with variable hoisting. If a variable is not assigned a value
until later in the function then it it okay to define more than one per
statement. ::

    // BAD: contrived example.
    function lowercaseNames(names) {
      var names = [];

      for (var index = 0, length = names.length; index < length; index += 1) {
        var name = names[index];
        names.push(name.toLowerCase());
      }

      var sorted = names.sort();
      return sorted;
    }

    // GOOD:
    function lowercaseNames(names) {
      var names = [];
      var index, sorted, name;

      for (index = 0, length = names.length; index < length; index += 1) {
        name = names[index];
        names.push(names[index].toLowerCase());
      }

      sorted = names.sort();
      return sorted;
    }

Naming
------

All properties, functions and methods must use lowercase camelCase: ::

    var myUsername = 'bill';
    var methods = {
      getSomething: function () {}
    };

Constructor functions must use uppercase CamelCase: ::

    function DatasetSearchView() {
    }

Constants must be uppercase with spaces delimited by underscores: ::

    var env = {
      PRODUCTION:  'production',
      DEVELOPMENT: 'development',
      TESTING:     'testing'
    };

Event handlers and callback functions should be prefixed with "on": ::

    function onDownloadClick(event) {}

    jQuery('.download').click(onDownloadClick);

Boolean variables or methods returning boolean functions should prefix
the variable name with "is": ::

    function isAdmin() {}

    var canEdit = isUser() && isAdmin();


.. note:: Alternatives are "has", "can" and "should" if they make more sense

Private methods should be prefixed with an underscore: ::

    View.extend({
      "click": "_onClick",
      _onClick: function (event) {
      }
    });

Functions should be declared as named functions rather than assigning an
anonymous function to a variable. ::

    // GOOD:
    function getName() {
    }

    // BAD:
    var getName = function () {
    };

Named functions are generally easier to debug as they appear named in the
debugger.

Comments
--------

Comments should be used to explain anything that may be unclear when you return
to it in six months time. Single line comments should be used for all inline
comments that do not form part of the documentation. ::

    // Export the function to either the exports or global object depending
    // on the current environment. This can be either an AMD module, CommonJS
    // module or a browser.
    if (typeof module.define === 'function' && module.define.amd) {
      module.define('broadcast', function () {
        return Broadcast;
      });
    } else if (module.exports) {
      module.exports = Broadcast;
    } else {
      module.Broadcast = Broadcast;
    }

File Structure
--------------

All public JavaScript files should be contained within a _javascript_ directory
within the _public_ directory and files should be structured accordingly. ::

    lib/
      main.js
      utils.js
      components/
    vendor/
      jquery.js
      jquery.plugin.js
      underscore.js
    templates/
    test/
      index.html
      spec/
        main-spec.js
        utils-spec.js
      vendor/
        mocha.js
        mocha.css
        chai.js

All files and directories should be lowercase with hyphens used to separate words.

lib
  Should contain all application files. These can be structured appropriately.
  It is recommended that *main.js* be used as the bootstrap filename that sets
  up the page.

vendor
  Should contain all external dependencies. These should not contain
  version numbers in the filename. This information should be available in
  the header comment of the file. Library plugins should be prefixed with the
  library name. eg the hover intent jQuery plugin would have the filename
  *jquery.hover-intent.js*.

templates
  Should be stored in a seperate directory and have the .html
  extension.
test
  Contains the test runner *index.html*. *vendor* contains all test
  dependencies and libraries. *spec* contains the actual test files. Each
  test file should be the filename with *-spec* appended.

JSHint
------

All JavaScript should pass `JSHint`_ before being committed. This can
be installed using ``npm`` (which is bundled with `node`_) by running: ::

    $ npm -g install jshint

Each project should include a jshint.json file with appropriate configuration
options for the tool. Most text editors can also be configured to read from
this file.

.. _node: http://nodejs.org
.. _jshint: http://www.jshint.com

Documentation
-------------

*TODO*

Testing
-------

*TODO*

Best Practices
--------------

Forms
`````

All forms should work without JavaScript enabled. This means that they must
submit ``application/x-www-form-urlencoded`` data to the server and receive an appropriate
response. The server should check for the ``X-Requested-With: XMLHTTPRequest``
header to determine if the request is an ajax one. If so it can return an
appropriate format, otherwise it should issue a 303 redirect.

The one exception to this rule is if a form or button is injected with
JavaScript after the page has loaded. It's then not part of the HTML document
and can submit any data format it pleases.

Ajax
````````

Ajax requests can be used to improve the experience of submitting forms and
other actions that require server interactions. Nearly all requests will
go through the following states.

1.  User clicks button.
2.  JavaScript intercepts the click and disables the button (add ``disabled``
    attr).
3.  A loading indicator is displayed (add class ``.loading`` to button).
4.  The request is made to the server.
5.  a) On success the interface is updated.
    b) On error a message is displayed to the user if there is no other way to
       resolve the issue.
6.  The loading indicator is removed.
7.  The button is re-enabled.

Here's a possible example for submitting a search form using jQuery. ::

    jQuery('#search-form').submit(function (event) {
      var form = $(this);
      var button = form.find('[type=submit]');

      // Prevent the browser submitting the form.
      event.preventDefault();

      button.prop('disabled', true).addClass('loading');

      jQuery.ajax({
        type: this.method,
        data: form.serialize(),
        success: function (results) {
          updatePageWithResults(results);
        },
        error: function () {
          showSearchError('Sorry we were unable to complete this search');
        },
        complete: function () {
          button.prop('disabled', false).removeClass('loading');
        }
      });
    });

This covers possible issues that might arise from submitting the form as well
as providing the user with adequate feedback that the page is doing something.
Disabling the button prevents the form being submitted twice and the error
feedback should hopefully offer a solution for the error that occurred.

Event Handlers
``````````````

When using event handlers to listen for browser events it's a common
requirement to want to cancel the default browser action. This should be
done by calling the ``event.preventDefault()`` method: ::

    jQuery('button').click(function (event) {
      event.preventDefault();
    });

It is also possible to return ``false`` from the callback function. Avoid doing
this as it also calls the ``event.stopPropagation()`` method which prevents the
event from bubbling up the DOM tree. This prevents other handlers listening
for the same event. For example an analytics click handler attached to the
``<body>`` element.

Also jQuery (1.7+) now provides the `.on()`_ and `.off()`_  methods as
alternatives to ``.bind()``, ``.unbind()``, ``.delegate()`` and
``.undelegate()`` and they should be preferred for all tasks.

.. _.on(): http://api.jquery.com/on/
.. _.off(): http://api.jquery.com/off/

Closures
````````

*TODO*

Templating
``````````

*TODO*

Resources
---------

*TODO*

HTML Coding Standards
=====================

Formatting
----------

All HTML documents must use **two spaces** for indentation and there should be
no trailing whitespace. XHTML syntax must be used (this is more a Genshi
requirement) and all attributes must use double quotes around attributes. ::

    <!-- XHTML boolean attributes must still have values and self closing tags must have a closing / -->
    <video autoplay="autoplay" poster="poster_image.jpg">
      <source src="foo.ogg" type="video/ogg" />
    </video>

HTML5 elements should be used where appropriate reserving ``<div>`` and ``<span>``
elements for situations where there is no semantic value (such as wrapping
elements to provide styling hooks).

Doctype and layout
------------------

All documents must be using the HTML5 doctype and the ``<html>`` element should
have a ``"lang"`` attribute. The ``<head>`` should also at a minimum include
``"viewport"`` and ``"charset"`` meta tags. ::

    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Example Site</title>
      </head>
      <body></body>
    </html>

Forms
-----

Form fields must always include a ``<label>`` element with a ``"for"`` attribute
matching the ``"id"`` on the input. This helps accessibility by focusing the
input when the label is clicked, it also helps screen readers match labels to
their respective inputs. ::

    <label for="field-email">email</label>
    <input type="email" id="field-email" name="email" value="" />

Each ``<input>`` should have an ``"id"`` that is unique to the page. It does not
have to match the ``"name"`` attribute.

Forms should take advantage of the new HTML5 input types where they make sense
to do so, placeholder attributes should also be included where relevant.
Including these can provided enhancements in browsers that support them such as
tailored inputs and keyboards. ::

    <div>
      <label for="field-email">Email</label>
      <input type="email" id="field-email" name="email" value="name@example.com" />
    </div>
    <div>
      <label for="field-phone">Phone</label>
      <input type="phone" id="field-phone" name="phone" value="" placeholder="+44 077 12345 678" />
    </div>
    <div>
      <label for="field-url">Homepage</label>
      <input type="url" id="field-url" name="url" value="" placeholder="http://example.com" />
    </div>

Wufoo provides an `excellent reference`_ for these attributes.

.. _excellent reference: http://wufoo.com/html5/

Including meta data
-------------------

Classes should ideally only be used as styling hooks. If you need to include
additional data in the html document, for example to pass data to JavaScript,
then the HTML5 ``data-`` attributes should be used. ::

    <a class="btn" data-format="csv">Download CSV</a>

These can then be accessed easily via jQuery using the ``.data()`` method. ::

    jQuery('.btn').data('format'); //=> "csv"

    // Get the contents of all data attributes.
    jQuery('.btn').data(); => {format: "csv"}

One thing to note is that the JavaScript API for datasets will convert all
attribute names into camelCase. So ``"data-file-format"`` will become ``fileFormat``.

For example: ::

    <a class="btn" data-file-format="csv">Download CSV</a>

Will become: ::

    jQuery('.btn').data('fileFormat'); //=> "csv"
    jQuery('.btn').data(); => {fileFormat: "csv"}

Targeting Internet Explorer
---------------------------

Targeting lower versions of Internet Explorer (IE), those below version 9,
should be handled by the stylesheets. Small fixes should be provided inline
using the ``.ie`` specific class names. Larger fixes may require a separate
stylesheet but try to avoid this if at all possible.

Adding IE specific classes: ::

    <!doctype html>
    <!--[if lt IE 7]> <html lang="en" class="ie ie6"> <![endif]-->
    <!--[if IE 7]>    <html lang="en" class="ie ie7"> <![endif]-->
    <!--[if IE 8]>    <html lang="en" class="ie ie8"> <![endif]-->
    <!--[if gt IE 8]><!--> <html lang="en"> <!--<![endif]-->

.. note:: Only add lines for classes that are actually being used.

These can then be used within the CSS: ::

    .clear:before,
    .clear:after {
        content: "";
        display: table;
    }

    .clear:after {
        clear: both;
    }

    .ie7 .clear {
        zoom: 1; /* For IE 6/7 (trigger hasLayout) */
    }

i18n
----

Don't include line breaks within ``<p>`` blocks.  ie do this: ::

  <p>Blah foo blah</p>
  <p>New paragraph, blah</p>

And **not**: ::

  <p>Blah foo blah
     New paragraph, blah</p>

CSS Coding Standards
====================

Formatting
----------

All CSS documents must use **two spaces** for indentation and files should have
no trailing whitespace. Other formatting rules:

- Use soft-tabs with a two space indent.
- Use double quotes.
- Use shorthand notation where possible.
- Put spaces after ``:`` in property declarations.
- Put spaces before ``{`` in rule declarations.
- Use hex color codes ``#000`` unless using ``rgba()``.
- Always provide fallback properties for older browsers.
- Use one line per property declaration.
- Always follow a rule with one line of whitespace.
- Always quote ``url()`` and ``@import()`` contents.
- Do not indent blocks.

For example: ::

    .media {
      overflow: hidden;
      color: #fff;
      background-color: #000; /* Fallback value */
      background-image: linear-gradient(black, grey);
    }

    .media .img {
      float: left;
      border: 1px solid #ccc;
    }

    .media .img img {
      display: block;
    }

    .media .content {
      background: #fff url("../images/media-background.png") no-repeat;
    }

Naming
------

All ids, classes and attributes must be lowercase with hyphens used for
separation. ::

    /* GOOD */
    .dataset-list {}

    /* BAD */
    .datasetlist {}
    .datasetList {}
    .dataset_list {}

Comments
--------

Comments should be used liberally to explain anything that may be unclear at
first glance, especially IE workarounds or hacks. ::

    .prose p {
      font-size: 1.1666em /* 14px / 12px */;
    }

    .ie7 .search-form {
      /*
        Force the item to have layout in IE7 by setting display to block.
        See: http://reference.sitepoint.com/css/haslayout
      */
      display: inline-block;
    }

Modularity & Specificity
------------------------

Try keep all selectors loosely grouped into modules where possible and avoid
having too many selectors in one declaration to make them easy to override. ::

    /* Avoid */
    ul#dataset-list {}
    ul#dataset-list li {}
    ul#dataset-list li p a.download {}

Instead here we would create a dataset "module" and styling the item outside of
the container allows you to use it on it's own e.g. on a dataset page: ::

    .dataset-list {}
    .dataset-list-item {}
    .dataset-list-item .download {}

In the same vein use classes make the styles more robust, especially where the
HTML may change. For example when styling social links: ::

    <ul class="social">
      <li><a href="">Twitter</a></li>
      <li><a href="">Facebook</a></li>
      <li><a href="">LinkedIn</a></li>
    </ul>

You may use pseudo selectors to keep the HTML clean: ::

    .social li:nth-child(1) a {
      background-image: url(twitter.png);
    }

    .social li:nth-child(2) a {
      background-image: url(facebook.png);
    }

    .social li:nth-child(3) a {
      background-image: url(linked-in.png);
    }

However this will break any time the HTML changes for example if an item is
added or removed. Instead we can use class names to ensure the icons always
match the elements (Also you'd probably sprite the image :). ::

    .social .twitter {
      background-image: url(twitter.png);
    }

    .social .facebook {
      background-image: url(facebook.png);
    }

    .social .linked-in {
      background-image: url(linked-in.png);
    }

Avoid using tag names in selectors as this prevents re-use in other contexts. ::

    /* Cannot use this class on an <ol> or <div> element */
    ul.dataset-item {}

Also ids should not be used in selectors as it makes it far too difficult to
override later in the cascade. ::

    /* Cannot override this button style without including an id */
    .btn#download {}

Resources
---------

- `OOCSS`_
- `An Introduction to Object Orientated CSS`_
- `SMACSS`_
- `CSS for Grown Ups`_ (`slides`_)

.. note:: These resources are more related to structuring CSS for large projects rather
          than actual how-to style guides.

.. _OOCSS: www.stubbornella.org/content/2011/04/28/our-best-practices-are-killing-us/
.. _An Introduction to Object Orientated CSS: coding.smashingmagazine.com/2011/12/12/an-introduction-to-object-oriented-css-oocss/
.. _SMACSS: smacss.com
.. _CSS for Grown Ups: schedule.sxsw.com/2012/events/event_IAP9410
.. _slides: speakerdeck.com/u/andyhume/p/css-for-grown-ups-maturing-best-practises

