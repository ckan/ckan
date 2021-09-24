
def {{cookiecutter.project_shortname}}_hello():
    return "Hello, {{cookiecutter.project_shortname}}!"


def get_helpers():
    return {
        "{{cookiecutter.project_shortname}}_hello": {{
            cookiecutter.project_shortname
        }}_hello,
    }
