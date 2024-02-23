.. _tabledesigner:

========================
Table Designer extension
========================

The CKAN Table Designer extension is a *data ingestion* and *enforced-validation* tool for your
resources that:

- uses the CKAN DataStore database as the primary data source
- allows records to be updated without re-loading all data
- builds data schemas with custom types and constraints in the :ref:`data_dictionary` form
- enables linked data with simple and composite primary keys
- enforces validation with PostgreSQL triggers for almost *any business logic desired*
- works with existing DataStore APIs for integration with other applications:

  - :meth:`~ckanext.datastore.logic.action.datastore_create` to create or update the data schema
  - :meth:`~ckanext.datastore.logic.action.datastore_upsert` to create or update records
  - :meth:`~ckanext.datastore.logic.action.datastore_records_delete` to delete records

- expands resource DataStore API documentation for updating and deleting with *examples from live data*
- creates a :ref:`datatables-view` for interactive searching and selection of existing records
- provides web forms for:

  - creating or updating individual records with interactive validation
  - deleting one or more existing records with confirmation

- integrates with `ckanext-excelforms <https://github.com/ckan/ckanext-excelforms>`_ to use
  a spreadsheet application for:

  - bulk uploading thousands of records
  - batch updating hundreds of existing records
  - immediate validation/required field feedback while entering data
  - verifying data against validation rules server-side without uploading

- works with `ckanext-dsaudit <https://github.com/ckan/ckanext-dsaudit>`_ to track changes
  to records and data schemas


-------------------------
Setting up Table Designer
-------------------------

1. Enable the plugin
====================

Add the ``tabledesigner`` plugin to your CKAN config file *before* the ``datastore`` plugin::

 ckan.plugins = … tabledesigner datastore …

2. Set-up DataStore
===================

If you haven't already, follow the instructions in :ref:`setting_up_datastore`

---------------------------------------------
Table Designer vs. resource uploads and links
---------------------------------------------

With uploaded and linked resources the DataStore may contain a copy of the original
file data. This copy is deleted and re-loaded when the original file changes.
Often there is no data schema other than field types that are detected or overridden
by the user. If the original data contains an incompatible type or the type is detected
incorrectly the data loading process will fail leaving the DataStore empty.

Table Designer instead uses the CKAN DataStore as the primary source of data.

Records can be individually created, updated and removed. Type validation
and constraints are enforced so bad data can't be mixed with good data. Primary
keys are guaranteed to be unique enabling links between resources.

This makes Table Designer resources well suited for data that is incrementally updated
such as reference data, vocabularies and time series data.

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

.. image:: /images/table_designer_add_field.png

ID
==

All fields must have an ID. The ID is used as the column name in the DataStore database.
PostgreSQL requires that column names start with a letter and be no longer than 31 characters.

The field ID is used to identify fields in the API and when exporting data in CSV or
other formats.

We recommend using a single convention for all IDs e.g. ``lowercase_with_underscores`` to
simplify accessing data from external systems.

.. image:: /images/table_designer_obligation.png

Obligation
==========

Optional
   no restrictions
   
Required
   may not be NULL or blank

Primary Key
   required and guaranteed unique within the table

When multiple fields are marked as primary keys the combination of values in each row is used
to determine uniqueness.


-----------
Field Types
-----------

Table Designer offers some common fields types by default. To customize the
types available see :ref:FIXME

Text
====
Text fields contain a string of any length.

A pattern constraint is available to restrict text field using a regular expression.

When a pattern is changed it applies to all new records and records being updated,
not existing records.

When used as part of a primary key, text values will have surrounding whitespace removed
automatically.

Choice
======
Choice fields are text fields limited to one of a set of options defined.

Enter the options into the Choices box.  Other values may not be entered into this field.

If an option is removed from the Choices box that still exists in the data, the next time that
record is updated it will need to be changed to one of the current options for the change to be
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
