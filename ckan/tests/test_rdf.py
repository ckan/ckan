from pylons import config
import ckan.lib.helpers as h

if 0: # DISABLED IMPORTS AND ALL TESTS
    import ckan.lib.rdf as rdf
    import ckan.lib.talis as talis
    from ckan.tests import *
    import ckan.model as model

TALIS_STORE_NAME = 'ckan-dev1'

class _TestRdf:
    @classmethod
    def setup_class(self):
        CreateTestData.create_search_test_data()
        self.rdf = rdf.RdfExporter()
        self.talis = talis.Talis()
        self.pkg_name = u'usa-courts-gov'

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_1_package(self):
        pkg = model.Package.by_name(self.pkg_name)
        out = self.rdf.export_package(pkg)
        print out
        assert pkg.name in out, out

    def test_2_post(self):
        pkg = model.Package.by_name(self.pkg_name)
        rdf_xml = self.rdf.export_package(pkg)
        service = '/meta'
        err = self.talis.post(service, rdf_xml, with_password=True)
        assert not err, err

    def test_2_upload_package(self):
        pkg = model.Package.by_name(self.pkg_name)
        err = self.talis.post_pkg(pkg)
        assert not err, err

    def test_3_download_package(self):
        res = self.talis.get_pkg(self.pkg_name)
        assert not isinstance(res, Exception), res
        print res

        pkg = model.Package.by_name(self.pkg_name)
        assert pkg.name in res, res
        assert pkg.title in res, res

    def test_3_get(self):
        uri = talis.TALIS_URI + TALIS_STORE_NAME + '/meta?about=%s&output=rdf' % (rdf.CKAN_SUBJECT_BASE + self.pkg_name)
        res = self.talis.get(uri)
        assert not isinstance(res, Exception), res
        print res

        pkg = model.Package.by_name(self.pkg_name)
        assert pkg.name in res, res
        assert pkg.title in res, res

        
