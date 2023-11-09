from __future__ import annotations

from typing import Type, Callable, Any, List
from collections import defaultdict

from ckanext.datastore.backend.postgres import identifier, literal_string

from .column_types import ColumnType


def _(x: str):
    return x


_standard_column_constraints = defaultdict(list)


def _standard_constraint(
        keys: List[str]
        ) -> "Callable[[Type[ColumnConstraint]], Type[ColumnConstraint]]":
    def register(cls: "Type[ColumnConstraint]"):
        for key in keys:
            _standard_column_constraints[key].append(cls)
        return cls
    return register


class ColumnConstraint:
    def __new__(cls, *args: Any, **kwargs: Any):
        raise TypeError(
            'Column constraint classes are used directly, not instantiated'
        )


@_standard_constraint(['numeric', 'integer', 'date', 'timestamp'])
class RangeConstraint(ColumnConstraint):
    constraint_snippet = 'range.html'

    _SQL_VALIDATE_MIN = '''
    IF {value} < {minimum}::{type_} THEN
        errors := errors || ARRAY[[{colname}, 'Below minimum: "'
            || {minimum}::text || '"']];
    END IF;
    '''

    _SQL_VALIDATE_MAX = '''
    IF {value} > {maximum}::{type_} THEN
        errors := errors || ARRAY[[{colname}, 'Above maximum: "'
            || {maximum}::text || '"']];
    END IF;
    '''

    @classmethod
    def sql_constraint_rule(
            cls, info: dict[str, Any], column_type: Type[ColumnType]
            ):
        colname = info['id']
        sql = ''

        minimum = info.get('minimum')
        if minimum:
            sql += cls._SQL_VALIDATE_MIN.format(
                colname=literal_string(colname),
                value=f'NEW.{identifier(colname)}',
                minimum=literal_string(minimum),
                type_=column_type.datastore_type,
            )
        maximum = info.get('maximum')
        if maximum:
            sql += cls._SQL_VALIDATE_MAX.format(
                colname=literal_string(colname),
                value=f'NEW.{identifier(colname)}',
                maximum=literal_string(maximum),
                type_=column_type.datastore_type,
            )
        return sql
