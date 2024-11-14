import logging

import logstash

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckanext.logs.views as views
from ckan.lib.plugins import DefaultTranslation
from ckanext.logs.logic import action, auth

log = logging.getLogger(__name__)

CONFIG_FROM_ENV_VARS = {
    'logstash.kind': 'CKAN_LOGSTASH_KIND',
    'logstash.host': 'CKAN_LOGSTASH_HOST',
    'logstash.port': 'CKAN_LOGSTASH_PORT',
    'logstash.configure_logging': 'CKAN_LOGSTASH_CONFIGURE_LOGGING',
    'logstash.log_level': 'CKAN_LOGSTASH_LOG_LEVEL',
}

class LogsPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IMiddleware, inherit=True)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.ITranslation, inherit=True)
    
    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "logs")
        # toolkit.add_ckan_admin_tab(
        #     config_, u'logs.index',
        #     toolkit._(u'Logs')
        # )

    # IAuthFunctions

    def get_auth_functions(self):
        return auth.get_auth_functions()

    # IActions

    def get_actions(self):
        return action.get_actions()

    # IBlueprint

    def get_blueprint(self):
        return views.get_blueprints()

    # IMiddleware

    def make_middleware(self, app, config): # type: ignore
        """ implements make_middleware """
        self._configure_logging(config)
        return app
    
    def make_error_log_middleware(self, app, config): # type: ignore
        """ implements make_error_log_middleware """
        self._configure_logging(config)
        return app
    
    def _configure_logging(self, config): # type: ignore
        
        '''
        Configure the Logstash log handler to the specified level
        '''
        logstash_host = config.get('ckan.logstash.host')
        logstash_port = int(config.get('ckan.logstash.port') or 5959)
        logstash_kind = config.get('ckan.logstash.kind')
        logstash_kind = logstash_kind or ''
        logstash_kind = logstash_kind.lower()
        logstash_messagetype = config.get('ckan.logstash.message_type','opendata')
        
        if logstash_kind == 'tcp':
            handler = logstash.TCPLogstashHandler(
                logstash_host, logstash_port, version=1
            )
        elif logstash_kind == 'udp':
            handler = logstash.LogstashHandler(
                logstash_host, logstash_port, version=1
            )
        elif logstash_kind == 'ampq':
            handler = logstash.AMQPLogstashHandler(
                host=logstash_host,  version=1
            )
        else:
            log.warning('Unknown logstash kind specified (%s)',
                        config.get('ckan.logstash.kind'))
            return

        handler.setLevel(logging.NOTSET)
        handler.formatter.host = config.get('ckan.site_url') # type: ignore
        handler.formatter.message_type = logstash_messagetype # type: ignore

        logging.info('Setting up Logstash logger')

        loggers = ['', 'ckan', 'ckanext', 'logstash.errors', __name__]
        logstash_log_level = config.get('ckan.logstash.log_level', logging.DEBUG)
        for name in loggers:
            logger = logging.getLogger(name)
            logger.addHandler(handler)
            logger.setLevel(logstash_log_level)

        log.debug('Set-up Logstash logger with level %s', logstash_log_level)