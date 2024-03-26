from __future__ import annotations

from typing import Type, Callable, Any, List, cast
from collections.abc import Iterable, Mapping

from ckan.types import Validator, Schema
from ckan.plugins.toolkit import get_validator
from ckanext.datastore.backend.postgres import identifier, literal_string

from .column_constraints import ColumnConstraint


def _(x: str):
    return x


_standard_column_types = {}


def _standard_column(
        key: str) -> "Callable[[Type[ColumnType]], Type[ColumnType]]":
    def register(cls: "Type[ColumnType]"):
        _standard_column_types[key] = cls
        return cls
    return register


class ColumnType:
    """
    ColumnType subclasses define:

    - PostgreSQL column type used to store data
    - label, description and example value
    - pl/pgsql rules for validating data on insert/update
    - snippets for data dictionary field definitions and form entry
    - validators for data dictionary field values
    - choice lists for choice fields
    - excel format and validation rules for ckanext-excelforms

    Use IColumnTypes to add/modify the column types available.
    """
    #:
    label = 'undefined'
    #:
    description = 'undefined'
    #: DataStore PostgreSQL column type
    datastore_type = 'text'
    #: snippet used for adding/editing individual records
    form_snippet = 'text.html'
    #: snippet used for resource page data dictionary extra info
    view_snippet = None
    #: text.html form snippet input tag ``type`` attribute value
    html_input_type = 'text'
    #: ckanext-excelforms column format
    excel_format = 'General'
    #: used by sql_required_rule
    _SQL_IS_EMPTY = "({value} = '') IS NOT FALSE"

    def __init__(
            self,
            field: dict[str, Any],
            constraint_types: List[Type[ColumnConstraint]]):
        self.colname = field.get('id', '')
        self.field = field
        self._constraint_types = constraint_types

    def column_constraints(self) -> Iterable[ColumnConstraint]:
        for cct in self._constraint_types:
            yield cct(self)

    # sql_required_rule format string
    _SQL_REQUIRED = '''
    IF {condition} THEN
        errors := errors || ARRAY[
            {colname}, {error}
        ];
    END IF;
    '''

    def sql_required_rule(self):
        """
        return SQL to enforce that primary keys and required fields are
        not empty.
        """
        error = 'Missing value'

        if self.field.get('tdpkreq'):
            if self.field.get('tdpkreq') == 'pk':
                error = 'Primary key must not be empty'

            return self._SQL_REQUIRED.format(
                condition=self._SQL_IS_EMPTY.format(
                    value=f'NEW.{identifier(self.colname)}'
                ),
                colname=literal_string(self.colname),
                error=literal_string(error),
            )

    def sql_validate_rule(self):
        """
        Override to return type-related SQL validation.
        For constraints use ColumnConstraint subclasses instead.
        """
        return

    @classmethod
    def datastore_field_schema(
            cls, td_ignore: Validator, td_pd: Validator) -> Schema:
        """
        Return schema with keys to add to the datastore_create
        field schema. Convention for table designer field keys:

        - prefix keys with 'td' to avoid name conflicts with other
          extensions using IDataDictionaryForm
        - use td_ignore validator first to ignore input when not
          editing a table designer resource (schema applies to
          all data data dictionaries not only table designer ones)
        - use td_pd validator last to store values as table designer
          plugin data so they can be read from datastore_info later

        e.g.::

         return {'tdmykey': [td_ignore, my_validator, td_pd]}
         #        ^ prefix   ^ ignore non-td          ^ store value
        """
        return {}


@_standard_column('text')
class TextColumn(ColumnType):
    #:
    label = _('Text')
    #:
    description = _('Unicode text of any length')
    #:
    example = _('free-form text')
    table_schema_type = 'string'
    table_schema_format = 'default'

    _SQL_TRIM_PK = '''
    {value} := trim({value});
    '''

    def sql_validate_rule(self):
        '''
        Return an SQL rule to remove surrounding whitespace from text
        pk fields to avoid accidental duplication.
        '''
        if self.field.get('tdpkreq') == 'pk':
            return self._SQL_TRIM_PK.format(
                value=f'NEW.{identifier(self.colname)}',
            )
        return ''


