from nose.tools import assert_equal

from ckan.tests import *
import ckan.model as model
from ckan.lib.create_test_data import CreateTestData



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

    def test_is_deleted(self):
        user = CreateTestData._create_user_without_commit('a_user')
        user.state = 'some-state'
        assert not user.is_deleted(), user
        user.delete()
        assert user.is_deleted(), user

    def test_user_is_active_by_default(self):
        user = CreateTestData._create_user_without_commit('a_user')
        assert user.is_active(), user

    def test_activate(self):
        user = CreateTestData._create_user_without_commit('a_user')
        user.state = 'some-state'
        assert not user.is_active(), user
        user.activate()
        assert user.is_active(), user

    def test_activate(self):
        user = CreateTestData._create_user_without_commit('a_user')
        user.state = 'some-state'
        assert not user.is_active(), user
        user.activate()
        assert user.is_active(), user

    def test_is_pending(self):
        user = CreateTestData._create_user_without_commit('a_user')
        user.state = 'some-state'
        assert not user.is_pending(), user
        user.set_pending()
        assert user.is_pending(), user


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


class TestUser2(object):
    '''
        This class was originally in ckan/model/test_user.py
    '''

    @classmethod
    def setup_class(self):
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_number_of_edits(self):
        # initially annafan won't have made any edits
        assert model.User.by_name(u'annafan').number_of_edits() == 0, \
                    "annafan shouldn't have made any edits"

        # so we'll get him to edit his package twice
        for i in [1,2]:

            rev = model.repo.new_revision()
            pkg = model.Package.by_name(u'annakarenina')
            pkg.notes = u'Changed notes %i' % i
            rev.author = u'annafan'
            model.repo.commit_and_remove()

            #and each time check that number_of_edits is correct
            assert model.User.by_name(u'annafan').number_of_edits() == i, \
                   "annafan should have made %i edit(s)" % i


    def test_number_of_administered_packages(self):
        model.User.by_name(u'annafan').number_administered_packages() == 1, \
            "annafan should own one package"
        model.User.by_name(u'joeadmin').number_administered_packages() == 0, \
            "joeadmin shouldn't own any packages"


    def test_search(self):
        anna_names = [a.name for a in  model.User.search('anna').all()]
        assert anna_names==['annafan'], \
            "Search for anna should find annafan only."

        test_names = [a.name for a in  model.User.search('test').all()]
        assert ( len(test_names) == 2 and
                 'tester' in test_names and
                 'testsysadmin' in test_names ), \
                 "Search for test should find tester and testsysadmin (only)"

