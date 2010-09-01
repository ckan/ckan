Form Formats
~~~~~~~~~~~~~~~~~

Here are the data formats for the Form API.

+--------------------------------+---------------------------------------------------------------------------+
| Name                           | Format                                                                    |
+================================+===========================================================================+
| Package-Create-Form            | Form-FieldSet Form-FieldSet Form-FieldSet                                 |
+--------------------------------+---------------------------------------------------------------------------+
| Package-Edit-Form              | Form-FieldSet Form-FieldSet Form-FieldSet                                 |
+--------------------------------+---------------------------------------------------------------------------+
| Form-FieldSet                  || <fieldset>                                                               |
|                                ||     <legend>...</legend>                                                 |
|                                ||     <dl>                                                                 |
|                                ||         Form-Field Form-Field Form-Field ...                             |
|                                ||     </dl>                                                                |
|                                || </fieldset>                                                              |
+--------------------------------+---------------------------------------------------------------------------+
| Form-Field                     | <dt>Form-Label</dt><dd>Form-Input</dd>                                    |
+--------------------------------+---------------------------------------------------------------------------+
| Form-Label                     | <label class="field_opt" for="FIELD-NAME">LABEL</label>                   |
+--------------------------------+---------------------------------------------------------------------------+
| Form-Input                     | <input id="FIELD-NAME" name="FIELD-NAME" value="FIELD-VALUE" ... />       |
+--------------------------------+---------------------------------------------------------------------------+
| Package-Create-Form-Submission | { form_data: [ (FIELD-NAME, FIELD-VALUE), (FIELD-NAME, FIELD-VALUE),      |
|                                | (FIELD-NAME, FIELD-VALUE), ... ],                                         |
|                                | log_message: LOG-MESSAGE, author: AUTHOR }                                |
+--------------------------------+---------------------------------------------------------------------------+
| Package-Edit-Form-Submission   | { form_data: [ (FIELD-NAME, FIELD-VALUE), (FIELD-NAME, FIELD-VALUE),      |
|                                | (FIELD-NAME, FIELD-VALUE), ... ],                                         |
|                                | log_message: LOG-MESSAGE, author: AUTHOR }                                |
+--------------------------------+---------------------------------------------------------------------------+
 

To send request data, create a simple data structure, then convert it to a JSON string, then percent-encode the JSON string, then send it as the request body.

Response data will be in the response body.

