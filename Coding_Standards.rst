CKAN Coding Standards
=====================

Docstring Standards
-------------------

We want CKAN's docstrings to be clear and easy to read for programmers who are
smart and competent but who may not know a lot of CKAN-related technical
jargon and whose first language may not be English. We also want it to be easy
to maintain the docstrings and keep them up to date with the actual behaviour
of the code as it changes over time. So:

- Keep docstrings short, describe only what's necessary and no more
- Keep docstrings simple, use plain English, try not to use a long word
  where a short one will do, and always cut out a word if it's possible to do
  so
- Avoid repetition

PEP 257
```````

Generally, follow `PEP 257`_. For example:

- All modules and all functions, classes and public methods exported by a
  module should have docstrings. Packages may also have docstrings, in the
  module docstring of the ``__init__.py`` file.

A function's docstring should:

- Summarize the function's behaviour
- Document its arguments, return value(s), side effects and exceptions raised
- Document any restrictions on when the function can be called (e.g. many of
  CKAN's API functions require some authorization)
- Start with a one-line summary of the function's effect, ending with a period,
  that gives the function's effect as a command, e.g.  "Do X this and return
  Y", not as a description (e.g. don't write "Returns the pathname ...")
- If necessary followed by a blank line then a longer description
- The summary and description should not reiterate the arguments of the
  function as these can be seen from the header (but they should mention the
  return type which is not in the header)

.. _PEP 257: http://www.python.org/dev/peps/pep-0257/

CKAN docstrings deviate from PEP 257 in a couple of ways:

- We use '''triple single quotes''' around docstrings, not """triple double
  quotes""" (put triple single quotes around one-line docstrings as well as
  multi-line ones, it makes them easier to expand later)
- We use Sphinx directives for documenting parameters, exceptions and return
  values

Sphinx
``````

Use `Sphinx directives`_ for documenting the parameters, exceptions and returns
of functions:

- Use :param and :type to describe each parameter
- Use :returns and :rtype to describe each return
  (it's not necessary to include a :returns: directive if this would just
  repeat the first-line summary of the function, you can just give an :rtype:
  instead)
- Use :raises to describe each exception raised
- Give an example value for each param

Example:

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

The phrases that follow :param foo:, :type foo:, or :returns: should not start
with capital letters or end with full stops. These should be short phrases and
not full sentences. If more detail is required put it in the function
description instead.

Indicate optional arguments by ending their :param directives with (optional)
in brackets. Where relevant also indicate the default value:
(optional, default: 5). It's also helpful to list all required parameters
before optional ones.

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

.. _Autodoc: http://sphinx.pocoo.org/ext/autodoc.html

'Dataset' vs 'Package'
``````````````````````

CKAN datasets used to be called packages and the old name still appears in the
source, e.g. in function names like package_list(). When documenting functions
like this write dataset not package, but the first time you do this put package
after it in brackets to avoid any confusion, e.g.

::

    def package_show(context, data_dict):
        '''Return the metadata of a dataset (package) and its resources.
