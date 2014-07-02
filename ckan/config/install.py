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
            'ckan_sqlalchemy_url': os.environ.get(
                'ckan_sqlalchemy_url',
                'postgresql://ckan_default:pass@localhost/ckan_default'),
            'ckan_beaker_session_type': os.environ.get(
                'ckan_beaker_session_type', 'file'),
            'ckan_beaker_session_url': os.environ.get(
                'ckan_beaker_session_url', ''),
            'ckan_datastore_write_url': os.environ.get(
                'ckan_datastore_write_url',
                'postgresql://ckan_default:pass@localhost/datastore_default'),
            'ckan_datastore_read_url': os.environ.get(
                'ckan_datastore_read_url',
                ('postgresql://datastore_default:pass@localhost/datastore_def'
                 'ault')),
            'ckan_datapusher_url': os.environ.get(
                'ckan_datapusher_url', 'http://127.0.0.1:8800/'),
            'ckan_solr_url': os.environ.get(
                'ckan_solr_url', 'http://127.0.0.1:8983/solr'),
            'ckan_email_to': os.environ.get(
                'ckan_email_to', 'you@yourdomain.com'),
            'ckan_error_email_from': os.environ.get(
                'ckan_error_email_from', 'paste@localhost'),
            'ckan_site_id': os.environ.get('ckan_site_id', 'default'),
            'ckan_site_url': os.environ.get('ckan_site_url', ''),
            'ckan_plugins': os.environ.get(
                'ckan_plugins', 'stats text_preview recline_preview'),
            'ckan_site_title': os.environ.get('ckan_site_title', 'CKAN'),
        }
        vars.update(environment_variables)

        return super(CKANInstaller, self).config_content(command, vars)