@_standard_column('choice')
class ChoiceColumn(ColumnType):
    #:
    label = _('Choice')
    #:
    description = _('Choose one option from a fixed list')
    #:
    example = 'b1'
    datastore_type = 'text'
    table_schema_type = 'string'
    table_schema_format = 'default'
    table_schema_constraint = 'enum'
    #: render a select input based on self.choices()
    form_snippet = 'choice.html'
    #: render a textarea input for valid options
    design_snippet = 'choice.html'
    #: preview choices in a table on resource page
    view_snippet = 'choice.html'

    def choices(self) -> Iterable[str] | Mapping[str, str]:
        """
        Return a choice list from the field data.
        """
        c = self.field.get('tdchoices', [])
        if isinstance(c, list):
            return c
        # when building from form values convert from newline list
        cleanlist = cast(
            Callable[[list[str]], list[str]],
            get_validator('tabledesigner_clean_list'))
        newlinelist = cast(
            Callable[[str], list[str]],
            get_validator('tabledesigner_newline_list'))
        return cleanlist(newlinelist(c))

    # \t is used when converting errors to string, remove any from data
    _SQL_VALIDATE = '''
    IF {value} IS NOT NULL AND {value} <> ''
            AND NOT ({value} = ANY ({choices}))
        THEN
        errors := errors || ARRAY[[{colname}, 'Invalid choice: "'
            || replace({value}, E'\t', ' ') || '"']];
    END IF;
    '''

    def sql_validate_rule(self):
        """
        Return SQL to validate an option against self.choices()
        """
        return self._SQL_VALIDATE.format(
            value=f'NEW.{identifier(self.colname)}',
            colname=literal_string(self.colname),
            choices='ARRAY[' + ','.join(
                literal_string(c) for c in self.choices()
            ) + ']'
        )

    def excel_validate_rule(self):
        """
        Return an Excel formula to validate options against self.choices()
        """
        # excelforms provides {_choice_range_} cells with all choice values
        return 'COUNTIF({_choice_range_},TRIM({_value_}))=0'

    @classmethod
    def datastore_field_schema(
            cls, td_ignore: Validator, td_pd: Validator) -> Schema:
        """
        Return schema to store ``tdchoices`` in the field data as a list of
        strings.
        """
        not_empty = get_validator('not_empty')
        td_newline_list = get_validator('tabledesigner_newline_list')
        td_clean_list = get_validator('tabledesigner_clean_list')

        return {'tdchoices': [
            td_ignore, td_newline_list, td_clean_list, not_empty, td_pd]}


@_standard_column('email')
class EmailColumn(ColumnType):
    #:
    label = _('Email Address')
    #:
    description = _('A single email address')
    #:
    example = 'user@example.com'
    datastore_type = 'text'
    table_schema_type = 'string'
    table_schema_format = 'email'
    html_input_type = 'email'

    # remove surrounding whitespace and validate
    _SQL_VALIDATE = '''
    {value} := trim({value});
    IF {value} <> '' AND regexp_match({value}, {pattern}) IS NULL THEN
        errors := errors || ARRAY[{colname}, {error}];
    END IF;
    '''

    # pattern from https://html.spec.whatwg.org/#valid-e-mail-address
    _EMAIL_PATTERN = (
        r"^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9]" +
        r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9]" +
        r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    )

    def sql_validate_rule(self):
        """
        Return SQL rule to check value against the email regex.
        """
        return self._SQL_VALIDATE.format(
            value=f'NEW.{identifier(self.colname)}',
            pattern=literal_string(self._EMAIL_PATTERN),
            colname=literal_string(self.colname),
            error=literal_string(_('Invalid email')),
        )


@_standard_column('uri')
class URIColumn(ColumnType):
    #:
    label = _('URI')
    #:
    description = _('Uniform resource identifier (URL or URN)')
    #:
    example = 'https://example.com/page'
    datastore_type = 'text'
    table_schema_type = 'string'
    table_schema_format = 'uri'
    html_input_type = 'url'


