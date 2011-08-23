from pylons import config
from ckan import plugins, model
import ckan.lib.search as search
from ckan.tests import CreateTestData, setup_test_search_index
from test_solr_package_search import TestSearchOverall

class TestSearchOverallWithSynchronousIndexing(TestSearchOverall):
    '''Repeat test from test_package_search with synchronous indexing
    '''

    @classmethod
    def setup_class(cls):
        setup_test_search_index()
        # Force a garbage collection to trigger issue #695
        import gc
        gc.collect()

        CreateTestData.create()

        cls.new_pkg_dict = {
            "name": "council-owned-litter-bins",
            "notes": "Location of Council owned litter bins within Borough.",
            "resources": [{"description": "Resource locator",
                           "format": "Unverified",
                           "url": "http://www.barrowbc.gov.uk"}],
            "tags": ["Utility and governmental services"],
            "title": "Council Owned Litter Bins",
            "extras": {
                "INSPIRE": "True",
                "bbox-east-long": "-3.12442",
                "bbox-north-lat": "54.218407",
                "bbox-south-lat": "54.039634",
                "bbox-west-long": "-3.32485",
                "constraint": "conditions unknown; (e) intellectual property rights;",
                "dataset-reference-date": [{"type": "creation",
                                            "value": "2008-10-10"},
                                           {"type": "revision",
                                            "value": "2009-10-08"}],
                "guid": "00a743bf-cca4-4c19-a8e5-e64f7edbcadd",
                "metadata-date": "2009-10-16",
                "metadata-language": "eng",
                "published_by": 0,
                "resource-type": "dataset",
                "spatial-reference-system": "wee",
                "temporal_coverage-from": "1977-03-10T11:45:30",
                "temporal_coverage-to": "2005-01-15T09:10:00"
            }
        }

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        search.clear()

    def _create_package(self, package=None):
        rev = model.repo.new_revision()
        rev.author = u'tester'
        rev.message = u'Creating test data'
        if not package:
            package = model.Package()

        relationship_attr = ['extras', 'resources', 'tags']
        package_properties = {}
        for key, value in self.new_pkg_dict.iteritems():
            if key not in relationship_attr:
                setattr(package, key, value)

        tags = self.new_pkg_dict.get('tags', [])
        for tag in tags:
            package.add_tag_by_name(tag, autoflush=False)
        
        for resource_dict in self.new_pkg_dict.get("resources", []):
            resource = model.Resource(**resource_dict)
            package.resources[:] = []
            package.resources.append(resource)

        for key, value in self.new_pkg_dict.get("extras", {}).iteritems():
            extra = model.PackageExtra(key=key, value=value)
            package._extras[key] = extra

        model.Session.add(package)
        model.setup_default_user_roles(package, [])
        model.repo.commit_and_remove()
        return package

    def _remove_package(self):
        package = model.Package.by_name('council-owned-litter-bins')
        model.Session.delete(package)
        model.Session.commit()

    def test_01_search_table_count(self):
        self._check_search_results('', 2)

    def test_02_add_package_from_dict(self):
        self._create_package()
        self._check_search_results('', 3)
        self._check_search_results('wee', 1, ['council-owned-litter-bins'])
        self._remove_package()

    def test_03_update_package_from_dict(self):
        self._create_package()
        package = model.Package.by_name('council-owned-litter-bins')
        self.new_pkg_dict['name'] = 'new_name'
        self.new_pkg_dict['extras']['published_by'] = 'meeeee'
        self._create_package(package)
        self._check_search_results('', 3)
        self._check_search_results('meeeee', 1, ['new_name'])

        package = model.Package.by_name('new_name')
        self.new_pkg_dict['name'] = 'council-owned-litter-bins'
        self._create_package(package)
        self._check_search_results('', 3)
        self._check_search_results('wee', 1, ['council-owned-litter-bins'])
        self._remove_package()

    def test_04_delete_package_from_dict(self):
        self._create_package()
        package = model.Package.by_name('council-owned-litter-bins')
        assert package
        self._remove_package()
        self._check_search_results('', 2)
