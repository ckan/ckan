import re
import os

from pylons.util import PylonsInstaller

import ckan


class CKANInstaller(PylonsInstaller):

    # The paster make-config command calls this method, e.g.
    # paster make-config ckan /etc/ckan/default/development.ini
    def config_content(self, command, vars):
        '''Write a CKAN config file to the filesystem.

        The values for certain config settings will be read from environment
        variables if the environment variables are set, otherwise defaults will
        be used. This is particularly useful for automated install/deployment
        tools that need to create a config file with certain settings in it.

        The names of the environment variables are based on the names of the
        config settings in the config file, but:

        * Each . in the config setting name is replaced with an _ in the
          environment variable name (because environment variable names can't
          contain .'s).

        * The environment variable names always begin with 'ckan_', even if
          some of the config setting names don't (to prevent clasing with
          environment variables from other programs).

        At the time of writing, the following environment variables are
        supported:

        ckan_sqlalchemy_url: The :ref:`sqlalchemy.url` setting.

        ckan_beaker_session_type: The :ref:`beaker.session.type` setting.

        ckan_beaker_session_url: The :ref:`beaker.session.url` setting.

        ckan_datastore_write_url: The :ref:`ckan.datastore.write_url` setting.

        ckan_datastore_read_url: The :ref:`ckan.datastore.read_url` setting.

        ckan_datapusher_url: The :ref:`ckan.datapusher.url` setting.

        ckan_solr_url: The :ref:`solr_url` setting.

        ckan_email_to: The :ref:`email_to` setting.

        ckan_error_email_from: The :ref:`error_email_from` setting.

        ckan_site_id: The :ref:`ckan.site_id` setting.

        ckan_site_url: The :ref:`ckan.site_url` setting.

        ckan_plugins: The :ref:`ckan.plugins` setting.

        ckan_site_title: The :ref:`ckan.site_title` setting.

        But see :py:meth:`CKANInstaller.config_content` in
        ``ckan/config/install.py`` for the definitive list of supported
        environment variables.

        '''
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
                'postgresql://datastore_default:pass@localhost/datastore_default'),
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
