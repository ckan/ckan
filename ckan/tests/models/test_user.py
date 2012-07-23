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

def to_names(domain_obj_list):
    '''Takes a list of domain objects and returns a corresponding list
    of their names.'''
    objs = []
    for obj in domain_obj_list:
        objs.append(obj.name if obj else None)
    return objs

class TestUserGroups:
    @classmethod
    def setup_class(self):
        CreateTestData.create_arbitrary([{'name': 'testpkg'}],
                                        extra_user_names=['brian', 'sandra'])
        CreateTestData.create_groups([
            {'name': 'grp1',
             'phone': '1234',
             }
            ])
        model.repo.new_revision()
        grp1 = model.Group.by_name(u'grp1')
        brian = model.User.by_name(u'brian')
        model.Session.add(model.Member(group=grp1,
                                       table_id=brian.id,
                                       table_name='user',
                                       capacity='admin')
                         )
        model.repo.commit_and_remove()
        
    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()
    
    def test_get_groups(self):
        brian = model.User.by_name(u'brian')
        groups = brian.get_groups()
        assert_equal(to_names(groups), ['grp1'])
        assert_equal(groups[0].extras, {'phone': '1234'})

        # check cache works between sessions
        model.Session.expunge_all()
        #don't refresh brian user since this is how c.user works
        # i.e. don't do this: brian = model.User.by_name(u'brian')
        groups = brian.get_groups()
        assert_equal(to_names(groups), ['grp1'])
        assert_equal(groups[0].extras, {'phone': '1234'})

