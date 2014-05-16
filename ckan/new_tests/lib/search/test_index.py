import datetime
import hashlib
import nose

from pylons import config
import ckan.lib.search as search


eq_ = nose.tools.eq_


class TestSearchIndex(object):

    @classmethod
    def setup_class(cls):

        if not search.is_available():
            raise nose.SkipTest('Solr not reachable')

        cls.solr_client = search.make_connection()

        cls.fq = " +site_id:\"%s\" " % config['ckan.site_id']

        cls.package_index = search.PackageSearchIndex()

        cls.base_package_dict = {
            'id': 'test-index',
            'name': 'monkey',
            'title': 'Monkey',
            'state': 'active',
            'private': False,
            'type': 'dataset',
            'owner_org': None,
            'metadata_created': datetime.datetime.now().isoformat(),
            'metadata_modified': datetime.datetime.now().isoformat(),
        }

    def teardown(self):
        # clear the search index after every test
        self.package_index.clear()

    def test_index_basic(self):

        self.package_index.index_package(self.base_package_dict)

        response = self.solr_client.query('name:monkey', fq=self.fq)

        eq_(len(response), 1)

        eq_(response.results[0]['id'], 'test-index')
        eq_(response.results[0]['name'], 'monkey')
        eq_(response.results[0]['title'], 'Monkey')

        index_id = hashlib.md5(
            '{0}{1}'.format(self.base_package_dict['id'],
                            config['ckan.site_id'])
        ).hexdigest()

        eq_(response.results[0]['index_id'], index_id)

    def test_no_state_no_index(self):
        pkg_dict = self.base_package_dict.copy()
        pkg_dict.update({
            'state': None,
        })

        self.package_index.index_package(pkg_dict)

        response = self.solr_client.query('name:monkey', fq=self.fq)

        eq_(len(response), 0)

    def test_clear_index(self):

        self.package_index.index_package(self.base_package_dict)

        self.package_index.clear()

        response = self.solr_client.query('name:monkey', fq=self.fq)
        eq_(len(response), 0)

    def test_index_illegal_xml_chars(self):

        pkg_dict = self.base_package_dict.copy()
        pkg_dict.update({
            'title': u'\u00c3a\u0001ltimo n\u00famero penguin',
            'notes': u'\u00c3a\u0001ltimo n\u00famero penguin',
        })
        self.package_index.index_package(pkg_dict)

        response = self.solr_client.query('name:monkey', fq=self.fq)

        eq_(len(response), 1)
        eq_(response.results[0]['title'], u'\u00c3altimo n\u00famero penguin')

    def test_index_date_field(self):

        pkg_dict = self.base_package_dict.copy()
        pkg_dict.update({
            'extras': [
                {'key': 'test_date', 'value': '2014-03-22'},
                {'key': 'test_tim_date', 'value': '2014-03-22 05:42:14'},
            ]
        })

        self.package_index.index_package(pkg_dict)

        response = self.solr_client.query('name:monkey', fq=self.fq)

        eq_(len(response), 1)

        assert isinstance(response.results[0]['test_date'], datetime.datetime)
        eq_(response.results[0]['test_date'].strftime('%Y-%m-%d'),
            '2014-03-22')
        eq_(response.results[0]['test_tim_date'].strftime('%Y-%m-%d %H:%M:%S'),
            '2014-03-22 05:42:14')

    def test_index_date_field_wrong_value(self):

        pkg_dict = self.base_package_dict.copy()
        pkg_dict.update({
            'extras': [
                {'key': 'test_wrong_date', 'value': 'Not a date'},
                {'key': 'test_another_wrong_date', 'value': '2014-13-01'},
            ]
        })

        self.package_index.index_package(pkg_dict)

        response = self.solr_client.query('name:monkey', fq=self.fq)

        eq_(len(response), 1)

        assert 'test_wrong_date' not in response.results[0]
        assert 'test_another_wrong_date' not in response.results[0]

    def test_index_date_field_empty_value(self):

        pkg_dict = self.base_package_dict.copy()
        pkg_dict.update({
            'extras': [
                {'key': 'test_empty_date', 'value': ''},
            ]
        })

        self.package_index.index_package(pkg_dict)

        response = self.solr_client.query('name:monkey', fq=self.fq)

        eq_(len(response), 1)

        assert 'test_empty_date' not in response.results[0]
