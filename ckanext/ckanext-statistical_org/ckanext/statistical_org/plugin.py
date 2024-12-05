import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from .logic import auth
from .logic.action import statistical_org_get_sum
# import ckanext.statistical_org.cli as cli
# import ckanext.statistical_org.helpers as helpers
# import ckanext.statistical_org.views as views
# from ckanext.statistical_org.logic import (
#     action, auth, validators
# )


class StatisticalOrgPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer) 
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IActions)
    # plugins.implements(plugins.IBlueprint)
    # plugins.implements(plugins.IClick)
    # plugins.implements(plugins.ITemplateHelpers)
    # plugins.implements(plugins.IValidators)
    

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "statistical_org")

    
    # IAuthFunctions

    def get_auth_functions(self):
        return auth.get_auth_functions()

    # IActions

    def get_actions(self):
        return {
            'statistical_org_get_sum': statistical_org_get_sum
        }

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
    
