Form Methods
~~~~~~~~~~~~

Here are the methods of the Form API.

+-------------------------------+--------+-------------------------------------+---------------------------+
| Resource                      | Method | Request                             | Response                  |
+===============================+========+=====================================+===========================+ 
| Package Create Form           | GET    |                                     | Package-Create-Form       | 
+-------------------------------+--------+-------------------------------------+---------------------------+
| Package Create Form           | PUT    | Package-Create-Form-Submission      |                           | 
+-------------------------------+--------+-------------------------------------+---------------------------+
| Package Edit Form             | GET    |                                     | Package-Edit-Form         | 
+-------------------------------+--------+-------------------------------------+---------------------------+
| Package Edit Form             | PUT    | Package-Edit-Form-Submission        |                           | 
+-------------------------------+--------+-------------------------------------+---------------------------+
| HarvestSource Create Form     | GET    |                                     | HarvestSource-Create-Form | 
+-------------------------------+--------+-------------------------------------+---------------------------+
| HarvestSource Create Form     | PUT    | HarvestSource-Create-Form-Submission|                           | 
+-------------------------------+--------+-------------------------------------+---------------------------+

* The form responses are used by clients within their HTML pages.

* PUT operations may instead use the HTTP POST method.

* Successful create form submission requests will return status code of 201 with a Location header contain a locator for the new resource.

* Successful edit form submission requests will return status code of 200.

* Unsuccessful form submission requests will return status code of 400 with an error form response. The error form response are used instead of the original form response to display errorful submissions to users.


