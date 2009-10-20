from pylons import config
import ckan.lib.helpers as h

import ckan.lib.rdf as rdf
from ckan.tests import *
import ckan.model as model

class TestRdf:
    @classmethod
    def setup_class(self):
        CreateSearchTestData.create()
        self.rdf = rdf.RdfExporter()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_1_package(self):
        pkg = model.Package.by_name(u'usa-courts-gov')
        out = self.rdf.export_package(pkg)
        print out
        assert pkg.name in out, out
