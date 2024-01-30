from collections import defaultdict

from ckan.types import Validator, Schema
from ckan.plugins.toolkit import get_validator
from ckanext.datastore.backend.postgres import identifier, literal_string

from . import column_types
from .excel import excel_literal


def _(x):
    return x


_standard_column_constraints = defaultdict(list)


def _standard_constraint(keys):
    def register(cls):
        for key in keys:
            _standard_column_constraints[key].append(cls)
        return cls
    return register


class ColumnConstraint:
    def __init__(self, ct):
    """
    ColumnConstraint subclasses define:
    - pl/pgsql rules for validating data on insert/update
    - validators for data dictionary field values
    - excel validation rules for ckanext-excelforms

    Use IColumnConstraints to add/modify column constraints available.
    """
    def __init__(self, ct: column_types.ColumnType):
        self.colname = ct.colname
        self.info = ct.info
        self.column_type = ct

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

        e.g.
        return {'tdmykey': [td_ignore, my_validator, td_pd]}
        #        ^ prefix   ^ ignore non-td          ^ store value
        """
        return {}


@_standard_constraint(['numeric', 'integer', 'date', 'timestamp'])
class RangeConstraint(ColumnConstraint):
    constraint_snippet = 'range.html'

    _SQL_CHECK_MIN = '''
    IF {value} < {minimum}::{type_} THEN
        errors := errors || ARRAY[[{colname}, {error} || ': "'
            || {minimum}::text || '"']];
    END IF;
    '''

    _SQL_CHECK_MAX = '''
    IF {value} > {maximum}::{type_} THEN
        errors := errors || ARRAY[[{colname}, {error} ||': "'
            || {maximum}::text || '"']];
    END IF;
    '''

    def sql_constraint_rule(self):
        sql = ''

        minimum = self.info.get('minimum')
        if minimum:
            sql += self._SQL_CHECK_MIN.format(
                colname=literal_string(self.colname),
                value='NEW.' + identifier(self.colname),
                minimum=literal_string(minimum),
                error=literal_string(_('Below minimum')),
                type_=self.column_type.datastore_type,
            )
        maximum = self.info.get('maximum')
        if maximum:
            sql += self._SQL_CHECK_MAX.format(
                colname=literal_string(self.colname),
                value='NEW.' + identifier(self.colname),
                maximum=literal_string(maximum),
                error=literal_string(_('Above maximum')),
                type_=self.column_type.datastore_type,
            )
        return sql

    def excel_constraint_rule(self):
        rules = []
        minimum = self.info.get('minimum')
        if minimum:
            rules.append('0>{_value_}-' + excel_literal(minimum))
        maximum = self.info.get('maximum')
        if maximum:
            rules.append('0<{_value_}-' + excel_literal(maximum))
            if minimum:
                return 'OR(' + ','.join(rules) + ')'
        return ''.join(rules)

    @classmethod
    def datastore_field_schema(
            cls, td_ignore: Validator, td_pd: Validator) -> Schema:
        """
        Check for valid range and types
        """
        ignore_empty = get_validator('ignore_empty')
        td_check_type = get_validator('tabledesigner_check_type')
        td_compare_min = get_validator('tabledesigner_compare_minimum')

        return {
            'tdminimum': [td_ignore, ignore_empty, td_check_type, td_pd],
            'tdmaximum': [
                td_ignore, ignore_empty, td_check_type, td_compare_min, td_pd
            ],
        }


@_standard_constraint(['text'])
class PatternConstraint(ColumnConstraint):
    constraint_snippet = 'pattern.html'

    _SQL_CHECK_PATTERN = '''
    IF regexp_match({value}, {pattern}) IS NULL THEN
        validation.errors := validation.errors ||
            ARRAY[{colname}, {error}];
    END IF;
    '''

    def sql_constraint_rule(self):
        pattern = self.info.get('pattern')
        if not pattern:
            return ''

        return self._SQL_CHECK_PATTERN.format(
            colname=literal_string(self.colname),
            value='NEW.' + identifier(self.colname),
            pattern=literal_string('^' + pattern + '$'),
            error=literal_string(
                _('Does not match pattern')),
            )

    @classmethod
    def datastore_field_schema(
            cls, td_ignore: Validator, td_pd: Validator) -> Schema:
        """
        Check for valid pattern
        """
        ignore_empty = get_validator('ignore_empty')
        td_check_pattern = get_validator('tabledesigner_check_pattern')

        return {
            'tdpattern': [td_ignore, ignore_empty, td_check_pattern, td_pd],
        }
