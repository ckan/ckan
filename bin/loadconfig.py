import os

def load_config(path):
    # OLD: pylons 0.9.4 and before version ...
    # conf_file = os.path.abspath(path)
    # from paste.deploy import loadapp, CONFIG
    # import paste.deploy

    # conf = paste.deploy.appconfig('config:' + conf_file)
    # CONFIG.push_process_config({'app_conf': conf.local_conf,
    #   'global_conf': conf.global_conf}) 

    import paste.deploy
    conf = paste.deploy.appconfig('config:' + path)
    import ckan
    ckan.config.environment.load_environment(conf.global_conf,
            conf.local_conf)


