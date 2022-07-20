# encoding: utf-8

import datetime
import hashlib
import json
import nose
from nose.tools import assert_equal, assert_in, assert_not_in

from ckan.common import config
import ckan.lib.search as search
import ckan.tests.helpers as helpers


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

        response = self.solr_client.search(q='name:monkey', fq=self.fq)

        assert_equal(len(response), 1)

        assert_equal(response.docs[0]['id'], 'test-index')
        assert_equal(response.docs[0]['name'], 'monkey')
        assert_equal(response.docs[0]['title'], 'Monkey')

        index_id = hashlib.md5(
            '{0}{1}'.format(self.base_package_dict['id'],
                            config['ckan.site_id'])
        ).hexdigest()

        assert_equal(response.docs[0]['index_id'], index_id)

    def test_no_state_no_index(self):
        pkg_dict = self.base_package_dict.copy()
        pkg_dict.update({
            'state': None,
        })

        self.package_index.index_package(pkg_dict)

        response = self.solr_client.search(q='name:monkey', fq=self.fq)

        assert_equal(len(response), 0)

    def test_clear_index(self):

        self.package_index.index_package(self.base_package_dict)

        self.package_index.clear()

        response = self.solr_client.search(q='name:monkey', fq=self.fq)
        assert_equal(len(response), 0)

    def test_delete_package(self):
        self.package_index.index_package(self.base_package_dict)

        pkg_dict = self.base_package_dict.copy()
        pkg_dict.update({
            'id': 'test-index-2',
            'name': 'monkey2'
        })
        self.package_index.index_package(pkg_dict)

        response = self.solr_client.search(q='title:Monkey', fq=self.fq)
        assert_equal(len(response), 2)
        response_ids = sorted([x['id'] for x in response.docs])
        assert_equal(response_ids, ['test-index', 'test-index-2'])

        self.package_index.delete_package(pkg_dict)

        response = self.solr_client.search(q='title:Monkey', fq=self.fq)
        assert_equal(len(response), 1)
        response_ids = sorted([x['id'] for x in response.docs])
        assert_equal(response_ids, ['test-index'])

    def test_index_illegal_xml_chars(self):

        pkg_dict = self.base_package_dict.copy()
        pkg_dict.update({
            'title': u'\u00c3a\u0001ltimo n\u00famero penguin',
            'notes': u'\u00c3a\u0001ltimo n\u00famero penguin',
        })
        self.package_index.index_package(pkg_dict)

        response = self.solr_client.search(q='name:monkey', fq=self.fq)

        assert_equal(len(response), 1)
        assert_equal(response.docs[0]['title'],
                     u'\u00c3altimo n\u00famero penguin')

    def test_index_date_field(self):

        pkg_dict = self.base_package_dict.copy()
        pkg_dict.update({
            'extras': [
                {'key': 'test_date', 'value': '2014-03-22'},
                {'key': 'test_tim_date', 'value': '2014-03-22 05:42:14'},
            ]
        })

        self.package_index.index_package(pkg_dict)

        response = self.solr_client.search(q='name:monkey', fq=self.fq)

        assert_equal(len(response), 1)

        assert isinstance(response.docs[0]['test_date'], datetime.datetime)
        assert_equal(response.docs[0]['test_date'].strftime('%Y-%m-%d'),
                     '2014-03-22')
        assert_equal(
            response.docs[0]['test_tim_date'].strftime('%Y-%m-%d %H:%M:%S'),
            '2014-03-22 05:42:14'
        )

    def test_index_date_field_wrong_value(self):

        pkg_dict = self.base_package_dict.copy()
        pkg_dict.update({
            'extras': [
                {'key': 'test_wrong_date', 'value': 'Not a date'},
                {'key': 'test_another_wrong_date', 'value': '2014-13-01'},
            ]
        })

        self.package_index.index_package(pkg_dict)

        response = self.solr_client.search(q='name:monkey', fq=self.fq)

        assert_equal(len(response), 1)

        assert 'test_wrong_date' not in response.docs[0]
        assert 'test_another_wrong_date' not in response.docs[0]

    def test_index_date_field_empty_value(self):

        pkg_dict = self.base_package_dict.copy()
        pkg_dict.update({
            'extras': [
                {'key': 'test_empty_date', 'value': ''},
            ]
        })

        self.package_index.index_package(pkg_dict)

        response = self.solr_client.search(q='name:monkey', fq=self.fq)

        assert_equal(len(response), 1)

        assert 'test_empty_date' not in response.docs[0]


