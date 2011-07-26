Using the API
-------------

To send request data, create a simple data structure, then convert it to a JSON string, then percent-encode the JSON string, then send it as the request body. Response data will be in the response body.

Notes:

 * When you update an object, fields that you don't supply will remain as they were before.

 * To delete an 'extra' key-value pair, supply the key with a None value.

 * When you read a package then some additional information is supplied that cannot current be adjusted throught the CKAN API. This includes info on Package Relationship ('relationships'), Group membership ('groups'), ratings ('ratings_average' and 'ratings_count') and Package ID ('id'). This is purely a convenience for clients, and only forms part of the Package on GET.

