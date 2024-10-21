import ckan.plugins as p
from flask import Flask
from ckan.common import g, request

# from .logic.actions import tracking_by_user
# from .logic import auth
import sqlalchemy as sa

class Task2Plugin(p.SingletonPlugin):
    p.implements(p.IMiddleware, inherit = True)
    # p.implements(p.IActions)
    # p.implements(p.IAuthFunctions)

    def make_middleware(self, app: Flask, config):
        @app.after_request  
        def after_request(response):
            
            url = request.environ['PATH_INFO']
            
            if '/dataset/' in url: 
                data_type = self.get_data_type(url)                 
                key = g.userobj.id
                sql = '''INSERT INTO tracking_raw
                     (user_key, url, tracking_type)
                     VALUES (%s, %s, %s)'''
                self.engine = sa.create_engine(config.get('sqlalchemy.url'))
                self.engine.execute(sql, key, url, data_type)

            return response

        return app
    
    def get_data_type(self, url):
        
        
        if 'resource' in url:
            data_type = 'resource'
            a = url.split('/resource/')[1].split('/')[0]
            print('a: ', a)
        else:
            data_type = 'page'  
        return data_type

    # def get_actions(self):
    #     return {
    #         'tracking_by_user': tracking_by_user
    #     }

    # def get_auth_functions(self):
    #     return auth.get_auth_functions()