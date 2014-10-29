'''Functional tests for CKAN's configuration '''

import ckan.tests as tests


class TestConfiguration(object):

    def test_missing_siteurl(self):
        from pylons import config
        from ckan import plugins

        config['ckan.site_url'] = ''

        try:
            # Load any plugin to trigger the update config check
            plugins.load('pdf_view')
            assert False,\
                "Expected update_config() to complain of missing site_url"
        except RuntimeError, rte:
            pass
