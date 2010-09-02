Form Methods
~~~~~~~~~~~~

Here are the methods of the Form API.

+-------------------------------+--------+-------------------------------+-------------------------+
| Resource                      | Method | Request                       | Response                |
+===============================+========+===============================+=========================+ 
| Package Edit Form             | GET    |                               | Package-Edit-Form       | 
+-------------------------------+--------+-------------------------------+-------------------------+
| Package Edit Form             | PUT    | Package-Edit-Form-Submission  |                         | 
+-------------------------------+--------+-------------------------------+-------------------------+

* The form responses are used by clients within their HTML pages.

* PUT operations may instead use the HTTP POST method.

* Successful form submission requests will return status code of 200 with an empty response.

* Unsuccessful form submission requests will return status code of 400 with an error form response. The error form response are used instead of the original form response to display errorful submissions to users.



