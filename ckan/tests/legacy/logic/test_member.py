from nose.tools import assert_raises
import ckan.model as model
import ckan.logic as logic
import ckan.lib.create_test_data as create_test_data


class TestMemberLogic(object):

    @classmethod
    def setup_class(cls):
        model.repo.new_revision()
        create_test_data.CreateTestData.create()
        cls.user = model.User.get('testsysadmin')
        cls.tester = model.User.get('tester')
        cls.group = model.Group.get('david')
        cls.roger = model.Group.get('roger')
        cls.pkgs = [model.Package.by_name('warandpeace'),
                    model.Package.by_name('annakarenina')]

        # 'Tester' becomes an admin for the 'roger' group
        model.repo.new_revision()
        model.Member(group=cls.roger, table_id=cls.tester.id,
                     table_name='user', capacity='admin')
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_member_create(self):
        self._member_create(self.pkgs[0].id, 'package', 'public')
        res = self._member_list()
        assert (self.pkgs[0].id, 'package', 'public') in res, res

    def test_member_create_should_update_member_if_it_already_exists(self):
        initial = self._member_create(self.pkgs[0].id, 'package', 'public')
        final = self._member_create(self.pkgs[0].id, 'package', 'private')
        assert initial['id'] == final['id'], [initial, final]
        assert initial['capacity'] == u'public'
        assert final['capacity'] == u'private'

    def test_member_create_raises_if_user_unauthorized_to_update_group(self):
        ctx, dd = self._build_context(self.pkgs[0].id, 'package',
                                      user='unauthorized_user')
        assert_raises(logic.NotAuthorized,
                      logic.get_action('member_create'), ctx, dd)

    def test_member_create_with_child_group_permission(self):
        # 'tester' has admin priviledge for roger, so anyone can make it
        # a child group.
        self._member_create_group_hierarchy(parent_group=self.group,
                                            child_group=self.roger,
                                            user=self.tester)

    def test_member_create_raises_when_only_have_parent_group_permission(self):
        assert_raises(logic.NotAuthorized,
                      self._member_create_group_hierarchy,
                      self.roger,  # parent
                      self.group,  # child
                      self.tester)

    def test_member_create_accepts_group_name_or_id(self):
        by_name = self._member_create_in_group(self.pkgs[0].id, 'package',
                                               'public', self.group.name)
        by_id = self._member_create_in_group(self.pkgs[0].id, 'package',
                                             'public', self.group.id)
        assert by_name['id'] == by_id['id']

    def test_member_create_accepts_object_name_or_id(self):
        test_cases = ((self.pkgs[0], 'package', 'public'),
                      (self.user, 'user', 'admin'))
        for case in test_cases:
            obj = case[0]
            by_name = self._member_create(obj.name, case[1], case[2])
            by_id = self._member_create(obj.id, case[1], case[2])
            assert by_name['id'] == by_id['id']

    def test_member_create_raises_if_any_required_parameter_isnt_defined(self):
        ctx, dd = self._build_context(self.pkgs[0].id, 'package')
        for key in dd.keys():
            new_dd = dd.copy()
            del new_dd[key]
            assert_raises(logic.ValidationError,
                          logic.get_action('member_create'), ctx, new_dd)

    def test_member_create_raises_if_group_wasnt_found(self):
        assert_raises(logic.NotFound,
                      self._member_create_in_group,
                      self.pkgs[0].id, 'package', 'public', 'inexistent_group')

    def test_member_create_raises_if_object_wasnt_found(self):
        assert_raises(logic.NotFound,
                      self._member_create,
                      'inexistent_package', 'package', 'public')

    def test_member_create_raises_if_object_type_is_invalid(self):
        assert_raises(logic.ValidationError,
                      self._member_create,
                      'obj_id', 'invalid_obj_type', 'public')

    def test_member_list(self):
        self._member_create(self.pkgs[0].id, 'package', 'public')
        self._member_create(self.pkgs[1].id, 'package', 'public')
        res = self._member_list('package')
        assert (self.pkgs[0].id, 'package', 'public') in res
        assert (self.pkgs[1].id, 'package', 'public') in res

        res = self._member_list('user', 'admin')
        assert len(res) == 0, res

        assert_raises(logic.NotFound,
                      self._member_list, 'user', 'admin', 'inexistent_group')

        self._member_create(self.user.id, 'user', 'admin')
        res = self._member_list('user', 'admin')
        assert (self.user.id, 'user', 'Admin') in res, res

    def test_member_create_accepts_group_name_or_id(self):
        for group_key in [self.group.id, self.group.name]:
            self._member_create(self.user.id, 'user', 'admin')

            self._member_delete_in_group(self.user.id, 'user', group_key)

            res = self._member_list('user', 'admin')
            assert (self.user.id, 'user', 'Admin') not in res, res

    def test_member_delete_accepts_object_name_or_id(self):
        for key in [self.user.id, self.user.name]:
            self._member_create(key, 'user', 'admin')

            self._member_delete(key, 'user')

            res = self._member_list('user', 'admin')
            assert (self.user.id, 'user', 'Admin') not in res, res

    def test_member_delete_raises_if_user_unauthorized_to_update_group(self):
        ctx, dd = self._build_context(self.pkgs[0].id, 'package',
                                      user='unauthorized_user')
        assert_raises(logic.NotAuthorized,
                      logic.get_action('member_delete'), ctx, dd)

    def test_member_delete_raises_if_any_required_parameter_isnt_defined(self):
        ctx, dd = self._build_context(self.pkgs[0].id, 'package')
        for key in ['id', 'object', 'object_type']:
            new_dd = dd.copy()
            del new_dd[key]
            assert_raises(logic.ValidationError,
                          logic.get_action('member_delete'), ctx, new_dd)

    def test_member_delete_raises_if_group_wasnt_found(self):
        assert_raises(logic.NotFound,
                      self._member_delete_in_group,
                      self.pkgs[0].id, 'package', 'inexistent_group')

    def test_member_delete_raises_if_object_wasnt_found(self):
        assert_raises(logic.NotFound,
                      self._member_delete, 'unexistent_package', 'package')

    def test_member_delete_raises_if_object_type_is_invalid(self):
        assert_raises(logic.ValidationError,
                      self._member_delete, 'obj_id', 'invalid_obj_type')

    def _member_create(self, obj, obj_type, capacity):
        '''Makes the given object a member of cls.group.'''
        ctx, dd = self._build_context(obj, obj_type, capacity)
        return logic.get_action('member_create')(ctx, dd)

    def _member_create_in_group(self, obj, obj_type, capacity, group_id):
        '''Makes the given object a member of the given group.'''
        ctx, dd = self._build_context(obj, obj_type, capacity, group_id)
        return logic.get_action('member_create')(ctx, dd)

    def _member_create_as_user(self, obj, obj_type, capacity, user):
        '''Makes the given object a member of cls.group using privileges of
        the given user.'''
        ctx, dd = self._build_context(obj, obj_type, capacity, user=user)
        return logic.get_action('member_create')(ctx, dd)

    def _member_list(self, obj_type=None, capacity=None, group_id=None):
        ctx, dd = self._build_context(None, obj_type, capacity, group_id)
        return logic.get_action('member_list')(ctx, dd)

    def _member_delete(self, obj, obj_type):
        ctx, dd = self._build_context(obj, obj_type)
        return logic.get_action('member_delete')(ctx, dd)

    def _member_delete_in_group(self, obj, obj_type, group_id):
        ctx, dd = self._build_context(obj, obj_type, group_id=group_id)
        return logic.get_action('member_delete')(ctx, dd)

    def _member_create_group_hierarchy(self, parent_group, child_group, user):
        ctx, dd = self._build_context(parent_group.name, 'group', 'parent',
                                      group_id=child_group.name, user=user.id)
        return logic.get_action('member_create')(ctx, dd)

    def _build_context(self, obj, obj_type, capacity='public',
                       group_id=None, user=None):
        ctx = {'model': model,
               'session': model.Session,
               'user': user or self.user.id}
        ctx['auth_user_obj'] = model.User.get(ctx['user'])
        dd = {'id': group_id or self.group.name,
              'object': obj,
              'object_type': obj_type,
              'capacity': capacity}
        return ctx, dd
