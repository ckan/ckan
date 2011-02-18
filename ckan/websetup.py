"""Setup the ckan application"""
import logging

from ckan.config.environment import load_environment

log = logging.getLogger(__name__)

def setup_app(command, conf, vars):
    """Place any commands to setup ckan here"""
    load_environment(conf.global_conf, conf.local_conf)
    
    from ckan import model
    log.debug('Creating tables')
    model.repo.create_db()
    log.info('Creating tables: SUCCESS')

