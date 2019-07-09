=====================
CKAN Python 2/3 Guide
=====================

This section documents the requirements for porting existing CKAN code for Python 3 support, and for creating new code that supports both Python 2 and Python 3.

----------
User story
----------

As a developer working on CKAN or CKAN Extensions, I want a clear guide, for writing code compatible with Python 2 and Python 3, so my code is consistent with common practice around CKAN, using a common set of tools.

---------
Use cases
---------

- Contributing Python 2/3 compatible code in CKAN Core
- Contributing Python 2/3 compatible code in a CKAN Extension
- Starting a new CKAN Extension with Python 2/3 compatibility

--------
Python 3
--------

From CKAN 2.9, CKAN will officially support Python 2 (≥ 2.6) and Python 3 (≥ 3.6).

-----
Flask
-----

CKAN provides Python 3 support by removing the underlying Pylons web framework, which is only compatible with Python 2, and integrating Flask as the web framework, which is compatible with Python 2 and Python 3. Flask is a very popular framework for writing web applications in Python; read more about Flask_.

--------
Approach
--------

CKAN provides support for both Python 2 and Python 3 using a compatible source approach. This enables us to continue supporting Python 2 in the current transitional period, and gracefully upgrade to a Python 3 only codebase in future versions of CKAN (from CKAN 3.0 onwards).

----
Tips
----

Future imports
##############

Import the following at the top of all modules::

  from __future__ import absolute_import
  from __future__ import division
  from __future__ import print_function
  from __future__ import unicode_literals

String handling
###############

- Remove any ``u`` prefixes before unicode strings in existing Python 2 code.
- Add a ``b`` prefix for any bytestrings
- Review code to ensure only unicode strings are exposed as part of the public interfaces of the codebase, which will make string handling more consistent.
  
Ensure you read the references below for further background information on all these tips.

Exception handling
##################

Python-Future provides a clean interface for exception handling compatibility::

  from future.utils import raise_
  traceback = sys.exc_info()[2]
  raise_(ValueError, "dodgy value", traceback)

Iterating over dicts
####################

Python-Future provides a clean interface for iterating over dicts (and for creating custom iterators - see the docs)::
  from builtins import dict
  from future.utils import listvalues
  from future.utils import itervalues
  from future.utils import listitems
  from future.utils import iteritems
  

  heights = dict(Fred=175, Anne=166, Joe=192)

  # value lists
  valuelist = listvalues(heights)
  valuelist = list(itervalues(heights))

  # item lists
  itemlist = listitems(heights)
  itemlist = list(iteritems(heights))

Flask-based API for extensions
##############################

TODO

-------
Tooling
-------

We recommend the use of the `Python-Future`_ library to provide a clean abstraction over the differences between Python 2 and Python 3. `Six`_ is another library that is acceptable, and commonly used. See here_ for an explanation of the differences between Python-Future and Six.

----------
References
----------

- `The official guide to porting Python 2 code to Python 3`_
- `Python 2-3 Cheat Sheet`_
- `Python-Future`_
- `Six`_

.. _Flask: http://flask.pocoo.org
.. _The official guide to porting Python 2 code to Python 3: https://docs.python.org/3/howto/pyporting.html#pyporting-howto
.. _Python 2-3 Cheat Sheet: https://python-future.org/compatible_idioms.html
.. _Python-Future: https://six.readthedocs.io
.. _Six: https://python-future.org
.. _here: https://python-future.org/faq.html#what-is-the-relationship-between-future-and-six
