from ckan import authz
from ckan.lib import jobs as rq_jobs

import ckanext.datastore.logic.auth as auth


def xloader_submit(context, data_dict):
    # only sysadmins can specify a custom processing queue
    custom_queue = data_dict.get('queue')
    if custom_queue and custom_queue != rq_jobs.DEFAULT_QUEUE_NAME:
        return authz.is_authorized('config_option_update', context, data_dict)
    return auth.datastore_auth(context, data_dict)


def xloader_status(context, data_dict):
    return auth.datastore_auth(context, data_dict)
