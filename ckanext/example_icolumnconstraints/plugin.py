from __future__ import annotations

from typing import Type, List

from ckan import plugins
from ckan.common import CKANConfig
from ckan.plugins import toolkit

from ckanext.tabledesigner.interfaces import IColumnConstraints
from ckanext.tabledesigner.column_types import ColumnType
from ckanext.tabledesigner.column_constraints import (
    ColumnConstraint)

from ckanext.datastore.backend.postgres import identifier, literal_string


class ExampleIColumnConstraintsPlugin(plugins.SingletonPlugin):
    plugins.implements(IColumnConstraints)
    plugins.implements(plugins.IConfigurer)

    def update_config(self, config: CKANConfig):
        toolkit.add_template_directory(config, "templates")

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

    def sql_constraint_rule(self):
        if not self.info.get('immutable'):
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
