import json
import nose.tools

import ckan.lib.search
import ckan.new_tests.helpers as helpers

assert_equal = nose.tools.assert_equal
assert_in = helpers.assert_in
assert_not_in = helpers.assert_not_in


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

    def test_index_package_stores_basic_solr_fields(self):
        index = ckan.lib.search.index.PackageSearchIndex()
        pkg_dict = self._get_pkg_dict()

        index.index_package(pkg_dict)
        indexed_pkg = ckan.lib.search.show(pkg_dict['name'])

        # At root level are the fields that SOLR uses
        assert_equal(indexed_pkg['name'], 'river-quality')
        assert_equal(indexed_pkg['metadata_modified'],
                     '2014-06-10T08:24:12.782Z')
        assert_equal(indexed_pkg['entity_type'], 'package')
        assert_equal(indexed_pkg['dataset_type'], 'dataset')

    def test_index_package_stores_unvalidated_data_dict(self):
        index = ckan.lib.search.index.PackageSearchIndex()
        pkg_dict = self._get_pkg_dict()

        index.index_package(pkg_dict)
        indexed_pkg = ckan.lib.search.show(pkg_dict['name'])

        # data_dict is the result of package_show, unvalidated
        data_dict = json.loads(indexed_pkg['data_dict'])
        assert_equal(data_dict['name'], 'river-quality')
        # title is inserted (copied from the name) during validation
        # so its absence shows it is not validated
        assert_not_in('title', data_dict)

    def test_index_package_stores_validated_data_dict(self):
        index = ckan.lib.search.index.PackageSearchIndex()
        pkg_dict = self._get_pkg_dict()

        index.index_package(pkg_dict)
        indexed_pkg = ckan.lib.search.show(pkg_dict['name'])

        # validated_data_dict is the result of package_show, validated
        validated_data_dict = json.loads(indexed_pkg['validated_data_dict'])
        assert_equal(validated_data_dict['name'], 'river-quality')
        # title is inserted (copied from the name) during validation
        # so its presence shows it is validated
        assert_in('title', validated_data_dict)

    def test_index_package_stores_validated_data_dict_without_unvalidated_data_dict(self):
        # This is a regression test for #1764
        index = ckan.lib.search.index.PackageSearchIndex()
        pkg_dict = self._get_pkg_dict()

        index.index_package(pkg_dict)
        indexed_pkg = ckan.lib.search.show(pkg_dict['name'])

        validated_data_dict = json.loads(indexed_pkg['validated_data_dict'])
        assert_not_in('data_dict', validated_data_dict)
