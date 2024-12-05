import ckan.plugins.toolkit as tk


def statistical_org_required(value):
    if not value or value is tk.missing:
        raise tk.Invalid(tk._("Required"))
    return value


def get_validators():
    return {
        "statistical_org_required": statistical_org_required,
    }
