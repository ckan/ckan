.. _table-designer:

========================
Table Designer extension
========================

.. versionadded:: 2.11

The CKAN Table Designer extension is a *data ingestion* and *enforced-validation* tool that:

- uses the :ref:`CKAN DataStore <datastore>` database as the primary data source
- allows rows to be updated without re-loading all data
- builds data schemas with custom types and constraints in the :ref:`data_dictionary` form
- enables referencing other tables with simple and composite primary keys
- enforces validation with PostgreSQL triggers for almost *any business logic desired*
- works with existing DataStore APIs for integration with other applications:

  - :meth:`~ckanext.datastore.logic.action.datastore_create` to create or update the data schema
  - :meth:`~ckanext.datastore.logic.action.datastore_upsert` to create or update rows
  - :meth:`~ckanext.datastore.logic.action.datastore_records_delete` to delete rows

- expands resource DataStore API documentation for updating and deleting with *examples from live data*
- creates a :ref:`datatables-view` for interactive searching and selection of existing rows
- provides web forms for:

  - creating or updating individual rows with interactive validation
  - deleting one or more existing rows with confirmation

- integrates with `ckanext-excelforms <https://github.com/ckan/ckanext-excelforms>`_ to use
  a spreadsheet application for:

  - bulk uploading thousands of rows
  - batch updating hundreds of existing rows
  - immediate validation/required field feedback while entering data
  - verifying data against validation rules server-side without uploading

- works with `ckanext-dsaudit <https://github.com/ckan/ckanext-dsaudit>`_ to track changes
  to rows and data schemas


---------------------------------------------
Table Designer vs. resource uploads and links
---------------------------------------------

With uploaded and linked resources the DataStore may contain a copy of the original
file data. This copy is deleted and re-loaded when the original file changes.
Often there is no data schema other than field types that are detected or overridden
by the user. If the original data contains an incompatible type or the type is detected
incorrectly the data loading process will fail leaving the DataStore empty.

Table Designer instead uses the CKAN DataStore as the primary source of data.

Rows can be individually created, updated and removed. Type validation
and constraints are enforced so bad data can't be mixed with good data. Primary
keys are guaranteed to be unique enabling links between resources.

This makes Table Designer resources well suited for data that is incrementally updated
such as reference data, vocabularies and time series data.


-------------------------
Setting up Table Designer
-------------------------

1. Enable the plugin
====================

Add the ``tabledesigner`` plugin to your CKAN config file *before* the ``datatables_view``
and ``datastore`` plugins::

 ckan.plugins = … tabledesigner datatables_view datastore …

2. Set-up DataStore
===================

If you haven't already, follow the instructions in :ref:`setting_up_datastore`


----------------------------------
Creating a Table Designer resource
----------------------------------

When creating a resource select "Data: Table Designer". This will automatically create
an empty DataStore table and a :ref:`datatables-view`.

.. image:: /images/table_designer_button.png

After saving your resource navigate to the :ref:`data_dictionary`
form to start creating fields.

.. image:: /images/table_designer_data_dict_button.png


----------------------------------------
Creating fields with the Data Dictionary
----------------------------------------

A newly created resource will have no fields defined. Use the "Add Field" button
in the Data Dictionary form to add fields for your data.

Customize each field with an ID, an obligation, a label and description.

ID
==

All fields must have an ID. The ID is used as the column name in the DataStore database.
PostgreSQL requires that column names start with a letter and be no longer than 31 characters.

The field ID is used to identify fields in the API and when exporting data in CSV or
other formats.

We recommend using a single convention for all IDs e.g. ``lowercase_with_underscores`` to
simplify accessing data from external systems.

Obligation
==========

The field obligation defaults to optional.

Optional
   no restrictions

Required
   may not be NULL or blank

Primary Key
   required and guaranteed unique within the table

When multiple fields are marked as primary keys the combination of values in each row is used
to determine uniqueness.

Label
=====

The field label is a human-friendly version of the ID, used when displaying data in the data
table preview, the data dictionary, in forms and in Excel templates.

Description
===========

The field description is markdown displayed in the data dictionary, as help text forms and
in Excel templates.


-----------
Field Types
-----------

Table Designer offers some common fields types by default. To customize the
types available see :ref:`custom-columns-constraints`.

.. image:: /images/table_designer_add_field.png


Text
====
Text fields contain a string of any length.

A pattern constraint is available to restrict text field using a regular expression.
When a pattern is changed the new pattern applies to all new rows and rows being updated,
not existing rows.

When used as part of a primary key, text values will have surrounding whitespace removed
automatically.

Choice
======
Choice fields are text fields that limit the user to selecting one of a set of options defined.

Enter the options into the Choices box, one option per line.

If an option is removed from the Choices box that exists in the data, the next time that
row is updated it will need to be changed to one of the current options for the change to be
accepted.

Email Address
=============
Email Address fields are text fields limited to a single valid email address according to
https://html.spec.whatwg.org/#valid-e-mail-address

URI
===
URI is a text field used for links (URLs) or other Uniform Resource Identifier values

Universally unique identifier
=============================
A UUID field is a 128-bit value written as a sequence of 32 hexadecimal digits
in groups separated by hyphens.

Values are always returned in standard form, e.g.::

 a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11

Numeric
=======
Numeric fields are *exact decimal values* with up to 131072 digits before the decimal point and
16383 digits after the decimal point.

Minimum and maximum constraints may be set to limit the range of values accepted, e.g. setting
the minimum to 0 would prevent negative numbers from being entered.

