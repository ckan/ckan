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
   :py:class:`~ckanext.tabledesigner.column_constraint.ColumnConstraint`
   subclasses that apply to this type to extend the form templates
   and validation rules

For example when a field is defined with the "Integer" type, the field's
``tdtype`` is set to ``"integer"``, the ``ColumnType`` subclass is
:py:class:`~ckanext.tabledesigner.column_types.IntegerColumn` and
the :py:class:`~ckanext.tabledesigner.column_constraint.RangeConstraint`
class applies to limit the minimum and maximum values.

``IntegerColumn`` sets the DataStore column type to ``"int8"`` to store
a 64-bit value and adds a rule to check for integers when entering
values in Excel templates with ckanext-excelformat

New column types may be defined and existing column types replaced or removed
by an extension implementing the
:py:class:`~ckanext.tabledesigner.interfaces.IColumnTypes` interface.

``RangeConstraint`` adds minimum and maximum form fields to the data
dictionary form, stores those values as ``tdminumum`` and ``tdmaximum``
in the field and applies a rule to ensure that no values outside those
given will be accepted by the DataStore database.

``RangeConstraint`` is separate ``IntegerColumn`` because it can
be applied equally to other types including:

 - :py:class:`~ckanext.tabledesigner.column_types.NumericColumn`
 - :py:class:`~ckanext.tabledesigner.column_types.DateColumn`
 - :py:class:`~ckanext.tabledesigner.column_types.TimestampColumn`

New constraints may be defined, existing constraints may be applied to
new types or removed from existing types by a extension implementing the
:py:class:`~ckanext.tabledesigner.interfaces.IColumnConstraints` interface.

-------------------
Star Rating Example
-------------------

Let's start by creating a new type for storing a user rating from 1-5.

For efficiency the value can be stored using numbers 1-5 in the smallest
integer type available.

We will reuse the choice form snippet to display choices as a drop-down
showing 1 star to 5 stars.

.. literalinclude:: ../../ckanext/example_icolumntypes/plugin.py



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

ColumnType base class
=====================

.. autoclass:: ckanext.tabledesigner.column_types.ColumnType
   :members:

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
   :show-inheritance:

NumericColumn ``tdtype = "numeric"``
====================================

.. autoclass:: ckanext.tabledesigner.column_types.NumericColumn
   :members:
   :show-inheritance:

IntegerColumn ``tdtype = "integer"``
====================================

.. autoclass:: ckanext.tabledesigner.column_types.IntegerColumn
   :members:
   :show-inheritance:

BooleanColumn ``tdtype = "boolean"``
====================================

.. autoclass:: ckanext.tabledesigner.column_types.BooleanColumn
   :members:
   :show-inheritance:

JSONColumn ``tdtype = "json"``
==============================

.. autoclass:: ckanext.tabledesigner.column_types.JSONColumn
   :members:
   :show-inheritance:

DateColumn ``tdtype = "date"``
==============================

.. autoclass:: ckanext.tabledesigner.column_types.DateColumn
   :members:
   :show-inheritance:

TimestampColumn ``tdtype = "timestamp"``
========================================

.. autoclass:: ckanext.tabledesigner.column_types.TimestampColumn
   :members:
   :show-inheritance:


---------------------------
Column Constraint Reference
---------------------------

ColumnConstraint base class
===========================

.. autoclass:: ckanext.tabledesigner.column_constraints.ColumnConstraint
   :members:

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
