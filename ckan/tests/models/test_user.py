from nose.tools import assert_equal

from ckan.tests import *
import ckan.model as model

class TestUser:

    @classmethod
    def setup_class(self):
        CreateTestData.create_user('brian', password='pass',
                                   fullname='Brian', email='brian@brian.com')
        CreateTestData.create_user(openid='http://sandra.owndomain.com/',
                                   fullname='Sandra')

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()
        
    def test_0_basic(self):
        out = model.User.by_name(u'brian')
        assert_equal(out.name, u'brian')
        assert_equal(len(out.apikey), 36)
        assert_equal(out.fullname, 'Brian')
        assert_equal(out.email, u'brian@brian.com')

        out = model.User.by_openid(u'http://sandra.owndomain.com/')
        assert_equal(out.fullname, u'Sandra')

    def test_1_timestamp_any_existing(self):
        user = model.Session.query(model.User).first()
        assert len(str(user.created)) > 5, out.created

    def test_2_timestamp_new(self):
        user = model.User()
        openid = u'http://xyz.com'
        user.name = openid
        model.Session.add(user)
        model.repo.commit_and_remove()

        out = model.User.by_name(openid)
        assert len(str(out.created)) > 5, out.created

    def test_3_get(self):
        out = model.User.get(u'brian')
        assert out.fullname == u'Brian'

        out = model.User.get(u'http://sandra.owndomain.com/')
        assert out.fullname == u'Sandra'

    def test_4_get_openid_missing_slash(self):
        # browsers seem to lose the double slash
        out = model.User.get(u'http:/sandra.owndomain.com/')
        assert out
        assert out.fullname == u'Sandra'
