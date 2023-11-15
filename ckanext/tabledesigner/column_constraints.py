from collections import defaultdict

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
        self.colname = ct.colname
        self.info = ct.info
        self.column_type = ct


@_standard_constraint(['numeric', 'integer', 'date', 'timestamp'])
class RangeConstraint(ColumnConstraint):
    constraint_snippet = 'range.html'

    _SQL_VALIDATE_MIN = '''
    IF {value} < {minimum}::{type_} THEN
        errors := errors || ARRAY[[{colname}, {error} || ': "'
            || {minimum}::text || '"']];
    END IF;
    '''

    _SQL_VALIDATE_MAX = '''
    IF {value} > {maximum}::{type_} THEN
        errors := errors || ARRAY[[{colname}, {error} ||': "'
            || {maximum}::text || '"']];
    END IF;
    '''

    def sql_constraint_rule(self):
        sql = ''

        minimum = self.info.get('minimum')
        if minimum:
            sql += self._SQL_VALIDATE_MIN.format(
                colname=literal_string(self.colname),
                value='NEW.' + identifier(colname),
                minimum=literal_string(minimum),
                error=literal_string(_('Below minimum')),
                type_=self.column_type.datastore_type,
            )
        maximum = self.info.get('maximum')
        if maximum:
            sql += self._SQL_VALIDATE_MAX.format(
                colname=literal_string(self.colname),
                value='NEW.' + identifier(colname),
                maximum=literal_string(maximum),
                error=literal_string(_('Above maximum')),
                type_=self.column_type.datastore_type,
            )
        return sql

    def excel_constraint_rule(self) -> str:
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


@_standard_constraint(['text'])
class PatternConstraint(ColumnConstraint):
    constraint_snippet = 'pattern.html'

    _SQL_VALIDATE_PATTERN = '''
    BEGIN
        IF regexp_match({value}, {pattern}) IS NULL THEN
            validation.errors := validation.errors ||
                ARRAY[{colname}, {error}];
        END IF;
    EXCEPTION
        WHEN invalid_regular_expression THEN
        validation.errors := validation.errors || ARRAY[{colname}, {invalid}];
    END;
    '''

    def sql_constraint_rule(self) -> str:
        pattern = self.info.get('pattern')
        if not pattern:
            return ''

        return self._SQL_VALIDATE_PATTERN.format(
            colname=literal_string(self.colname),
            value=f'NEW.{identifier(self.colname)}',
            pattern=literal_string('^' + pattern + '$'),
            error=literal_string(
                _('Does not match pattern') + ': ' + pattern),
            invalid=literal_string(
                _('Data dictionary field pattern is invalid')
            ),
        )
