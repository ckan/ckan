"""
Setup your Routes options here
"""
import os
from routes import Mapper

def make_map(global_conf={}, app_conf={}):
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    map = Mapper(directory=os.path.join(root_path, 'controllers'))
    
    # This route handles displaying the error page and graphics used in the 404/500
    # error pages. It should likely stay at the top to ensure that the error page is
    # displayed properly.
    map.connect('error/:action/:id', controller='error')
    
    # Define your routes. The more specific and detailed routes should be defined first,
    # so they may take precedent over the more generic routes. For more information, refer
    # to the routes manual @ http://routes.groovie.org/docs/
    map.connect(':controller/:action/:id')
    map.connect('*url', controller='template', action='view')

    return map
