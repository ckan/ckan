import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

{%if cookiecutter.include_examples|int%}
# import ckanext.{{cookiecutter.project_shortname}}.cli as cli
# import ckanext.{{cookiecutter.project_shortname}}.helpers as helpers
# import ckanext.{{cookiecutter.project_shortname}}.views as views
# from ckanext.{{cookiecutter.project_shortname}}.logic import (
#     action, auth, validators
# )

{%endif%}
class {{cookiecutter.plugin_class_name}}(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    {%if cookiecutter.include_examples|int%}
    # plugins.implements(plugins.IAuthFunctions)
    # plugins.implements(plugins.IActions)
    # plugins.implements(plugins.IBlueprint)
    # plugins.implements(plugins.IClick)
    # plugins.implements(plugins.ITemplateHelpers)
    # plugins.implements(plugins.IValidators)
    {%endif%}

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "{{cookiecutter.project_shortname}}")

    {%if cookiecutter.include_examples|int%}
    # IAuthFunctions

    # def get_auth_functions(self):
    #     return auth.get_auth_functions()

    # IActions

    # def get_actions(self):
    #     return action.get_actions()

    # IBlueprint

    # def get_blueprint(self):
    #     return views.get_blueprints()

    # IClick

    # def get_commands(self):
    #     return cli.get_commands()

    # ITemplateHelpers

    # def get_helpers(self):
    #     return helpers.get_helpers()

    # IValidators

    # def get_validators(self):
    #     return validators.get_validators()
    {%endif%}
