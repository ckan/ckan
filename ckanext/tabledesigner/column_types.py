from ckanext.datastore.backend.postgres import identifier, literal_string

from ckan.plugins.toolkit import h


def _(x):
    return x


_standard_column_types = {}


def _standard_column(key):
    def register(cls):
        _standard_column_types[key] = cls
    return register


class ColumnType:
    label = 'undefined'
    # some defaults to save repetition in subclasses
    datastore_type = 'text'
    form_snippet = 'text.html'
    html_input_type = 'text'
    sql_is_empty = "({column} = '') IS NOT FALSE"

    def __new__(cls, *args, **kwargs):
        raise TypeError(
            'Column type classes are used directly, not instantiated'
        )

    _SQL_REQUIRED = '''
    IF {condition} THEN
        errors := errors || ARRAY[
            {colname}, {error}
        ];
    END IF;
    '''

    @classmethod
    def sql_required_rule(cls, info):
        """
        Primary keys and required fields must not be empty
        """
        colname = info['id']
        error = 'Missing value'

        if info.get('pkreq'):
            if info.get('pkreq') == 'pk':
                error = 'Primary key must not be empty'

            return cls._SQL_REQUIRED.format(
                condition=cls.sql_is_empty.format(
                    column='NEW.' + identifier(colname)
                ),
                colname=literal_string(colname),
                error=literal_string(error),
            )

    @classmethod
    def sql_validate_rule(cls, info):
        """
        Override when type-related validation is required

        For constraints use ColumnConstraint subclasses instead
        """
        return


@_standard_column('text')
class TextColumn(ColumnType):
    label = _('Text')
    description = _('Unicode text of any length')
    example = _('free-form text')
    table_schema_type = 'string'
    table_schema_format = 'default'


@_standard_column('choice')
class ChoiceColumn(ColumnType):
    label = _('Choice')
    description = _('Choose one option from a fixed list')
    example = 'b1'
    datastore_type = 'text'
    table_schema_type = 'string'
    table_schema_format = 'default'
    table_schema_constraint = 'enum'
    form_snippet = 'choice.html'
    design_snippet = 'choice.html'

    @classmethod
    def choices(cls, info):
        """
        Comma-separated text field with choice values
        """
        choices = info.get('choices')
        if choices:
            return [c.strip() for c in choices.split(',')]
        return []

    _SQL_VALIDATE = '''
    IF {value} IS NOT NULL AND {value} <> ''
            AND NOT ({value} = ANY ({choices}))
        THEN
        errors := errors || ARRAY[[{colname}, 'Invalid choice: "'
            || replace({value}, E'\t', ' ') || '"']];
    END IF;
    '''

    @classmethod
    def sql_validate_rule(cls, info):
        """
        Copy choices into validation rule as a literal string array
        """
        colname = info['id']

        # \t is used when converting errors to string, remove any from data
        return cls._SQL_VALIDATE.format(
            value='NEW.' + identifier(colname),
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
    html_input_type = 'email'


@_standard_column('uri')
class URIColumn(ColumnType):
    label = _('URI')
    description = _('A uniform resource identifier (URL or URN)')
    example = 'https://example.com/page'
    datastore_type = 'text'
    table_schema_type = 'string'
    table_schema_format = 'uri'
    html_input_type = 'url'


@_standard_column('uuid')
class UUIDColumn(ColumnType):
    label = _('UUID')
    description = _('A universally unique identifier as hexadecimal')
    example = '213b972d-75c0-48b7-b14a-5a19eb58a1fa'
    datastore_type = 'uuid'
    table_schema_type = 'string'
    table_schema_format = 'uuid'
    sql_is_empty = "{column} IS NULL"


@_standard_column('numeric')
class NumericColumn(ColumnType):
    label = _('Numeric')
    description = _('Number with arbitrary precision (any number of '
                    'digits before and after the decimal)')
    example = '2.01'
    datastore_type = 'numeric'
    table_schema_type = 'number'
    sql_is_empty = "{column} IS NULL"


@_standard_column('integer')
class IntegerColumn(ColumnType):
    label = _('Integer')
    description = _('Whole numbers with no decimal')
    example = '21'
    datastore_type = 'int4'
    table_scema_type = 'integer'
    sql_is_empty = "{column} IS NULL"


@_standard_column('boolean')
class BooleanColumn(ColumnType):
    label = _('Boolean')
    description = _('True or false values')
    example = 'false'
    datastore_type = 'boolean'
    table_schema_type = 'boolean'
    sql_is_empty = "{column} IS NULL"


@_standard_column('json')
class JSONColumn(ColumnType):
    label = _('JSON')
    description = _('A JSON object')
    example = '{"key": "value"}'
    datastore_type = 'json'
    table_schema_type = 'object'
    sql_is_empty = "{column} IS NULL OR {column}::jsonb = 'null'::jsonb"


@_standard_column('date')
class DateColumn(ColumnType):
    label = _('Date')
    description = _('Date without time of day')
    example = '2024-01-01'
    datastore_type = 'date'
    table_schema_type = 'date'
    table_schema_format = 'fmt:YYYY-MM-DD'
    html_input_type = 'date'
    sql_is_empty = "{column} IS NULL"


@_standard_column('timestamp')
class TimestampColumn(ColumnType):
    label = _('Timestamp')
    description = _('Date and time without time zone')
    example = '2024-01-01 12:00:00'
    datastore_type = 'timestamp'
    table_schema_type = 'time'
    table_schema_format = 'fmt:YYYY-MM--DD hh:mm:ss'
    html_input_type = 'datetime-local'
    sql_is_empty = "{column} IS NULL"
