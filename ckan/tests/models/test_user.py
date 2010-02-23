from ckan.tests import *
import ckan.model as model

class TestUser:
    def test_2_basic(self):
        user = model.User()
        openid = u'http://xyz.com'
        user.name = openid
        model.Session.add(user)
        model.repo.commit_and_remove()

        out = model.User.by_name(openid)
        assert len(out.apikey) == 36

    def test_0_timestamp_any_existing(self):
        user = model.Session.query(model.User).first()
        assert len(str(user.created)) > 5, out.created

    def test_1_timestamp_new(self):
        user = model.User()
        openid = u'http://xyz.com'
        user.name = openid
        model.Session.add(user)
        model.repo.commit_and_remove()

        out = model.User.by_name(openid)
        assert len(str(out.created)) > 5, out.created
