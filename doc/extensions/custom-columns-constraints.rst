.. _custom-columns-constraints:

=======================================================
Customizing Table Designer Column Types and Constraints
=======================================================

The :ref:`table-designer` field types are built with:

 - a ``tdtype`` string value identifying the type e.g. ``"text"``
 - a corresponding
   :py:class:`~ckanext.tabledesigner.column_types.ColumnType` subclass
   that defines the DataStore column type, template snippets and
   validation rules
 - a list of
   :py:class:`~ckanext.tabledesigner.column_constraints.ColumnConstraint`
   subclasses that apply to this type to extend the form templates
   and validation rules

For example when a field is defined with the "Integer" type, the field's
``tdtype`` is set to ``"integer"``, the
:py:class:`~ckanext.tabledesigner.column_types.ColumnType` subclass is
:py:class:`~ckanext.tabledesigner.column_types.IntegerColumn` and
the :py:class:`~ckanext.tabledesigner.column_constraints.RangeConstraint`
class applies to limit the minimum and maximum values.

:py:class:`~ckanext.tabledesigner.column_types.IntegerColumn`
sets the DataStore column type to ``"int8"`` to store
a 64-bit value and adds a rule to check for integers when entering
values in Excel templates with
`ckanext-excelforms <https://github.com/ckan/ckanext-excelforms>`_.

New column types may be defined and existing column types replaced or removed
by an extension implementing the
:py:class:`~ckanext.tabledesigner.interfaces.IColumnTypes` interface.

:py:class:`~ckanext.tabledesigner.column_constraints.RangeConstraint`
adds minimum and maximum form fields to the data
dictionary form, stores those values as ``tdminimum`` and ``tdmaximum``
in the field and applies a rule to ensure that no values outside those
given will be accepted by the DataStore database.

:py:class:`~ckanext.tabledesigner.column_constraints.RangeConstraint`
is separate from
:py:class:`~ckanext.tabledesigner.column_types.IntegerColumn`
to allow disabling or replacing it and because it
:ref:`applies equally to other types<range-constraint>`.

New constraints may be defined and existing constraints may be applied to
new types or removed from existing types by an extension implementing the
:py:class:`~ckanext.tabledesigner.interfaces.IColumnConstraints` interface.


--------------------------
Custom Column Type Example
--------------------------

Let's create a new type for storing a user rating from 1-5.

.. image:: /images/table_designer_star_rating.png

.. literalinclude:: ../../ckanext/example_icolumntypes/plugin.py
 :pyobject: StarRatingColumn

For space efficiency our values can be stored using numbers 1-5 in the
smallest PostgreSQL integer type available: ``int2``.

We use the ``choice.html`` form snippet with a ``choices()`` method
to display a drop-down in
the :ref:`web forms<table-designer-web-forms>`
showing 1-star (★) to 5-star (★★★★★) options.

`ckanext-excelforms <https://github.com/ckan/ckanext-excelforms>`_
uses the same ``choices()`` method to populate a drop-down and
reference information with our options in
:ref:`Excel templates<table-designer-excelforms>`.

We're storing an integer but comparing it to string keys in the
form so we define a ``choice_value_key()`` to convert values before
comparing.

We enforce validation server-side with ``sql_validate_rule()``. Here
we return SQL that checks that our value is ``BETWEEN 1 AND 5``.
If not it adds an error message to an ``errors`` array.
This array is used to return errors
from :func:`~ckanext.datastore.logic.action.datastore_upsert` and to
display errors in the :ref:`web forms<table-designer-web-forms>`.

.. warning:: Generating SQL with string operations and user-provided
 data can allow untrusted code to be executed from the DataStore
 database. Make sure to use
 :func:`~ckanext.datastore.backend.postgres.identifier` for column
 names and
 :func:`~ckanext.datastore.backend.postgres.literal_string` for
 string values added to the SQL returned.

SQL rules from all the column types and constraints in a table
are combined into a trigger that is executed as a
`data change trigger <https://www.postgresql.org/docs/current/plpgsql-trigger.html#PLPGSQL-DML-TRIGGER>`_
in the DataStore database. Almost any business logic can be
implemented including validation across columns or tables and
by using PostgreSQL extensions like PostGIS or foreign data
wrappers.

.. note::

  For column types and constraints we use a dummy gettext function
  ``_()`` because strings defined at the module level are translated
  when rendered later.

  .. literalinclude:: ../../ckanext/example_icolumntypes/plugin.py
   :pyobject: _

Next we need to register our new column type with an
:class:`~ckanext.tabledesigner.interfaces.IColumnTypes` plugin:

.. literalinclude:: ../../ckanext/example_icolumntypes/plugin.py
 :pyobject: ExampleIColumnTypesPlugin

``column_types()`` adds our new column type to the existing ones
with a ``tdtype`` value of ``"star_rating"``. Enable our plugin
and add a new star rating field to a Table Designer resource.


--------------------------------
Custom Column Constraint Example
--------------------------------

Let's create a constraint that can prevent any field from being
modified after it is first set to a non-empty value.

.. image:: /images/table_designer_immutable_checkbox.png

We create a
``templates/tabledesigner/constraint_snippets/immutable.html``
snippet to render an "Immutable" checkbox in the Data Dictionary form:

.. literalinclude:: ../../ckanext/example_icolumnconstraints/templates/tabledesigner/constraint_snippets/immutable.html
 :language: jinja

When checked the ``ImmutableConstraint`` will apply for that field:

.. literalinclude:: ../../ckanext/example_icolumnconstraints/plugin.py
 :pyobject: ImmutableConstraint

