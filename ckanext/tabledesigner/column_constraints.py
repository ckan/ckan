from collections import defaultdict

from ckanext.datastore.backend.postgres import identifier, literal_string

from .column_types import ColumnType


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
    def __new__(cls, *args, **kwargs):
        raise TypeError(
            'Column constraint classes are used directly, not instantiated'
        )


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

    @classmethod
    def sql_constraint_rule(cls, info, column_type):
        colname = info['id']
        sql = ''

        minimum = info.get('minimum')
        if minimum:
            sql += cls._SQL_VALIDATE_MIN.format(
                colname=literal_string(colname),
                value='NEW.' + identifier(colname),
                minimum=literal_string(minimum),
                error=literal_string(_('Below minimum')),
                type_=column_type.datastore_type,
            )
        maximum = info.get('maximum')
        if maximum:
            sql += cls._SQL_VALIDATE_MAX.format(
                colname=literal_string(colname),
                value='NEW.' + identifier(colname),
                maximum=literal_string(maximum),
                error=literal_string(_('Above maximum')),
                type_=column_type.datastore_type,
            )
        return sql


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

    @classmethod
    def sql_constraint_rule(
            cls, info: dict[str, Any], column_type: Type[ColumnType]
            ):
        colname = info['id']
        pattern = info.get('pattern')
        if not pattern:
            return

        return cls._SQL_VALIDATE_PATTERN.format(
            colname=literal_string(colname),
            value=f'NEW.{identifier(colname)}',
            pattern=literal_string('^' + pattern + '$'),
            error=literal_string(_('Does not match pattern')),
            invalid=literal_string(
                _('Data dictionary field pattern is invalid')
            ),
        )
