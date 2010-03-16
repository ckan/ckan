import simplejson

import ckan.model as model
from ckan.tests import *
from ckan.lib.base import *
import ckan.authz as authz

class TestGroupEditAuthz(TestController):
    @classmethod
    def setup_class(self):
        model.repo.rebuild_db()
        model.repo.new_revision()
        self.admin = 'madeup-administrator'
        user = model.User(name=unicode(self.admin))
        model.Session.add(user)
        self.another = u'madeup-another'
        model.Session.add(model.User(name=unicode(self.another)))
        self.groupname = u'test6'
        group = model.Group(name=self.groupname)
        model.setup_default_user_roles(group, admins=[user])
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_0_nonadmin_cannot_edit_authz(self):
        offset = url_for(controller='group', action='authz', id=self.groupname)
        res = self.app.get(offset, status=[302, 401])
        res = res.follow()
        assert res.request.url.startswith('/user/login')
        # Alternative if we allowed read-only access
        # res = self.app.get(offset)
        # assert not '<form' in res, res
    
    def test_1_admin_has_access(self):
        offset_authz = url_for(controller='group', action='authz', id=self.groupname)
        res = self.app.get(offset_authz, extra_environ={'REMOTE_USER':
            self.admin}, status=200)

        # check link is there too
        offset_read = url_for(controller='group', action='read', id=self.groupname)
        res = self.app.get(offset_read, extra_environ={'REMOTE_USER':
            self.admin})
        assert offset_authz in res
        

    def test_2_read_ok(self):
        offset = url_for(controller='group', action='authz', id=self.groupname)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.admin})
        print res
        assert self.groupname in res
        assert '<tr' in res
        assert self.admin in res
        assert 'Role' in res
        for uname in [ model.PSEUDO_USER__VISITOR, self.admin ]:
            assert '%s' % uname in res
        # crude but roughly correct
        group = model.Group.by_name(self.groupname)
        for r in group.roles:
            assert '<select id="GroupRole-%s-role' % r.id in res

        # now test delete links
        pr = group.roles[0]
        href = '%s' % pr.id
        assert href in res, res

    def _prs(self, groupname):
        group = model.Group.by_name(groupname)
        return dict([ (getattr(r.user, 'name', 'USER NAME IS NONE'), r) for r in group.roles ])

    def test_3_admin_changes_role(self):
        # create a role to be deleted
        group = model.Group.by_name(self.groupname)
        model.add_user_to_role(model.User.by_name(u'visitor'), model.Role.READER, group)
        model.repo.commit_and_remove()

        offset = url_for(controller='group', action='authz', id=self.groupname)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.admin})
        assert self.groupname in res

        group = model.Group.by_name(self.groupname)
        assert len(group.roles) == 3, [(grouprole.user.name, grouprole.role) for grouprole in group.roles]

        def _r(r):
            return 'GroupRole-%s-role' % r.id
        def _u(r):
            return 'GroupRole-%s-user_id' % r.id

        prs = self._prs(self.groupname)
        assert prs.has_key('visitor')
        assert prs.has_key('logged_in')
        assert prs.has_key(self.admin), prs
        form = res.forms[0]
        
        # change role assignments
        form.select(_r(prs['visitor']), model.Role.EDITOR)
        res = form.submit('commit', extra_environ={'REMOTE_USER': self.admin})

        model.Session.remove()
        prs = self._prs(self.groupname)
        assert len(prs) == 3, prs
        assert prs['visitor'].role == model.Role.EDITOR
    
    def test_4_admin_deletes_role(self):
        group = model.Group.by_name(self.groupname)
        
        # create a role to be deleted
        model.add_user_to_role(model.User.by_name(u'logged_in'), model.Role.READER, group)
        model.repo.commit_and_remove()
        
        group = model.Group.by_name(self.groupname)
        num_roles_start = len(group.roles)

        # make sure not admin
        pr_id = [ r for r in group.roles if r.user.name != self.admin ][0].id
        offset = url_for(controller='group', action='authz', id=self.groupname,
                role_to_delete=pr_id)
        # need this here as o/w conflicts over session binding
        model.Session.remove()
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.admin})
        assert 'Deleted role' in res, res
        assert 'error' not in res, res
        group = model.Group.by_name(self.groupname)
        assert len(group.roles) == num_roles_start - 1
        assert model.Session.query(model.GroupRole).filter_by(id=pr_id).count() == 0

    def test_5_admin_adds_role(self):
        model.repo.commit_and_remove()
        offset = url_for(controller='group', action='authz', id=self.groupname)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.admin})
        assert self.groupname in res
        prs = self._prs(self.groupname) 
        startlen = len(prs)
        # could be 2 or 3 depending on whether we ran this test alone or not
        # assert len(prs) == 2, prs

        assert 'Create New User Roles' in res
        assert '<select id="GroupRole--user_id"' in res, res
        assert '<td>madeup-administrator</td>' not in res, res
        form = res.forms[0]
        another = model.User.by_name(self.another)
        form.select('GroupRole--user_id', another.id)
        form.select('GroupRole--role', model.Role.ADMIN)
        res = form.submit('commit', extra_environ={'REMOTE_USER': self.admin})
        model.Session.remove()

        prs = self._prs(self.groupname)
        assert len(prs) == startlen+1, prs
        assert prs[self.another].role == model.Role.ADMIN

