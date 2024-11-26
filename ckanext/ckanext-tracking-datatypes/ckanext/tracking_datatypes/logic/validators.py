import ckan.plugins.toolkit as tk


def tracking_datatypes_required(value):
    if not value or value is tk.missing:
        raise tk.Invalid(tk._("Required"))
    return value


def get_validators():
    return {
        "tracking_datatypes_required": tracking_datatypes_required,
    }
