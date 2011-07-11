JSONP formatted responses
-------------------------

To cater for scripts from other sites that wish to access the API, the data can be returned in JSONP format, where the JSON data is 'padded' with a function call. The function is named in the 'callback' parameter.

Example normal request::

 GET /api/rest/package/pollution_stats
 returns: {"name": "pollution_stats", ... }

but now with the callback parameter::

 GET /api/rest/package/pollution_stats?callback=jsoncallback
 returns: jsoncallback({"name": "pollution_stats", ... });

This parameter can apply to all GET requests in the API.

