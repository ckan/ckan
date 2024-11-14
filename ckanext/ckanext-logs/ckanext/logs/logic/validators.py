import ckan.plugins.toolkit as tk


def logs_required(value):
    if not value or value is tk.missing:
        raise tk.Invalid("Required")
    return value


def get_validators():
    return {
        "logs_required": logs_required,
    }
