import ckan.plugins as p
from flask import Flask
from ckan.common import g, request

from .logic.actions import tracking_by_user, tracking_urls_and_counts
from .logic import auth
import sqlalchemy as sa
import re 
from ckan.types import CKANApp
from .helpers import generate_user_key, get_data_type


class API_Tracking_Plugin(p.SingletonPlugin):
    p.implements(p.IMiddleware, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)

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
            'tracking_urls_and_counts': tracking_urls_and_counts
        }

    def get_auth_functions(self):
        return auth.get_auth_functions()
