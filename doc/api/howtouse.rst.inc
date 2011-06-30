Using the API
-------------

To send request data, create a simple data structure, then convert it to a JSON string, then percent-encode the JSON string, then send it as the request body. Response data will be in the response body.

If using curl, the default Content-Type header will be ``application/x-www-form-urlencoded`` and the JSON string gets sent as a single parameter key. However Javascript libraries tend to set Content-Type to be ``application/json`` and the JSON string is the body to the POST. The latter content became acceptable from CKAN version 1.4.2.

Notes:

 * When you update an object, fields that you don't supply will remain as they were before.

 * To delete an 'extra' key-value pair, supply the key with a None value.

 * When you read a package then some additional information is supplied that cannot current be adjusted throught the CKAN API. This includes info on Package Relationship ('relationships'), Group membership ('groups'), ratings ('ratings_average' and 'ratings_count') and Package ID ('id'). This is purely a convenience for clients, and only forms part of the Package on GET.