class TestPackageSearchIndex:
    @staticmethod
    def _get_pkg_dict():
        # This is a simple package, enough to be indexed, in the format that
        # package_show would return
        return {'name': 'river-quality',
                'id': 'd9567b82-d3f0-4c17-b222-d9a7499f7940',
                'state': 'active',
                'private': '',
                'type': 'dataset',
                'metadata_created': '2014-06-10T08:24:12.782257',
                'metadata_modified': '2014-06-10T08:24:12.782257',
                }

    @staticmethod
    def _get_pkg_dict_with_resources():
        # A simple package with some resources
        pkg_dict = TestPackageSearchIndex._get_pkg_dict()
        pkg_dict['resources'] = [
            {'description': 'A river quality report',
             'format': 'pdf',
             'resource_type': 'doc',
             'url': 'http://www.foo.com/riverquality.pdf',
             'alt_url': 'http://www.bar.com/riverquality.pdf',
             'city': 'Asuncion'
             },
            {'description': 'A river quality table',
             'format': 'csv',
             'resource_type': 'file',
             'url': 'http://www.foo.com/riverquality.csv',
             'alt_url': 'http://www.bar.com/riverquality.csv',
             'institution': 'Global River Foundation'
             }
        ]
        return pkg_dict

    def test_index_package_stores_basic_solr_fields(self):
        index = search.index.PackageSearchIndex()
        pkg_dict = self._get_pkg_dict()

        index.index_package(pkg_dict)
        indexed_pkg = search.show(pkg_dict['name'])

        # At root level are the fields that SOLR uses
        assert_equal(indexed_pkg['name'], 'river-quality')
        assert_equal(indexed_pkg['metadata_modified'],
                     '2014-06-10T08:24:12.782Z')
        assert_equal(indexed_pkg['entity_type'], 'package')
        assert_equal(indexed_pkg['dataset_type'], 'dataset')

    def test_index_package_stores_unvalidated_data_dict(self):
        index = search.index.PackageSearchIndex()
        pkg_dict = self._get_pkg_dict()

        index.index_package(pkg_dict)
        indexed_pkg = search.show(pkg_dict['name'])

        # data_dict is the result of package_show, unvalidated
        data_dict = json.loads(indexed_pkg['data_dict'])
        assert_equal(data_dict['name'], 'river-quality')
        # title is inserted (copied from the name) during validation
        # so its absence shows it is not validated
        assert_not_in('title', data_dict)

    def test_index_package_stores_validated_data_dict(self):
        index = search.index.PackageSearchIndex()
        pkg_dict = self._get_pkg_dict()

        index.index_package(pkg_dict)
        indexed_pkg = search.show(pkg_dict['name'])

        # validated_data_dict is the result of package_show, validated
        validated_data_dict = json.loads(indexed_pkg['validated_data_dict'])
        assert_equal(validated_data_dict['name'], 'river-quality')
        # title is inserted (copied from the name) during validation
        # so its presence shows it is validated
        assert_in('title', validated_data_dict)

    def test_index_package_stores_validated_data_dict_without_unvalidated_data_dict(self):
        # This is a regression test for #1764
        index = search.index.PackageSearchIndex()
        pkg_dict = self._get_pkg_dict()

        index.index_package(pkg_dict)
        indexed_pkg = search.show(pkg_dict['name'])

        validated_data_dict = json.loads(indexed_pkg['validated_data_dict'])
        assert_not_in('data_dict', validated_data_dict)

    def test_index_package_stores_unvalidated_data_dict_without_validated_data_dict(self):
        # This is a regression test for #2208
        index = search.index.PackageSearchIndex()
        pkg_dict = self._get_pkg_dict()

        index.index_package(pkg_dict)
        data_dict = json.loads(search.show(pkg_dict['name'])['data_dict'])

        assert_not_in('validated_data_dict', data_dict)

    def test_index_package_stores_resource_extras_in_config_file(self):
        index = search.index.PackageSearchIndex()
        pkg_dict = self._get_pkg_dict_with_resources()

        index.index_package(pkg_dict)
        indexed_pkg = search.show(pkg_dict['name'])

        # Resource fields given by ckan.extra_resource_fields are indexed
        assert_equal(indexed_pkg['res_extras_alt_url'],
                     ['http://www.bar.com/riverquality.pdf',
                      'http://www.bar.com/riverquality.csv'])

        # Other resource fields are ignored
        assert_equal(indexed_pkg.get('res_extras_institution', None), None)
        assert_equal(indexed_pkg.get('res_extras_city', None), None)

    def test_indexed_package_stores_resource_type(self):
        index = search.index.PackageSearchIndex()
        pkg_dict = self._get_pkg_dict_with_resources()

        index.index_package(pkg_dict)
        indexed_pkg = search.show(pkg_dict['name'])

        # Resource types are indexed
        assert_equal(indexed_pkg['res_type'], ['doc', 'file'])
