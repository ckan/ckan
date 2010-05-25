from ckan.tests import *
import ckan.model as model
import ckan.forms
from ckan.tests.pylons_controller import PylonsTestCase

class TestGroupFieldset(PylonsTestCase):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        ckan.tests.CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_1(self):
        group = model.Group.by_name(u'roger')
        fs = ckan.forms.get_group_fieldset('group_fs').bind(group)
        out = fs.render()
        print out
        desc = fs.description.render()
        assert 'textarea' in desc, desc
        # TODO: ...
        # assert 'checkbox' in out, out
        # assert 'select' in out, out


