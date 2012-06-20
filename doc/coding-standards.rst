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

Merging
-------

When merging a feature or bug branch into master:

- Use the ``--no-ff`` option in the ``git merge`` command
- Add an entry to the ``CHANGELOG`` file

Frontend Coding Standards
=========================

Javavscript
-----------

Formatting
``````````

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
...........

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
......

Single quotes should be used everywhere unless writing JSON or the string
contains them. This makes it easier to create strings containing HTML. ::

    jQuery('<div id="my-div" />').appendTo('body');

Object properties need not be quoted unless required by the interpreter. ::

    var object = {
      name: 'bill',
      'class': 'user-name'
    };

Variable declarations
.....................

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
``````

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
````````

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
``````````````

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
``````

All JavaScript should pass `JSHint`_ before being committed. This can
be installed using `npm` (which is bundled with `node`_) by running: ::

    $ npm -g install jshint

Each project should include a jshint.json file with appropriate configuration
options for the tool. Most text editors can also be configured to read from
this file.

.. _node: http://nodejs.org
.. _jshint: http://www.jshint.com

Documentation
`````````````

_TODO_

Testing
```````

_TODO_

Best Practices
``````````````

Forms
.....

All forms should work without JavaScript enabled. This means that they must
submit `application/x-www-form-urlencoded` data to the server and receive an appropriate
response. The server should check for the `X-Requested-With: XMLHTTPRequest`
header to determine if the request is an ajax one. If so it can return an
appropriate format, otherwise it should issue a 303 redirect.

The one exception to this rule is if a form or button is injected with
JavaScript after the page has loaded. It's then not part of the HTML document
and can submit any data format it pleases.

Ajax
....

Ajax requests can be used to improve the experience of submitting forms and
other actions that require server interactions. Nearly all requests will
go through the following states.

1.  User clicks button.
2.  JavaScript intercepts the click and disables the button (add `disabled`
    attr).
3.  A loading indicator is displayed (add class `.loading` to button).
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
..............

When using event handlers to listen for browser events it's a common
requirement to want to cancel the default browser action. This should be
done by calling the `event.preventDefault()` method: ::

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
........

_TODO_

Templating
..........

_TODO_

Resources
`````````

_TODO_

{:js: data-code="js"}

- i18n

  - In html, don't include line breaks within ``<p>`` blocks.  ie do this: ::

      <p>Blah foo blah</p>
      <p>New paragraph, blah</p>

    And **not**: ::

      <p>Blah foo blah
         New paragraph, blah</p>

http://aron.github.com/ckan-style/styleguide/

Backend Coding Standards
========================

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

