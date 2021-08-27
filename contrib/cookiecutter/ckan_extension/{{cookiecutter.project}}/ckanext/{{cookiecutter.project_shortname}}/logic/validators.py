import ckan.plugins.toolkit as tk


def {{cookiecutter.project_shortname}}_required(value):
    if not value or value is tk.missing:
        raise tk.Invalid(tk._("Required"))
    return value


def get_validators():
    return {
        "{{cookiecutter.project_shortname}}_required": {{
            cookiecutter.project_shortname}}_required,
    }
