from ckan import model
from ckan.logic import get_action
from ckan.lib.create_test_data import CreateTestData

class TestMemberLogic(object):

    @classmethod
    def setup_class(cls):
        cls.username = 'testsysadmin'
        cls.groupname = 'david'

        model.repo.new_revision()
        CreateTestData.create()
        cls.pkgs = [
            model.Package.by_name('warandpeace'),
            model.Package.by_name('annakarenina'),
        ]

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def _build_context( self, obj, obj_type, capacity='public'):
        ctx = { 'model': model,
                'session': model.Session,
                'user':self.username
        }
        dd = {
            'id': self.groupname,
            'object': obj,
            'object_type': obj_type,
            'capacity': capacity }
        return ctx, dd

    def _add_member( self, obj, obj_type, capacity):
        ctx, dd = self._build_context(obj,obj_type,capacity)
        return get_action('member_create')(ctx,dd)

    def test_member_add(self):
        res = self._add_member( self.pkgs[0].id, 'package', 'public')
        assert 'capacity' in res and res['capacity'] == u'public'

    def test_member_list(self):
        _ = self._add_member( self.pkgs[0].id, 'package', 'public')
        _ = self._add_member( self.pkgs[1].id, 'package', 'public')
        ctx, dd = self._build_context('','package')
        res = get_action('member_list')(ctx,dd)
        assert len(res) == 2, res

        ctx, dd = self._build_context('','user', 'admin')
        res = get_action('member_list')(ctx,dd)
        assert len(res) == 0, res

        _ = self._add_member( self.username, 'user', 'admin')
        ctx, dd = self._build_context('','user', 'admin')
        res = get_action('member_list')(ctx,dd)
        assert len(res) == 1, res


    def test_member_delete(self):
        _ = self._add_member( self.username, 'user', 'admin')
        ctx, dd = self._build_context(self.username,'user', 'admin')
        res = get_action('member_list')(ctx,dd)
        assert len(res) == 1, res

        get_action('member_delete')(ctx,dd)

        res = get_action('member_list')(ctx,dd)
        assert len(res) == 0, res
