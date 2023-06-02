
_ = lambda x: x

_standard_column_types = {}

def _standard_column(key):
    def register(cls):
        _standard_column_types[key] = cls
    return register


column_types = _standard_column_types  # FIXME: include plugin column types


class ColumnType:
    sql_is_empty = "{column} IS NULL"


@_standard_column('text')
class TextColumn(ColumnType):
    label = _('Text')
    description = _('Unicode text of any length')
    example = _('free-form text')
    datastore_type = 'text'
    table_schema_type = 'string'
    table_schema_format = 'default'
    sql_is_empty = "({column} = '') IS NOT FALSE"


@_standard_column('email')
class EmailColumn(ColumnType):
    label = _('Email Address')
    description = _('A single email address')
    example = 'user@example.com'
    datastore_type = 'text'
    table_schema_type = 'string'
    table_schema_format = 'email'
    sql_is_empty = "({column} = '') IS NOT FALSE"


@_standard_column('uri')
class URIColumn(ColumnType):
    label = _('URI')
    description = _('A uniform resource identifier (URL or URN)')
    example = 'https://example.com/page'
    datastore_type = 'text'
    table_schema_type = 'string'
    table_schema_format = 'uri'
    sql_is_empty = "({column} = '') IS NOT FALSE"


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
