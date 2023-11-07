from __future__ import annotations

from typing import Type

from ckan.plugins import interfaces

from .column_types import ColumnType


class IColumnTypes(interfaces.Interface):
    """Custom Column Types for Table Designer"""

    # earlier plugins override later plugins
    _reverse_iteration_order = True

    def column_types(
            self, existing_types: dict[str, Type[ColumnType]]
            ) -> dict[str, Type[ColumnType]]:
        """
        return a {tdtype string value: ColumnType subclasses, ...} dict

        existing_types is the standard column types dict, possibly modified
        by other IColumnTypes plugins later in the plugin list (earlier
        plugins may modify types added/remove/updated by later plugins)

        ColumnType subclasses are used to set underlying datastore types,
        validation rules, input widget types, template snippets, choice
        lists, examples, help text and control other table designer
        features.
        """
        return existing_types
