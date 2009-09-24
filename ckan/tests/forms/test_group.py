from ckan.tests import *
import ckan.model as model
import ckan.forms

class TestGroupFieldset:
    @classmethod
    def setup_class(self):
        model.Session.remove()
        ckan.tests.CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_1(self):
        group = model.Group.by_name(u'roger')
        fs = ckan.forms.group_fs.bind(group)
        out = fs.render()
        print out
        # TODO: ...
        # assert 'checkbox' in out, out
        # assert 'select' in out, out


