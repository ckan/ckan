.. index:: API_REF
.. _api-ref:

==================
CKAN API Reference
==================

TODO: Explain how to call API functions. In the source code, all of these functions take two params context and data_dict, but the params documented in the docstrings are actually the keys that should be in the data_dict. When you post a json dict to an API endpoint, the json dict becomes the data_dict. Give an example with curl.

Also explain how the returns values of the functions end up in the json dict that is returned.

.. automodule:: ckan.logic.action.get
   :members:

.. automodule:: ckan.logic.action.create
   :members:

.. automodule:: ckan.logic.action.update
   :members:

.. automodule:: ckan.logic.action.delete
   :members:
