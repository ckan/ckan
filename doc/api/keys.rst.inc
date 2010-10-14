API Keys
--------

You will need to supply an API Key for certain requests to the CKAN API:

* For any action which makes a change to a resource (i.e. all POST methods on register resources, and PUT/POST methods on entity resources).

* If the particular resource's authorization set-up is not open to 
  visitors for the action.

To obtain your API key:

1. Log-in to the particular CKAN website: /user/login

2. The user page has a link to the API Key: /user/apikey

The key should be passed in the API request header:

================= =====
Header            Example value
================= =====
Authorization     fde34a3c-b716-4c39-8dc4-881ba115c6d4
================= =====

If requests that are required to be authorized are not sent with a 
valid Authorization header, for example the user associated with the 
key is not authorized for the operation, or the header is somehow malformed,
then the requested operation will not be carried out and the CKAN API will
respond with status code 403.

For more information about HTTP Authorization header, please refer to section
14.8 of `RFC 2616 <http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.8>`_.



