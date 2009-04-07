import os

import simplejson

import ckan
from ckan.tests import *
from ckan.lib.converter import Dumper
import ckan.model as model

class TestConverter(object):

    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()
        d = Dumper()
        self.outpath = '/tmp/mytestdump.js'
        if os.path.exists(self.outpath):
            os.remove(self.outpath)
        d.dump(self.outpath)

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()

    def test_dump(self):
        assert os.path.exists(self.outpath) 
        dumpeddata = simplejson.load(open(self.outpath))
        assert dumpeddata['version'] == ckan.__version__
        assert len(dumpeddata['Package']) == 2
        assert len(dumpeddata['Tag']) == 2
        assert len(dumpeddata['PackageRevision']) == 2
        assert len(dumpeddata['Revision']) == 2, dumpeddata['Revision']
   
    def test_load(self):
        model.repo.clean_db()
        model.repo.create_db()
        d = Dumper()
        d.load(self.outpath)
        assert len(model.Package.query.all()) == 2

