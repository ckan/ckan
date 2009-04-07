"""Setup the ckan application"""
import logging

from paste.deploy import appconfig
from pylons import config

from ckan.config.environment import load_environment

log = logging.getLogger(__name__)

def setup_config(command, filename, section, vars):
    """Place any commands to setup ckan here"""
    conf = appconfig('config:' + filename)
    load_environment(conf.global_conf, conf.local_conf)
    
    from ckan import model
    log.info('Creating tables')
    model.repo.create_db()
    model.repo.init_db()
    log.info('Creating tables: SUCCESS')

