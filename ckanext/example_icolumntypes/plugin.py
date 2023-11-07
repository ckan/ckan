from __future__ import annotations

from typing import Any, Type

from ckan import plugins

from ckanext.tabledesigner.interfaces import IColumnTypes
from ckanext.tabledesigner.column_types import ColumnType, DateColumn

from ckanext.datastore.backend.postgres import identifier, literal_string


class ExampleIColumnTypesPlugin(plugins.SingletonPlugin):
    plugins.implements(IColumnTypes)

    def column_types(self, existing_types: dict[str, Type[ColumnType]]):
        return dict(
            existing_types,
            past_date=PastDateColumn,
        )


def _(x: str):
    return x


class PastDateColumn(DateColumn):
    """Date column that only accepts dates in the past"""
    label = _('Past Date')
    description = _('Date without time of day (must be in the past)')

    @classmethod
    def sql_validate_rule(cls, info: dict[str, Any]):
        colname = info['id']
        error = _('Date must be in the past')
        return f'''
            IF NEW.{identifier(colname)} > CURRENT_DATE THEN
                errors := errors || ARRAY[
                    [{literal_string(colname)}, {literal_string(error)}]];
            END IF;
        '''
