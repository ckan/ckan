================
Form Integration
================

CKAN allows you to integrate its Edit Dataset and New Dataset forms into an external front-end. To that end, CKAN also provides a simple way to redirect these forms back to the external front-end upon submission. 

Redirecting CKAN Forms
======================

It is obviously simple enough for an external front-end to link to CKAN's Edit Dataset and New Dataset forms, but once the forms are submitted, it would be desirable to redirect the user back to the external front-end, rather than CKAN's dataset read page. 

This is achieved with a parameter to the CKAN URL. The 'return URL' can be specified in two places:

 1. Passed as a URL-encoded value with the parameter ``return_to`` in the link to CKAN's form page.

 2. Specified in the CKAN config keys :ref:`package_new_return_url` and :ref:`package_edit_return_url`.

(If the 'return URL' is supplied in both places, then the first takes precedence.)

Since the 'return URL' may need to include the dataset name, which could be changed by the user, CKAN replaces a known placeholder ``<NAME>`` with this value on redirect.

.. note:: Note that the downside of specifying the 'return URL' in the CKAN config is that the CKAN web interface becomes less usable on its own, since the user is hampered by the redirects to the external interface.

Example
-------

An external front-end displays a dataset 'ontariolandcoverv100' here:: 

  http://datadotgc.ca/dataset/ontariolandcoverv100

It displays a link to edit this dataset using CKAN's form, which without the redirect would be::

  http://ca.ckan.net/dataset/edit/ontariolandoverv100

At first, it may seem that the return link should be ``http://datadotgc.ca/dataset/ontariolandcoverv100``. But when the user edits this dataset, the name may change. So the return link needs to be::

  http://datadotgc.ca/dataset/<NAME>

And this is URL-encoded to become::

  http%3A%2F%2Fdatadotgc.ca%2Fdataset%2F%3CNAME%3E

So, in summary, the edit link becomes:: 

  http://ca.ckan.net/dataset/edit/ontariolandoverv100?return_to=http%3A%2F%2Fdatadotgc.ca%2Fdataset%2F%3CNAME%3E

During editing the dataset, the user changes the dataset name to `canadalandcover`, presses 'preview' and finally 'commit'. The user is now redirected back to the external front-end at:: 

  http://datadotgc.ca/dataset/canadalandcover

The same functionality could be achieved by this line in the config file (``ca.ckan.net.ini``)::

 ...

 [app:main]
 package_edit_return_url = http://datadotgc.ca/dataset/<NAME>

 ...
