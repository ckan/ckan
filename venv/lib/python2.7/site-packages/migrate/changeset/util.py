from migrate.changeset import SQLA_10

"""
Safe quoting method
"""

def safe_quote(obj):
    # this is the SQLA 0.9 approach
    if hasattr(obj, 'name') and hasattr(obj.name, 'quote'):
        return obj.name.quote
    else:
        return obj.quote


def fk_column_names(constraint):
    if SQLA_10:
        return [
            constraint.columns[key].name for key in constraint.column_keys]
    else:
        return [
            element.parent.name for element in constraint.elements]
