'''**All lib functions should have tests**.

.. todo::

   Write the tests for one ``ckan.lib`` module, figuring out the best way
   to write lib tests. Then fill in this guidelines section, using the first


   We probably want to make these unit tests rather than high-level tests and
   mock out ``ckan.model``, so the tests are really fast and simple.

   Note that some things in lib are particularly important, e.g. the functions
   in :py:mod:`ckan.lib.helpers` are exported for templates (including
   extensions) to use, so all of these functions should really have tests and
   docstrings. It's probably worth focusing on these modules first.

'''
