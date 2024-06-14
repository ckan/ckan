from __future__ import annotations

from typing import Type

from ckan import plugins

from ckanext.tabledesigner.interfaces import IColumnTypes
from ckanext.tabledesigner.column_types import ColumnType, IntegerColumn

from ckanext.datastore.backend.postgres import identifier, literal_string


class ExampleIColumnTypesPlugin(plugins.SingletonPlugin):
    plugins.implements(IColumnTypes)

    def column_types(self, existing_types: dict[str, Type[ColumnType]]):
        return dict(
            existing_types,
            star_rating=StarRatingColumn,
        )


def _(x: str):
    return x


class StarRatingColumn(IntegerColumn):
    """Example 1-5 star rating column"""
    label = _('Star Rating')
    description = _('Rating between 1-5 stars')
    datastore_type = 'int2'  # smallest int type (16-bits)
    form_snippet = 'choice.html'
    view_snippet = 'choice.html'

    def choices(self):
        return {
            '1': '★',
            '2': '★★',
            '3': '★★★',
            '4': '★★★★',
            '5': '★★★★★',
        }

    def choice_value_key(self, value: int | str) -> str:
        return str(value) if value else ''

    def sql_validate_rule(self):
        error = _('Rating must be between 1 and 5')
        return f'''
        IF NOT NEW.{identifier(self.colname)} BETWEEN 1 AND 5 THEN
            errors := errors || ARRAY[[
                {literal_string(self.colname)}, {literal_string(error)}]];
        END IF;
        '''
