from math import log

import requests
from ckan.lib.base import render
import ckan.plugins as p
from flask import Flask
from ckan.common import g, request

from .logic.actions import tracking_by_user, tracking_urls_and_counts, statistical_org_get_sum, statistical_field_get_sum
from .logic import auth
import sqlalchemy as sa
import re 
from ckan.types import CKANApp
from .helpers import generate_user_key, get_data_type
import ckan.plugins.toolkit as toolkit
from ckan.common import CKANConfig
import ckan.plugins.toolkit as toolkit
import ckanext.api_tracking.views as views
from ckan.lib.plugins import DefaultTranslation


class API_Tracking_Plugin(p.SingletonPlugin, DefaultTranslation):
    p.implements(p.IMiddleware, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IConfigurer)
    p.implements(p.IBlueprint)
    p.implements(p.ITranslation)
   
    def get_blueprint(self):
        return views.get_blueprints()
    
    def update_config(self, config: CKANConfig):

        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        # 'templates' is the path to the templates dir, relative to this
        # plugin.py file.
        toolkit.add_template_directory(config, 'templates')
        # toolkit.add_public_directory(config, 'ckanext/api_tracking/assets')
        toolkit.add_resource("assets", "api_tracking")

    def make_middleware(self, app: CKANApp, config):
        @app.after_request
        def after_request(response):
            if config.get('ckan.tracking_enabled'):
                try:
                    url = request.environ.get('PATH_INFO', '')
                    pattern = r'^(/dataset/.*)'
                    match = re.match(pattern, url)
                
                    if match:
                        data_type = get_data_type(url)
                        if data_type:
                            key = g.userobj.id if g.userobj else generate_user_key(request.environ)
                            sql = '''INSERT INTO tracking_raw (user_key, url, tracking_type) VALUES (%s, %s, %s)'''
                        
                            try:
                                self.engine = sa.create_engine(config.get('sqlalchemy.url'))
                                self.engine.execute(sql, key, url, data_type)
                            except Exception as db_err:
                                app.logger.error(f"Database error: {db_err}")
                except Exception as e:
                    app.logger.error(f"Error processing request: {e}")   
            return response
        
        return app

    def get_actions(self):
        return {
            'tracking_by_user': tracking_by_user,
            'tracking_urls_and_counts': tracking_urls_and_counts,
            'statistical_org_get_sum': statistical_org_get_sum,
            'statistical_field_get_sum': statistical_field_get_sum
        }
        
    def get_auth_functions(self):
        return auth.get_auth_functions()

    