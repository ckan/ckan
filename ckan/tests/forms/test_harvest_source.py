from ckan.tests import *
import ckan.model as model
import ckan.forms
from ckan.tests.pylons_controller import PylonsTestCase

class TestHarvestSource(PylonsTestCase):

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_raw_form(self):
        fs = ckan.forms.get_harvest_source_fieldset()
        text = fs.render()
        assert 'url' in text
        assert 'description' in text

    def test_bound_form(self):
        source = model.HarvestSource(url=u'http://localhost/', description=u'My source')
        model.Session.add(source)
        model.Session.commit()
        model.Session.remove()
        fs = ckan.forms.get_harvest_source_fieldset()
        fs = fs.bind(source)
        text = fs.render()
        assert 'url' in text
        assert 'http://localhost/' in text
        assert 'description' in text
        assert 'My source' in text

