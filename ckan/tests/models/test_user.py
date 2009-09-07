from ckan.tests import *
import ckan.model as model

class TestUser:
    def test_basic(self):
        user = model.User()
        openid = u'http://xyz.com'
        user.name = openid
        model.repo.commit_and_remove()

        out = model.User.by_name(openid)
        assert len(out.apikey) == 36

