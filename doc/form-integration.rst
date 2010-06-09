================
Form integration
================

CKAN provides facility for integrating the package editing forms into another front end

Form completion redirect
========================

It is simple enough for the external front end to link to CKAN's package creation or edit pages, but once the form is submitted the user needs to be redirected back to the external front end, instead of CKAN's package read page. This is achieved with a parameter to the CKAN URL.

The 'return URL' is passed URL encoded as a parameter "return_to" to CKAN's form page. Since the 'return URL' may need to include the package name, which could be set in the form, CKAN replaces a known placeholder "<NAME>" with this value on redirect.

Example
-------

An external front end displays a package 'ontariolandcoverv100' here:: 

  http://datadotgc.ca/dataset/ontariolandcoverv100

It displays a link to edit this package using CKAN's form, which without the redirect would be::

  http://ca.ckan.net/package/edit/ontariolandoverv100

On first thought, the return link is::

  http://datadotgc.ca/dataset/ontariolandcoverv100

But when the user edit's this package, the name may change. So the return link needs to be::

  http://datadotgc.ca/dataset/<NAME>

This is URL encoded to be::

  http%3A%2F%2Fdatadotgc.ca%2Fdataset%2F%3CNAME%3E

So the edit link becomes:: 

  http://ca.ckan.net/package/edit/ontariolandoverv100?return_to=http%3A%2F%2Fdatadotgc.ca%2Fdataset%2F%3CNAME%3E

During editing the package, the user changes the name to `canadalandcover`, presses 'preview' and finally 'commit'. The user is now redirected back to the external front end at:: 

  http://datadotgc.ca/dataset/canadalandcover
