from flask import Blueprint


{{cookiecutter.project_shortname}} = Blueprint(
    "{{cookiecutter.project_shortname}}", __name__)


def page():
    return "Hello, {{cookiecutter.project_shortname}}!"


{{cookiecutter.project_shortname}}.add_url_rule(
    "/{{cookiecutter.project_shortname}}/page", view_func=page)


def get_blueprints():
    return [{{cookiecutter.project_shortname}}]
