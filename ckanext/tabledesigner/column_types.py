from __future__ import annotations

from typing import Type, Callable, Any, List

from ckanext.datastore.backend.postgres import identifier, literal_string

from ckan.plugins.toolkit import h


def _(x: str):
    return x


_standard_column_types = {}


def _standard_column(
        key: str) -> "Callable[[Type[ColumnType]], Type[ColumnType]]":
    def register(cls: "Type[ColumnType]"):
        _standard_column_types[key] = cls
        return cls
    return register


column_types = _standard_column_types  # FIXME: include plugin column types


class ColumnType:
    sql_is_empty = "{column} IS NULL"
    form_snippet = 'text.html'
    html_input_type = 'text'

    @classmethod
    def sql_required_rule(cls, info: dict[str, Any]):
        """
        Primary keys and required fields must not be empty
        """
        colname = info['id']
        error = 'Missing value'

        if info.get('pkreq'):
            if info.get('pkreq') == 'pk':
                error = 'Primary key must not be empty'

            return '''
                IF {condition} THEN
                    errors := errors || ARRAY[
                        {colname}, {error}
                    ];
                END IF;
                '''.format(
                    condition=cls.sql_is_empty.format(
                        column=f'NEW.{identifier(colname)}'
                    ),
                    colname=literal_string(colname),
                    error=literal_string(error),
                )

    @classmethod
    def sql_validate_rule(cls, info: dict[str, Any]):
        """
        Override when validation is required
        """
        return


@_standard_column('text')
class TextColumn(ColumnType):
    label = _('Text')
    description = _('Unicode text of any length')
    example = _('free-form text')
    datastore_type = 'text'
    table_schema_type = 'string'
    table_schema_format = 'default'
    sql_is_empty = "({column} = '') IS NOT FALSE"


@_standard_column('choice')
class ChoiceColumn(ColumnType):
    label = _('Choice')
    description = _('Choose one option from a fixed list')
    example = 'b1'
    datastore_type = 'text'
    table_schema_type = 'string'
    table_schema_format = 'default'
    table_schema_constraint = 'enum'
    sql_is_empty = "({column} = '') IS NOT FALSE"
    form_snippet = 'choice.html'

    @classmethod
    def choices(cls, info: dict[str, Any]) -> List[str]:
        """
        Comma-separated text field with choice values
        """
        choices = info.get('choices')
        if choices:
            return [c.strip() for c in choices.split(',')]
        return []

    @classmethod
    def sql_validate_rule(cls, info: dict[str, Any]):
        """
        Copy choices into validation rule as a literal string array
        """
        colname = info['id']

        # \t is used when converting errors to string, remove any from data
        return '''
            IF {value} IS NOT NULL AND {value} <> '' AND NOT ({value} = ANY ({choices}))
                THEN
                errors := errors || ARRAY[[{colname}, 'Invalid choice: "'
                    || replace({value}, E'\t', ' ') || '"']];
            END IF;
            '''.format(
                value=f'NEW.{identifier(colname)}',
                colname=literal_string(colname),
                choices='ARRAY[' + ','.join(
                    literal_string(c) for c in h.tabledesigner_choice_list(info)
                ) + ']'
            )


@_standard_column('email')
class EmailColumn(ColumnType):
    label = _('Email Address')
    description = _('A single email address')
    example = 'user@example.com'
    datastore_type = 'text'
    table_schema_type = 'string'
    table_schema_format = 'email'
    sql_is_empty = "({column} = '') IS NOT FALSE"
    html_input_type = 'email'


@_standard_column('uri')
class URIColumn(ColumnType):
    label = _('URI')
    description = _('A uniform resource identifier (URL or URN)')
    example = 'https://example.com/page'
    datastore_type = 'text'
    table_schema_type = 'string'
    table_schema_format = 'uri'
    sql_is_empty = "({column} = '') IS NOT FALSE"
    html_input_type = 'url'


@_standard_column('uuid')
class UUIDColumn(ColumnType):
    label = _('UUID')
    description = _('A universally unique identifier as hexadecimal')
    example = '213b972d-75c0-48b7-b14a-5a19eb58a1fa'
    datastore_type = 'uuid'
    table_schema_type = 'string'
    table_schema_format = 'uuid'


@_standard_column('numeric')
class NumericColumn(ColumnType):
    label = _('Numeric')
    description = _('Number with arbitrary precision (any number of '
                    'digits before and after the decimal)')
    example = '2.01'
    datastore_type = 'numeric'
    table_schema_type = 'number'


@_standard_column('integer')
class IntegerColumn(ColumnType):
    label = _('Integer')
    description = _('Whole numbers with no decimal')
    example = '21'
    datastore_type = 'int8'
    table_scema_type = 'integer'


@_standard_column('boolean')
class BooleanColumn(ColumnType):
    label = _('Boolean')
    description = _('True or false values')
    example = 'false'
    datastore_type = 'boolean'
    table_schema_type = 'boolean'


@_standard_column('json')
class JSONColumn(ColumnType):
    label = _('JSON')
    description = _('A JSON object')
    example = '{"key": "value"}'
    datastore_type = 'json'
    table_schema_type = 'object'


@_standard_column('date')
class DateColumn(ColumnType):
    label = _('Date')
    description = _('Date without time of day')
    example = '2024-01-01'
    datastore_type = 'date'
    table_schema_type = 'string'
    table_schema_format = 'date'
    html_input_type = 'date'


@_standard_column('timestamp')
class TimestampColumn(ColumnType):
    label = _('Timestamp')
    description = _('Date and time without time zone')
    example = '2024-01-01 12:00:00'
    datastore_type = 'timestamp'
    table_schema_type = 'string'
    table_schema_format = 'date-time'
    html_input_type = 'datetime-local'
