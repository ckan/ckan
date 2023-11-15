from ckanext.datastore.backend.postgres import identifier, literal_string

from .column_constraints import ColumnConstraint


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
    _SQL_IS_EMPTY = "({value} = '') IS NOT FALSE"

    def __init__(self, info, constraint_types):
        self.colname = info.get('id', '')
        self.info = info
        self._constraint_types = constraint_types

    def column_constraints(self) -> Iterator[ColumnConstraint]:
        for cct in self._constraint_types:
            yield cct(self)

    _SQL_REQUIRED = '''
    IF {condition} THEN
        errors := errors || ARRAY[
            {colname}, {error}
        ];
    END IF;
    '''

    def sql_required_rule(self):
        """
        Primary keys and required fields must not be empty
        """
        error = 'Missing value'

        if self.info.get('pkreq'):
            if self.info.get('pkreq') == 'pk':
                error = 'Primary key must not be empty'

            return self._SQL_REQUIRED.format(
                condition=self._SQL_IS_EMPTY.format(
                    column='NEW.' + identifier(colname)
                ),
                colname=literal_string(self.colname),
                error=literal_string(error),
            )

    def sql_validate_rule(self):
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

    def choices(self):
        """
        Comma-separated text field with choice values
        """
        choices = self.info.get('choices')
        if choices:
            return [c.strip() for c in choices.split(',')]
        return []

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
        Copy choices into validation rule as a literal string array
        """
        return self._SQL_VALIDATE.format(
            value='NEW.' + identifier(colname),
            colname=literal_string(self.colname),
            choices='ARRAY[' + ','.join(
                literal_string(c) for c in self.choices()
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

    # remove surrounding whitespace and validate
    _SQL_VALIDATE = '''
    {value} := trim({value});
    IF regexp_match({value}, {pattern}) IS NULL THEN
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
        return self._SQL_VALIDATE.format(
            value=f'NEW.{identifier(self.colname)}',
            pattern=literal_string(self._EMAIL_PATTERN),
            colname=literal_string(self.colname),
            error=literal_string(_('Invalid email')),
        )


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
    _SQL_IS_EMPTY = "{value} IS NULL"


@_standard_column('numeric')
class NumericColumn(ColumnType):
    label = _('Numeric')
    description = _('Number with arbitrary precision (any number of '
                    'digits before and after the decimal)')
    example = '2.01'
    datastore_type = 'numeric'
    table_schema_type = 'number'
    _SQL_IS_EMPTY = "{value} IS NULL"


@_standard_column('integer')
class IntegerColumn(ColumnType):
    label = _('Integer')
    description = _('Whole numbers with no decimal')
    example = '21'
    datastore_type = 'int4'
    table_scema_type = 'integer'
    _SQL_IS_EMPTY = "{value} IS NULL"


@_standard_column('boolean')
class BooleanColumn(ColumnType):
    label = _('Boolean')
    description = _('True or false values')
    example = 'false'
    datastore_type = 'boolean'
    table_schema_type = 'boolean'
    _SQL_IS_EMPTY = "{value} IS NULL"


@_standard_column('json')
class JSONColumn(ColumnType):
    label = _('JSON')
    description = _('A JSON object')
    example = '{"key": "value"}'
    datastore_type = 'json'
    table_schema_type = 'object'
    _SQL_IS_EMPTY = "{value} IS NULL OR {value}::jsonb = 'null'::jsonb"


@_standard_column('date')
class DateColumn(ColumnType):
    label = _('Date')
    description = _('Date without time of day')
    example = '2024-01-01'
    datastore_type = 'date'
    table_schema_type = 'date'
    table_schema_format = 'fmt:YYYY-MM-DD'
    html_input_type = 'date'
    _SQL_IS_EMPTY = "{value} IS NULL"


@_standard_column('timestamp')
class TimestampColumn(ColumnType):
    label = _('Timestamp')
    description = _('Date and time without time zone')
    example = '2024-01-01 12:00:00'
    datastore_type = 'timestamp'
    table_schema_type = 'time'
    table_schema_format = 'fmt:YYYY-MM--DD hh:mm:ss'
    html_input_type = 'datetime-local'
    _SQL_IS_EMPTY = "{value} IS NULL"
