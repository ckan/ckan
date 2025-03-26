from __future__ import annotations

from typing import Type, List

from ckan.types import Validator, Schema
from ckan import plugins
from ckan.common import CKANConfig
from ckan.plugins.toolkit import add_template_directory, get_validator

from ckanext.tabledesigner.interfaces import IColumnConstraints
from ckanext.tabledesigner.column_types import ColumnType
from ckanext.tabledesigner.column_constraints import (
    ColumnConstraint)

from ckanext.datastore.backend.postgres import identifier, literal_string


class ExampleIColumnConstraintsPlugin(plugins.SingletonPlugin):
    plugins.implements(IColumnConstraints)
    plugins.implements(plugins.IConfigurer)

    def update_config(self, config: CKANConfig):
        add_template_directory(config, "templates")

    def column_constraints(
            self,
            existing_constraints: dict[str, List[Type[ColumnConstraint]]],
            column_types: dict[str, Type[ColumnType]],
            ) -> dict[str, List[Type[ColumnConstraint]]]:
        """Apply immutable constraint to all types"""
        return {
            tdtype: existing_constraints.get(
                tdtype, []
            ) + [ImmutableConstraint] for tdtype in column_types
        }


def _(x: str):
    return x


class ImmutableConstraint(ColumnConstraint):
    """Allow a field to be set once then not changed again"""
    constraint_snippet = 'immutable.html'
    view_snippet = 'immutable.html'

    def sql_constraint_rule(self):
        if not self.field.get('tdimmutable'):
            return ''

        icolname = identifier(self.colname)
        old_is_empty = self.column_type._SQL_IS_EMPTY.format(
            value='OLD.' + icolname
        )

        error = _('This field may not be changed')
        return f'''
        IF NOT ({old_is_empty}) AND NEW.{icolname} <> OLD.{icolname} THEN
            errors := errors || ARRAY[[
                {literal_string(self.colname)}, {literal_string(error)}]];
        END IF;
        '''

    @classmethod
    def datastore_field_schema(
            cls, td_ignore: Validator, td_pd: Validator) -> Schema:
        """
        Store tdimmutable setting in field
        """
        boolean_validator = get_validator('boolean_validator')
        return {
            'tdimmutable': [td_ignore, boolean_validator, td_pd],
        }
