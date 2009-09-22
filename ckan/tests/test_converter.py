import os

import simplejson

import ckan
from ckan.tests import *
from ckan.lib.converter import Dumper
import ckan.model as model

class TestConverter(object):
# TODO this doesn't work on sqlite - we should fix this
    

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
        tables = dumpeddata.keys()
        for key in ['Package', 'Tag', 'Group', 'PackageGroup', 'PackageExtra']:
            assert key in tables, '%r not in %s' % (key, tables)
        for key in ['User']:
            assert key not in tables, '%s should not be in %s' % (key, tables)
        assert len(dumpeddata['Package']) == 2, len(dumpeddata['Package'])
        assert len(dumpeddata['Tag']) == 2, len(dumpeddata['Tag'])
        assert len(dumpeddata['PackageRevision']) == 2, len(dumpeddata['PackageRevision'])
        assert len(dumpeddata['Group']) == 2, len(dumpeddata['Group'])


    # Disabled 22/9/09 because not used anymore
    def _test_load(self):
        model.repo.clean_db()
        model.repo.create_db()
        d = Dumper()
        d.load(self.outpath)
        assert len(model.Package.query.all()) == 2