@_standard_column('uuid')
class UUIDColumn(ColumnType):
    #:
    label = _('Universally unique identifier (UUID)')
    #:
    description = _('A universally unique identifier as hexadecimal')
    #:
    example = '213b972d-75c0-48b7-b14a-5a19eb58a1fa'
    datastore_type = 'uuid'
    table_schema_type = 'string'
    table_schema_format = 'uuid'
    _SQL_IS_EMPTY = "{value} IS NULL"


@_standard_column('numeric')
class NumericColumn(ColumnType):
    #:
    label = _('Numeric')
    #:
    description = _('Number with arbitrary precision (any number of '
                    'digits before and after the decimal)')
    #:
    example = '2.01'
    datastore_type = 'numeric'
    table_schema_type = 'number'
    _SQL_IS_EMPTY = "{value} IS NULL"

    def excel_validate_rule(self):
        """
        Return an Excel formula to check for numbers.
        """
        return 'NOT(ISNUMBER({_value_}))'


@_standard_column('integer')
class IntegerColumn(ColumnType):
    #:
    label = _('Integer')
    #:
    description = _('Whole numbers with no decimal')
    #:
    example = '21'
    datastore_type = 'int8'
    table_schema_type = 'integer'
    _SQL_IS_EMPTY = "{value} IS NULL"

    def excel_validate_rule(self):
        """
        Return an Excel formula to check for integers.
        """
        return 'NOT(IFERROR(INT({_value_})=VALUE({_value_}),FALSE))'


@_standard_column('boolean')
class BooleanColumn(ColumnType):
    #:
    label = _('Boolean')
    #:
    description = _('True or false values')
    #:
    example = 'false'
    datastore_type = 'boolean'
    table_schema_type = 'boolean'
    form_snippet = 'choice.html'
    _SQL_IS_EMPTY = "{value} IS NULL"

    def choices(self):
        """
        Return TRUE/FALSE choices.
        """
        # We have a request context here so return labels in user's language
        from ckan.plugins.toolkit import _
        return {
            'false': _('FALSE'),
            'true': _('TRUE'),
        }

    def choice_value_key(self, value: bool | str) -> str:
        """
        Convert bool to string for matching choice keys in the choice.html form
        snippet.
        """
        return 'true' if value else 'false' if isinstance(
            value, bool) else value

    def excel_validate_rule(self):
        """
        Return an Excel formula to check for TRUE/FALSE.
        """
        return 'AND({_value_}<>TRUE,{_value_}<>FALSE)'


@_standard_column('json')
class JSONColumn(ColumnType):
    #:
    label = _('JSON')
    #:
    description = _('A JSON object')
    #:
    example = '{"key": "value"}'
    datastore_type = 'json'
    table_schema_type = 'object'
    _SQL_IS_EMPTY = "{value} IS NULL OR {value}::jsonb = 'null'::jsonb"


@_standard_column('date')
class DateColumn(ColumnType):
    #:
    label = _('Date')
    #:
    description = _('Date without time of day')
    #:
    example = '2024-01-01'
    datastore_type = 'date'
    table_schema_type = 'date'
    table_schema_format = 'fmt:YYYY-MM-DD'
    html_input_type = 'date'
    excel_format = 'yyyy-mm-dd'
    _SQL_IS_EMPTY = "{value} IS NULL"

    def excel_validate_rule(self):
        """
        Return an Excel formula to check for a date.
        """
        # excel represents timestamps as numbers, integers are dates
        return (
            'OR(NOT(ISNUMBER({_value_}+0)),'
            'NOT(IFERROR(INT({_value_}+0)=VALUE({_value_}+0),FALSE)))'
        )


@_standard_column('timestamp')
class TimestampColumn(ColumnType):
    #:
    label = _('Timestamp')
    #:
    description = _('Date and time without time zone')
    #:
    example = '2024-01-01 12:00:00'
    datastore_type = 'timestamp'
    table_schema_type = 'datetime'
    table_schema_format = 'fmt:YYYY-MM--DD hh:mm:ss'
    html_input_type = 'datetime-local'

    excel_format = 'yyyy-mm-dd HH:MM:SS'
    _SQL_IS_EMPTY = "{value} IS NULL"

    def excel_validate_rule(self):
        """
        Return an Excel formula to check for a timestamp.
        """
        # excel represents timestamps as numbers
        return 'NOT(ISNUMBER({_value_}+0))'
