import os

import pylons.config
import webhelpers

from ckan.config.routing import make_map

def load_environment(global_conf={}, app_conf={}):
    map = make_map(global_conf, app_conf)
    # Setup our paths
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = {'root_path': root_path,
             'controllers': os.path.join(root_path, 'controllers'),
             'templates': [os.path.join(root_path, path) for path in \
                           ('components', 'templates')],
             'static_files': os.path.join(root_path, 'public')
             }
    
    # The following template options are passed to your template engines
    tmpl_options = {}
    tmpl_options['myghty.log_errors'] = True
    tmpl_options['myghty.escapes'] = dict(l=webhelpers.auto_link, s=webhelpers.simple_format)
    
    # Add your own template options config options here, note that all config options will override
    # any Pylons config options
    
    # Return our loaded config object
    return pylons.config.Config(tmpl_options, map, paths)
