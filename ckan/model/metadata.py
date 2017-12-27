# encoding: utf-8

"""Wrapper for SqlAchemy MetaData

Keep a consistent set of metadata for CKAN.
"""

from sqlalchemy import MetaData
from ckan.common import config as ckan_config


class CkanMetaData(MetaData):
    """CKAN custom metadata

    Allow for setting metadata from CKAN's own configuration.

    """

    def __init__(self, *args, **kwargs):
        schema = ckan_config.get(u'ckan.migrations.target_schema')
        if u'schema' not in kwargs and schema:
            kwargs[u'schema'] = schema

        super(CkanMetaData, self).__init__(*args, **kwargs)
