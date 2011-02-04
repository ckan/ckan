from ckan.tests import *
import ckan.model as model
import ckan.forms
from ckan.tests.pylons_controller import PylonsTestCase

class TestHarvestSource(PylonsTestCase):

    def setup(self):
        super(TestHarvestSource, self).setup()

    def teardown(self):
        model.repo.rebuild_db()

    def test_form_raw(self):
        fs = ckan.forms.get_harvest_source_fieldset()
        text = fs.render()
        assert 'url' in text
        assert 'description' in text

    def test_form_bound_to_existing_object(self):
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

    def test_form_bound_to_new_object(self):
        source = model.HarvestSource(url=u'http://localhost/', description=u'My source')
        fs = ckan.forms.get_harvest_source_fieldset()
        fs = fs.bind(source)
        text = fs.render()
        assert 'url' in text
        assert 'http://localhost/' in text
        assert 'description' in text
        assert 'My source' in text

    def test_form_validate_new_object_and_sync(self):
        assert not model.HarvestSource.get(u'http://localhost/', None, 'url')
        fs = ckan.forms.get_harvest_source_fieldset()
        register = model.HarvestSource
        data = {
            'HarvestSource--url': u'http://localhost/', 
            'HarvestSource--description': u'My source'
        }
        fs = fs.bind(register, data=data, session=model.Session)
        # Test bound_fields.validate().
        fs.validate()
        assert not fs.errors
        # Test bound_fields.sync().
        fs.sync()
        model.Session.commit()
        source = model.HarvestSource.get(u'http://localhost/', None, 'url')
        assert source.id

    def test_form_invalidate_new_object_null(self):
        fs = ckan.forms.get_harvest_source_fieldset()
        register = model.HarvestSource
        data = {
            'HarvestSource--url': u'', 
            'HarvestSource--description': u'My source'
        }
        fs = fs.bind(register, data=data)
        # Test bound_fields.validate().
        fs.validate()
        assert fs.errors

    def test_form_invalidate_new_object_not_http(self):
        fs = ckan.forms.get_harvest_source_fieldset()
        register = model.HarvestSource
        data = {
            'HarvestSource--url': u'htp:', 
            'HarvestSource--description': u'My source'
        }
        fs = fs.bind(register, data=data)
        # Test bound_fields.validate().
        fs.validate()
        assert fs.errors

