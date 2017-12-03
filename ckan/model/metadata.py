# encoding: utf-8

from sqlalchemy import MetaData
from ckan.common import config as ckan_config

class CkanMetaData(MetaData):
    """CKAN custom metadata

    Allow for setting metadata from CKAN's own configuration.

    """

    def __init__(self, *args, **kwargs):
        schema = ckan_config.get('ckan.migrations.target_schema')
        if 'schema' not in kwargs and schema:
            kwargs['schema'] = schema

        super(CkanMetaData, self).__init__(*args, **kwargs)
