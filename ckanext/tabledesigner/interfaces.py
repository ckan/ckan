from __future__ import annotations

from typing import Type, List

from ckan.plugins import interfaces

from .column_types import ColumnType
from .column_constraints import ColumnConstraint


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
        plugins may modify types added/removed/updated by later plugins)

        ColumnType subclasses are used to set underlying datastore types,
        validation rules, input widget types, template snippets, choice
        lists, examples, help text and control other table designer
        features.
        """
        return existing_types


class IColumnConstraints(interfaces.Interface):
    """Custom Constraints for Table Designer Columns"""

    # earlier plugins override later plugins
    _reverse_iteration_order = True

    def column_constraints(
            self,
            existing_constraints: dict[str, List[Type[ColumnConstraint]]],
            column_types: dict[str, Type[ColumnType]],
            ) -> dict[str, List[Type[ColumnConstraint]]]:
        """
        return a {tdtype string value: [ColumnConstraint subclass, ...], ...}
        dict

        existing_constraints is the standard constraint dict, possibly modified
        by other IColumnConstraints plugins later in the plugin list (earlier
        plugins may modify constraints added/removed/updated by later plugins)

        The list of ColumnConstraint subclasses are applied, in order, to all
        columns with a matching tdtype value. ColumnConstraint subclasses may
        extend the design form and validation rules applied to a column.
        """
        return existing_constraints
