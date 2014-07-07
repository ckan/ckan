import re
import os

from pylons.util import PylonsInstaller

import ckan


class CKANInstaller(PylonsInstaller):

    # The paster make-config command calls this method, e.g.
    # paster make-config ckan /etc/ckan/default/development.ini
    def config_content(self, command, vars):
        ckan_version = ckan.__version__
        ckan_base_version = re.sub('[^0-9\.]', '', ckan_version)
        if ckan_base_version == ckan_version:
            ckan_doc_version = 'ckan-{0}'.format(ckan_version)
        else:
            ckan_doc_version = 'latest'

        vars.setdefault('doc_version', ckan_doc_version)

        # Optionally read the values for certain config settings from
        # environment variables.
        environment_variables = {
            'CKAN_SQLALCHEMY_URL': os.environ.get(
                'CKAN_SQLALCHEMY_URL',
                'postgresql://ckan_default:pass@localhost/ckan_default'),
            'CKAN_BEAKER_SESSION_TYPE': os.environ.get(
                'CKAN_BEAKER_SESSION_TYPE', 'file'),
            'CKAN_BEAKER_SESSION_URL': os.environ.get(
                'CKAN_BEAKER_SESSION_URL', ''),
            'CKAN_DATASTORE_WRITE_URL': os.environ.get(
                'CKAN_DATASTORE_WRITE_URL',
                'postgresql://ckan_default:pass@localhost/datastore_default'),
            'CKAN_DATASTORE_READ_URL': os.environ.get(
                'CKAN_DATASTORE_READ_URL',
                ('postgresql://datastore_default:pass@localhost/datastore_def'
                 'ault')),
            'CKAN_DATAPUSHER_URL': os.environ.get(
                'CKAN_DATAPUSHER_URL', 'Http://127.0.0.1:8800/'),
            'CKAN_SOLR_URL': os.environ.get(
                'CKAN_SOLR_URL', 'HTTP://127.0.0.1:8983/solr'),
            'CKAN_EMAIL_TO': os.environ.get(
                'CKAN_EMAIL_TO', 'you@yourdomain.com'),
            'CKAN_ERROR_EMAIL_FROM': os.environ.get(
                'CKAN_ERROR_EMAIL_FROM', 'paste@localhost'),
            'CKAN_SITE_ID': os.environ.get('CKAN_SITE_ID', 'default'),
            'CKAN_SITE_URL': os.environ.get('CKAN_SITE_URL', ''),
            'CKAN_PLUGINS': os.environ.get(
                'CKAN_PLUGINS', 'stats text_preview recline_preview'),
            'CKAN_SITE_TITLE': os.environ.get('CKAN_SITE_TITLE', 'CKAN'),
        }
        vars.update(environment_variables)

        return super(CKANInstaller, self).config_content(command, vars)
