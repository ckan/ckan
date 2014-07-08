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

        # The values for the config settings in the default config file are
        # read from environment variables, or fall back to defaults if the
        # environment variables aren't set.
        #
        # Note: This doesn't necessarily mean that all CKAN config settings can
        # be set in the config file by environment variables, some settings are
        # missing from the config file template entirely.
        #
        # Note: If you're adding new settings to the config file, a setting's
        # environment variable name is formed from its config file setting name
        # by:
        #
        # 1. Putting it in ALL_CAPS
        # 2. Replacing any .'s with _'s (environment variable names can't
        #    contain _'s)
        # 3. Appending CKAN_ to the start, if it's not there already.
        environment_variables = {
            'CKAN_SQLALCHEMY_URL': os.environ.get(
                'CKAN_SQLALCHEMY_URL',
                'postgresql://ckan_default:pass@localhost/ckan_default'),
            'CKAN_BEAKER_SESSION_TYPE': os.environ.get(
                'CKAN_BEAKER_SESSION_TYPE', 'file'),
            'CKAN_BEAKER_SESSION_URL': os.environ.get(
                'CKAN_BEAKER_SESSION_URL', ''),
            'CKAN_BEAKER_SESSION_KEY': os.environ.get(
                'CKAN_BEAKER_SESSION_KEY', 'ckan'),
            'CKAN_DATASTORE_WRITE_URL': os.environ.get(
                'CKAN_DATASTORE_WRITE_URL',
                'postgresql://ckan_default:pass@localhost/datastore_default'),
            'CKAN_DATASTORE_READ_URL': os.environ.get(
                'CKAN_DATASTORE_READ_URL', 'postgresql://datastore_default:'
                'pass@localhost/datastore_default'),
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
            'CKAN_CACHE_DIR': os.environ.get(
                'CKAN_CACHE_DIR', '/tmp/%(ckan.site_id)s/'),
            'CKAN_WHO_CONFIG_FILE': os.environ.get(
                'CKAN_WHO_CONFIG_FILE', '%(here)s/who.ini'),
            'CKAN_WHO_LOG_LEVEL': os.environ.get(
                'CKAN_WHO_LOG_LEVEL', 'warning'),
            'CKAN_WHO_LOG_FILE': os.environ.get(
                'CKAN_WHO_LOG_FILE', '%(cache_dir)s/who_log.ini'),
            'CKAN_AUTH_ANON_CREATE_DATASET': os.environ.get(
                'CKAN_AUTH_ANON_CREATE_DATASET', 'false'),
            'CKAN_AUTH_CREATE_UNOWNED_DATASET': os.environ.get(
                'CKAN_AUTH_CREATE_UNOWNED_DATASET', 'true'),
            'CKAN_AUTH_CREATE_DATASET_IF_NOT_IN_ORGANIZATION': os.environ.get(
                'CKAN_AUTH_CREATE_DATASET_IF_NOT_IN_ORGANIZATION', 'true'),
            'CKAN_AUTH_USER_CREATE_GROUPS': os.environ.get(
                'CKAN_AUTH_USER_CREATE_GROUPS', 'true'),
            'CKAN_AUTH_USER_CREATE_ORGANIZATIONS': os.environ.get(
                'CKAN_AUTH_USER_CREATE_ORGANIZATIONS', 'true'),
            'CKAN_AUTH_USER_DELETE_GROUPS': os.environ.get(
                'CKAN_AUTH_USER_DELETE_GROUPS', 'true'),
            'CKAN_AUTH_USER_DELETE_ORGANIZATIONS': os.environ.get(
                'CKAN_AUTH_USER_DELETE_ORGANIZATIONS', 'true'),
            'CKAN_AUTH_CREATE_USER_VIA_API': os.environ.get(
                'CKAN_AUTH_CREATE_USER_VIA_API', 'false'),
            'CKAN_AUTH_CREATE_USER_VIA_WEB': os.environ.get(
                'CKAN_AUTH_CREATE_USER_VIA_WEB', 'true'),
            'CKAN_AUTH_ROLES_THAT_CASCADE_TO_SUB_GROUPS': os.environ.get(
                'CKAN_AUTH_ROLES_THAT_CASCADE_TO_SUB_GROUPS', 'admin'),
            'CKAN_SITE_LOGO': os.environ.get(
                'CKAN_SITE_LOGO', '/base/images/ckan-logo.png'),
            'CKAN_SITE_DESCRIPTION': os.environ.get(
                'CKAN_SITE_DESCRIPTION', ''),
            'CKAN_FAVICON': os.environ.get(
                'CKAN_FAVICON', '/images/icons/ckan.ico'),
            'CKAN_GRAVATAR_DEFAULT': os.environ.get(
                'CKAN_GRAVATAR_DEFAULT', 'identicon'),
            'CKAN_PREVIEW_DIRECT': os.environ.get(
                'CKAN_PREVIEW_DIRECT', 'png jpg gif'),
            'CKAN_PREVIEW_LOADABLE': os.environ.get(
                'CKAN_PREVIEW_LOADABLE', 'html htm rdf+xml owl+xml xml n3 '
                'n-triples turtle plain atom csv tsv rss txt json'),
            'CKAN_LOCALE_DEFAULT': os.environ.get('CKAN_LOCALE_DEFAULT', 'en'),
            'CKAN_LOCALE_ORDER': os.environ.get(
                'CKAN_LOCALE_ORDER', 'en pt_BR ja it cs_CZ ca es fr el sv sr '
                'sr@latin no sk fi ru de pl nl bg ko_KR hu sa sl lv'),
            'CKAN_LOCALES_OFFERED': os.environ.get('CKAN_LOCALES_OFFERED', ''),
            'CKAN_LOCALES_FILTERED_OUT': os.environ.get(
                'CKAN_LOCALES_FILTERED_OUT', 'en_GB'),
            'CKAN_FEEDS_AUTHORITY_NAME': os.environ.get(
                'CKAN_FEEDS_AUTHORITY_NAME', ''),
            'CKAN_FEEDS_DATE': os.environ.get('CKAN_FEEDS_DATE', ''),
            'CKAN_FEEDS_AUTHOR_NAME': os.environ.get(
                'CKAN_FEEDS_AUTHOR_NAME', ''),
            'CKAN_FEEDS_AUTHOR_LINK': os.environ.get(
                'CKAN_FEEDS_AUTHOR_LINK', ''),
            'CKAN_STORAGE_PATH': os.environ.get('CKAN_STORAGE_PATH', '10'),
            'CKAN_MAX_RESOURCE_SIZE': os.environ.get(
                'CKAN_MAX_RESOURCE_SIZE', '10'),
            'CKAN_MAX_IMAGE_SIZE': os.environ.get('CKAN_MAX_IMAGE_SIZE', '2'),
            'CKAN_HIDE_ACTIVITY_STREAMS_FROM_USERS': os.environ.get(
                'CKAN_HIDE_ACTIVITY_STREAMS_FROM_USERS', '%(ckan.site_id)s'),
            'CKAN_SMTP_SERVER': os.environ.get(
                'CKAN_SMTP_SERVER', 'localhost'),
            'CKAN_SMTP_STARTTLS': os.environ.get(
                'CKAN_SMTP_STARTTLS', 'False'),
            }
        vars.update(environment_variables)

        return super(CKANInstaller, self).config_content(command, vars)
