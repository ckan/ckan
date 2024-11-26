import ckan.plugins as plugins
from ckan.plugins.interfaces import IActions, IAuthFunctions
import ckan.plugins.toolkit as toolkit
from .logic import auth
from ckan.common import g, request
from ckan.types import CKANApp
from .logic.action import resource_access_by_date

# import ckanext.tracking_datatypes.cli as cli
# import ckanext.tracking_datatypes.helpers as helpers
# import ckanext.tracking_datatypes.views as views
# from ckanext.tracking_datatypes.logic import (
#     action, auth, validators
# )


class TrackingDatatypesPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(IActions)
    plugins.implements(IAuthFunctions)
    
    # plugins.implements(plugins.IAuthFunctions)
    # plugins.implements(plugins.IActions)
    # plugins.implements(plugins.IBlueprint)
    # plugins.implements(plugins.IClick)
    # plugins.implements(plugins.ITemplateHelpers)
    # plugins.implements(plugins.IValidators)
    

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "tracking_datatypes")

    # def make_middleware(self, app: CKANApp, config):
    #     @app.after_request
    #     def after_request(response):
    #         if config.get('ckan.tracking_enabled'):
    #             try:
    #                 url = request.environ.get('PATH_INFO', '')
    #                 pattern = r'^(/dataset/.*)'
    #                 match = re.match(pattern, url)
                
    #                 if match:
    #                     data_type = get_data_type(url)
    #                     if data_type:
    #                         key = g.userobj.id if g.userobj else generate_user_key(request.environ)
    #                         sql = '''INSERT INTO tracking_raw (user_key, url, tracking_type) VALUES (%s, %s, %s)'''
                        
    #                         try:
    #                             self.engine = sa.create_engine(config.get('sqlalchemy.url'))
    #                             self.engine.execute(sql, key, url, data_type)
    #                         except Exception as db_err:
    #                             app.logger.error(f"Database error: {db_err}")
    #             except Exception as e:
    #                 app.logger.error(f"Error processing request: {e}")   
    #         return response
        
    #     return app
    
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
    
    def get_actions(self):
        return {
            'resource_access_by_date': resource_access_by_date
        }

    def get_auth_functions(self):
        return auth.get_auth_functions()
    