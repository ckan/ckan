import paste.deploy

def setup_config(command, filename, section, vars):
    """
    Place any commands to setup ckan here.
    """
    conf = paste.deploy.appconfig('config:' + filename)
    paste.deploy.CONFIG.push_process_config({'app_conf':conf.local_conf,
                                             'global_conf':conf.global_conf})
    pass

