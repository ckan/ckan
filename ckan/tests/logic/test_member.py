from nose.tools import assert_raises
import ckan.model as model
import ckan.logic as logic
import ckan.lib.create_test_data as create_test_data


class TestMemberLogic(object):

    @classmethod
    def setup_class(cls):
        cls.username = 'testsysadmin'
        cls.groupname = 'david'

        model.repo.new_revision()
        create_test_data.CreateTestData.create()
        cls.pkgs = [model.Package.by_name('warandpeace'),
                    model.Package.by_name('annakarenina')]

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_member_create(self):
        res = self._member_create(self.pkgs[0].id, 'package', 'public')
        assert 'capacity' in res and res['capacity'] == u'public'

    def test_member_create_should_update_member_if_it_already_exists(self):
        initial = self._member_create(self.pkgs[0].id, 'package', 'public')
        final = self._member_create(self.pkgs[0].id, 'package', 'private')
        assert initial['id'] == final['id'], [initial, final]
        assert initial['capacity'] == u'public'
        assert final['capacity'] == u'private'

    def test_member_create_validates_if_user_is_authorized_to_update_group(self):
        ctx, dd = self._build_context(self.pkgs[0].id, 'package', user='unauthorized-user')
        assert_raises(logic.NotAuthorized, logic.get_action('member_create'), ctx, dd)

    def test_member_create_accepts_group_name_or_id(self):
        group = model.Group.get(self.groupname)
        by_id = self._member_create_in_group(self.pkgs[0].id, 'package', 'public', group.name)
        by_name = self._member_create_in_group(self.pkgs[0].id, 'package', 'public', group.id)
        assert by_id['id'] == by_name['id']

    def test_member_create_requires_all_parameters_to_be_defined(self):
        ctx, dd = self._build_context(self.pkgs[0].id, 'package')
        for key in dd.keys():
            new_dd = dd.copy()
            del new_dd[key]
            assert_raises(logic.ValidationError, logic.get_action('member_create'), ctx, new_dd)

    def test_member_list(self):
        self._member_create(self.pkgs[0].id, 'package', 'public')
        self._member_create(self.pkgs[1].id, 'package', 'public')
        ctx, dd = self._build_context('', 'package')
        res = logic.get_action('member_list')(ctx, dd)
        assert (self.pkgs[0].id, 'package', 'public') in res
        assert (self.pkgs[1].id, 'package', 'public') in res

        ctx, dd = self._build_context('', 'user', 'admin')
        res = logic.get_action('member_list')(ctx, dd)
        assert len(res) == 0, res

        ctx, dd = self._build_context('', 'user', 'admin')
        dd['id'] = u'foo'
        assert_raises(logic.NotFound, logic.get_action('member_list'), ctx, dd)

        self._member_create(self.username, 'user', 'admin')
        ctx, dd = self._build_context('', 'user', 'admin')
        res = logic.get_action('member_list')(ctx, dd)
        assert (self.username, 'user', 'Admin') in res

    def test_member_delete(self):
        self._member_create(self.username, 'user', 'admin')
        ctx, dd = self._build_context(self.username, 'user', 'admin')
        res = logic.get_action('member_list')(ctx, dd)
        assert (self.username, 'user', 'Admin') in res, res

        logic.get_action('member_delete')(ctx, dd)

        res = logic.get_action('member_list')(ctx, dd)
        assert (self.username, 'user', 'Admin') not in res, res

    def _member_create(self, obj, obj_type, capacity):
        ctx, dd = self._build_context(obj, obj_type, capacity)
        return logic.get_action('member_create')(ctx, dd)

    def _member_create_in_group(self, obj, obj_type, capacity, group_id):
        ctx, dd = self._build_context(obj, obj_type, capacity, group_id)
        return logic.get_action('member_create')(ctx, dd)

    def _member_create_as_user(self, obj, obj_type, capacity, user):
        ctx, dd = self._build_context(obj, obj_type, capacity, user=user)
        return logic.get_action('member_create')(ctx, dd)

    def _build_context(self, obj, obj_type, capacity='public', group_id=None, user=None):
        ctx = {'model': model,
               'session': model.Session,
               'user': user or self.username}
        dd = {'id': group_id or self.groupname,
              'object': obj,
              'object_type': obj_type,
              'capacity': capacity}
        return ctx, dd
