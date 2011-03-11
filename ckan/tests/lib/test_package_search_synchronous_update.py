import json

from ckan.tests import *
from ckan.tests import is_search_supported
import ckan.lib.search as search
from ckan import plugins
from test_package_search import TestSearchOverall
from ckan import model

class TestSearchOverallWithSynchronousIndexing(TestSearchOverall):
    '''Repeat test from test_package_search with synchronous indexing
    '''

    @classmethod
    def setup_class(self):
        if not is_search_supported():
            raise SkipTest("Search not supported")

        import gc
        from pylons import config

        # Force a garbage collection to trigger issue #695
        gc.collect()

        config['search_backend'] = 'sql'
        self.backend = search.get_backend()
        plugins.load('synchronous_search')
        CreateTestData.create()

    def test_01_search_table_count(self):

        assert model.Session.query(model.PackageSearch).count() == 2 

    def test_02_add_package_from_dict(self):

        print self.create_package_from_data.__doc__
        self.package = self.create_package_from_data(json.loads(str(self.create_package_from_data.__doc__)))

        assert model.Session.query(model.PackageSearch).count() == 3 

        self._check_search_results('wee', 1, ['council-owned-litter-bins'])

    def test_03_update_package_from_dict(self):

        package = model.Package.by_name('council-owned-litter-bins')


        update_dict = json.loads(str(self.create_package_from_data.__doc__))
        update_dict['name'] = 'new_name'
        update_dict['extras']['published_by'] = 'meeeee'

        self.create_package_from_data(update_dict, package)
        assert model.Session.query(model.PackageSearch).count() == 3 

        self._check_search_results('meeeee', 1, ['new_name'])

    def test_04_delete_package_from_dict(self):

        package = model.Package.by_name('new_name')

        model.Session.delete(package)
        model.Session.commit()

        assert model.Session.query(model.PackageSearch).count() == 2 

    def create_package_from_data(self, package_data, package = None):
        ''' {"extras": {"INSPIRE": "True",
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
                    "temporal_coverage-to": "2005-01-15T09:10:00"},
         "name": "council-owned-litter-bins",
         "notes": "Location of Council owned litter bins within Borough.",
         "resources": [{"description": "Resource locator",
                        "format": "Unverified",
                        "url": "http://www.barrowbc.gov.uk"}],
         "tags": ["Utility and governmental services"],
         "title": "Council Owned Litter Bins"}
        '''

        if not package:
            package = model.Package()

        rev = model.repo.new_revision()
        
        relationship_attr = ['extras', 'resources', 'tags']

        package_properties = {}
        for key, value in package_data.iteritems():
            if key not in relationship_attr:
                setattr(package, key, value)

        tags = package_data.get('tags', [])

        for tag in tags:
            package.add_tag_by_name(tag, autoflush=False)
        
        for resource_dict in package_data.get("resources", []):
            resource = model.Resource(**resource_dict)
            package.resources[:] = []
            package.resources.append(resource)

        for key, value in package_data.get("extras", {}).iteritems():
            extra = model.PackageExtra(key=key, value=value)
            package._extras[key] = extra

        model.Session.add(package)
        model.Session.flush()

        model.setup_default_user_roles(package, [])


        model.Session.add(rev)
        model.Session.commit()

        return package


    @classmethod
    def teardown_class(self):
        model.repo.delete_all()

# Stop parent class tests from running
#TestSearchOverall = None
