import ckan.plugins.toolkit as tk
import ckanext.{{cookiecutter.project_shortname}}.logic.schema as schema


@tk.side_effect_free
def {{cookiecutter.project_shortname}}_get_sum(context, data_dict):
    tk.check_access(
        "{{cookiecutter.project_shortname}}_get_sum", context, data_dict)
    data, errors = tk.navl_validate(
        data_dict, schema.{{
            cookiecutter.project_shortname}}_get_sum(), context)

    if errors:
        raise tk.ValidationError(errors)

    return {
        "left": data["left"],
        "right": data["right"],
        "sum": data["left"] + data["right"]
    }


def get_actions():
    return {
        '{{cookiecutter.project_shortname}}_get_sum': {{
            cookiecutter.project_shortname
        }}_get_sum,
    }