We store the ``tdimmutable`` Data Dictionary field checkbox setting
with ``datastore_field_schema()``.

In ``sql_constraint_rule()`` we return SQL to access
the old value for a cell using ``OLD.(colname)``.
:py:class:`~ckanext.tabledesigner.column_types.ColumnType` subclasses
have an
:py:attr:`~ckanext.tabledesigner.column_types.ColumnType._SQL_IS_EMPTY`
format string, normally used to enforce
:py:meth:`~ckanext.tabledesigner.column_types.ColumnType.sql_required_rule`.
We can use that string to check if a value was set previously for this
column type.

We add an error message to the ``errors`` array if the old value was not
empty and the new value ``NEW.(colname)`` is different.

.. image:: /images/table_designer_immutable_error.png

Next we need to register our new column constraint and have it apply
to *all* the current column types:

.. literalinclude:: ../../ckanext/example_icolumnconstraints/plugin.py
 :pyobject: ExampleIColumnConstraintsPlugin

We add our extension's template directory from ``update_config()``
so that the checkbox snippet can be found.

In ``column_constraints()`` we append our ``ImmutableConstraint`` to
the constraints for all existing column types.

.. note::

  Plugin order matters here. If we want the ``ImmutableConstraint`` to
  apply to a new column type this plugin needs to come *before* the
  plugin that defines the type.


-------------------
Interface Reference
-------------------

.. autoclass:: ckanext.tabledesigner.interfaces.IColumnTypes
   :members:

.. autoclass:: ckanext.tabledesigner.interfaces.IColumnConstraints
   :members:


---------------------
Column Type Reference
---------------------

.. seealso::
   :source-blob:`Complete source code of these column type classes <ckanext/tabledesigner/column_types.py>`

ColumnType base class
=====================

.. autoclass:: ckanext.tabledesigner.column_types.ColumnType
   :members:
   :private-members: _SQL_IS_EMPTY

TextColumn ``tdtype = "text"``
==============================

.. autoclass:: ckanext.tabledesigner.column_types.TextColumn
   :members:
   :show-inheritance:

ChoiceColumn ``tdtype = "choice"``
==================================

.. autoclass:: ckanext.tabledesigner.column_types.ChoiceColumn
   :members:
   :show-inheritance:

EmailColumn ``tdtype = "email"``
================================

.. autoclass:: ckanext.tabledesigner.column_types.EmailColumn
   :members:
   :show-inheritance:

URIColumn ``tdtype = "uri"``
============================

.. autoclass:: ckanext.tabledesigner.column_types.URIColumn
   :members:
   :show-inheritance:

UUIDColumn ``tdtype = "uuid"``
==============================

.. autoclass:: ckanext.tabledesigner.column_types.UUIDColumn
   :members:
   :private-members: _SQL_IS_EMPTY
   :show-inheritance:

NumericColumn ``tdtype = "numeric"``
====================================

.. autoclass:: ckanext.tabledesigner.column_types.NumericColumn
   :members:
   :private-members: _SQL_IS_EMPTY
   :show-inheritance:

IntegerColumn ``tdtype = "integer"``
====================================

.. autoclass:: ckanext.tabledesigner.column_types.IntegerColumn
   :members:
   :private-members: _SQL_IS_EMPTY
   :show-inheritance:

BooleanColumn ``tdtype = "boolean"``
====================================

.. autoclass:: ckanext.tabledesigner.column_types.BooleanColumn
   :members:
   :private-members: _SQL_IS_EMPTY
   :show-inheritance:

JSONColumn ``tdtype = "json"``
==============================

.. autoclass:: ckanext.tabledesigner.column_types.JSONColumn
   :members:
   :private-members: _SQL_IS_EMPTY
   :show-inheritance:

DateColumn ``tdtype = "date"``
==============================

.. autoclass:: ckanext.tabledesigner.column_types.DateColumn
   :members:
   :private-members: _SQL_IS_EMPTY
   :show-inheritance:

TimestampColumn ``tdtype = "timestamp"``
========================================

.. autoclass:: ckanext.tabledesigner.column_types.TimestampColumn
   :members:
   :private-members: _SQL_IS_EMPTY
   :show-inheritance:


---------------------------
Column Constraint Reference
---------------------------

.. seealso::
   :source-blob:`Complete source code of these column constraint classes <ckanext/tabledesigner/column_constraints.py>`

ColumnConstraint base class
===========================

.. autoclass:: ckanext.tabledesigner.column_constraints.ColumnConstraint
   :members:

.. _range-constraint:

RangeConstraint
===============

Applies by default to:

 - :py:class:`~ckanext.tabledesigner.column_types.NumericColumn`
 - :py:class:`~ckanext.tabledesigner.column_types.IntegerColumn`
 - :py:class:`~ckanext.tabledesigner.column_types.DateColumn`
 - :py:class:`~ckanext.tabledesigner.column_types.TimestampColumn`

.. autoclass:: ckanext.tabledesigner.column_constraints.RangeConstraint
   :members:
   :show-inheritance:

PatternConstraint
=================

Applies by default to:

 - :py:class:`~ckanext.tabledesigner.column_types.TextColumn`

.. autoclass:: ckanext.tabledesigner.column_constraints.PatternConstraint
   :members:
   :show-inheritance:


-------------------------
String Escaping Functions
-------------------------

.. autofunction:: ckanext.datastore.backend.postgres.identifier

.. autofunction:: ckanext.datastore.backend.postgres.literal_string

.. autofunction:: ckanext.tabledesigner.excel.excel_literal