Integer
=======
Integer fields are 64-bit integer values with a range of -9223372036854775808 to +9223372036854775807

Minimum and maximum constraints may be set to limit the range of values accepted, e.g. setting
the minimum to 0 would prevent negative numbers from being entered.

Boolean
=======
Boolean fields may be set to either TRUE or FALSE.

JSON
====
JSON fields may contain any valid `JSON <https://www.json.org/>`_ 
and will retain the whitespace and order of keys passed.

Date
====
Date fields accept any ``YYYY-MM-DD`` value from 4713 BCE to 5874897 CE.

Minimum and maximum constraints may be set to limit the range of values accepted.

Timestamp
=========
Timestamp fields accept any ``YYYY-MM-DD hh:mm:ss.ssssss`` value from 4713 BCE to 294276 CE.

Minimum and maximum constraints may be set to limit the range of values accepted.


.. _table-designer-web-forms:

--------------------------------------------
Creating and updating rows with the web form
--------------------------------------------

Table Designer offers a web form for interactively creating or updating individual rows.

The fields you define generate the web forms. Labels for fields are shown instead of ids when
given, and field descriptions are displayed as help text and may include markdown with links,
tables or other information.

.. image:: /images/table_designer_form.png

The field type determines the input widget shown for each field. For custom types and input
widgets see: :ref:`custom-columns-constraints`

Creating rows
=============

Above the data table preview click the "Add row" button to create a row.

Updating rows
=============

In the data table preview select a row by clicking on it, then click the "Edit row" button
above the table.

Validation errors
=================

Errors will appear on the form after clicking "Save" if any values fail validation or cause
conflicts with existing rows.

.. image:: /images/table_designer_form_errors.png

Correct the highlighted errors and click "Save" again.


.. _table-designer-excelforms:

--------------------------------------------------
Creating and updating rows with ckanext-excelforms
--------------------------------------------------

`ckanext-excelforms <https://github.com/ckan/ckanext-excelforms>`_ is an extension for Table
Designer that allows using Excel templates to edit hundreds or create thousands of rows at
a time. Install ``ckanext-excelforms`` and add ``excelforms`` to your list of plugins *before*
the ``tabledesigner`` plugin::

 ckan.plugins = … excelforms tabledesigner datatables_view datastore …



Creating and updating rows
==========================

Below the data preview under "Table Designer" click the "Excel template" button to download
a clean template ``xlsx`` file. Open the template in Excel, LibreOffice, Google Docs or other
Excel-compatible spreadsheet application.

.. image:: /images/table_designer_excelforms.png

The template header (here "Bicycle Counters") is set based on the resource name. Each column
corresponds to one of the fields defined. Enter data into the rows starting right of the "▶".

.. note:: Use "paste special: values only" when pasting data into the template or the
 error highlighting and column formatting will be removed.

Click one of the column titles or the "reference" sheet to jump to a
reference tab with information about the field including descriptions and constraints. Click
on the field name in the reference to jump back to the data.

.. image:: /images/table_designer_excelforms_reference.png

Required cells missing data will appear with a *blue background* while entering data.
Cells with invalid values will appear with a *red background*.

.. image:: /images/table_designer_excelforms_errors.png

Duplicate primary keys (row 22), values outside the range constraints (row 24), values not
present in choices (row 27) and values in an invalid format (row 29) are highlighted as errors.

Click the thin border cells along the left (column A) or along the top under the field names (row 3)
to jump directly to the next error or missing value in that row/column. This is
useful when navigating a large template to quickly find errors or missing values.

Once errors are corrected, save the template and upload it with the file selection input
next to the "Excel template" button below the preview.

Click "Submit" to upload the data or "Check for Errors" to validate the data server-side
without creating or updating rows.

.. note:: If you have primary key fields defined, rows submitted here will *replace values for
 rows with the same primary key* in the DataStore database.


Editing existing rows
=====================

Select the rows to edit in the data table preview then click "Edit in Excel" above the table
to download an Excel template populated with data.

.. image:: /images/table_designer_excelforms_edit_button.png

This template is just like the clean one above except:

 - the template includes a read-only ``_id`` column at the left
 - the template has no additional rows for adding data
 - only the selected rows may be edited

Make changes to the rows in the template then save it and upload it with the file selection
input next to the "Excel template" button below the preview. Click "Submit".


-------------
Deleting rows
-------------

Select one or more rows in the data table preview then click "Delete rows" above the table.

.. image:: /images/table_designer_excelforms_delete.png

Click "Delete" to confirm deletion of the data shown.


-------------------------------------
Tracking changes with ckanext-dsaudit
-------------------------------------

Use `ckanext-dsaudit <https://github.com/ckan/ckanext-dsaudit>`_
with the activity plugin to track changes to Table Designer schemas
and data inserted and deleted from DataStore resources.
Install ``ckanext-dsaudit`` and add ``dsaudit`` to your list of plugins
*before* the ``activity`` plugin::

 ckan.plugins = … dsaudit activity …

Data Dictionary changes
=======================

``ckanext-dsaudit`` takes a snapshot of the Data Dictionary any time fields
are added or changed and adds it to the dataset activity feed.

.. image:: /images/dsaudit_redefined.png

Inserted rows
=============

``ckanext-dsaudit`` captures the total number of rows inserted or updated and
a sample of the values inserted and adds them to the dataset activity feed.

.. image:: /images/dsaudit_inserted.png

Deleted rows
============

``ckanext-dsaudit`` captures the total number of rows deleted and a sample
of the values deleted and adds them to the dataset activity feed.

.. image:: /images/dsaudit_deleted.png
