# encoding: utf-8

import ckanext.datastore.logic.auth as auth


def datapusher_submit(context, data_dict):
    return auth.datastore_auth(context, data_dict)


def datapusher_status(context, data_dict):
    return auth.datastore_auth(context, data_dict)
