import ckan.plugins.toolkit as tk


@tk.auth_allow_anonymous_access
def {{cookiecutter.project_shortname}}_get_sum(context, data_dict):
    return {"success": True}


def get_auth_functions():
    return {
        "{{cookiecutter.project_shortname}}_get_sum": {{
            cookiecutter.project_shortname}}_get_sum,
    }
