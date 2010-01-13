import simplejson

import ckan.model as model
from ckan.tests import *
from ckan.lib.base import *
import ckan.authz as authz

class TestPackageEditAuthz(TestController):
    @classmethod
    def setup_class(self):
        model.repo.rebuild_db()
        model.repo.new_revision()
        
        self.sysadmin = 'madeup-sysadmin'
        sysadmin_user = model.User(name=unicode(self.sysadmin))
        self.admin = 'madeup-administrator'
        admin_user = model.User(name=unicode(self.admin))
        self.another = u'madeup-another'
        another_user = model.User(name=unicode(self.another))
        for obj in sysadmin_user, admin_user, another_user:
            model.Session.add(obj)

        model.add_user_to_role(sysadmin_user, model.Role.ADMIN, model.System())
        model.repo.new_revision()

        self.pkgname = u'test6'
        self.pkgname2 = u'test6a'
        pkg = model.Package(name=self.pkgname)
        pkg2 = model.Package(name=self.pkgname2)
        model.Session.add(pkg)
        model.Session.add(pkg2)
        admin_user = model.User.by_name(unicode(self.admin))
        assert admin_user
        model.setup_default_user_roles(pkg, admins=[admin_user])
        model.setup_default_user_roles(pkg2, admins=[admin_user])

        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_0_nonadmin_cannot_edit_authz(self):
        offset = url_for(controller='package', action='authz', id=self.pkgname)
        res = self.app.get(offset, status=[302, 401])
        res = res.follow()
        assert res.request.url.startswith('/user/login')
        # Alternative if we allowed read-only access
        # res = self.app.get(offset)
        # assert not '<form' in res, res
    
    def test_1_admin_has_access(self):
        offset = url_for(controller='package', action='authz', id=self.pkgname)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.admin})

    def test_1_sysadmin_has_access(self):
        offset = url_for(controller='package', action='authz', id=self.pkgname)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.sysadmin})
    
    def test_2_read_ok(self):
        offset = url_for(controller='package', action='authz', id=self.pkgname)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.admin})
        print res
        assert self.pkgname in res
        assert '<tr' in res
        assert self.admin in res
        assert 'Role' in res
        for uname in [ model.PSEUDO_USER__VISITOR, self.admin ]:
            assert '%s' % uname in res
        # crude but roughly correct
        pkg = model.Package.by_name(self.pkgname)
        for r in pkg.roles:
            assert '<select id="PackageRole-%s-role' % r.id in res

        # now test delete links
        pr = pkg.roles[0]
        href = '%s' % pr.id
        assert href in res, res

    def _prs(self, pkgname):
        pkg = model.Package.by_name(pkgname)
        return dict([ (getattr(r.user, 'name', 'USER NAME IS NONE'), r) for r in pkg.roles ])

    def test_3_admin_changes_role(self):
        # load authz page
        offset = url_for(controller='package', action='authz', id=self.pkgname)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.admin})
        assert self.pkgname in res

        def _r(r):
            return 'PackageRole-%s-role' % r.id
        def _u(r):
            return 'PackageRole-%s-user_id' % r.id

        prs = self._prs(self.pkgname)
        assert prs['visitor'].role == model.Role.EDITOR
        assert prs['logged_in'].role == model.Role.EDITOR
        form = res.forms[0]
        
        # change role assignments
        form.select(_r(prs['visitor']), model.Role.READER)
        form.select(_r(prs['logged_in']), model.Role.ADMIN)
        res = form.submit('commit', extra_environ={'REMOTE_USER': self.admin})
        model.repo.commit_and_remove()

        # ensure db was changed
        prs = self._prs(self.pkgname)
        assert len(prs) == 3, prs
        assert prs['visitor'].role == model.Role.READER
        assert prs['logged_in'].role == model.Role.ADMIN

        # ensure rerender of form is changed
        offset = url_for(controller='package', action='authz', id=self.pkgname)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.admin})
        assert self.pkgname in res
        fv = res.forms[0]
        visitor_options = fv[_r(prs['visitor'])].options
        assert ('reader', True) in visitor_options, visitor_options
        logged_in_options = fv[_r(prs['logged_in'])].options
        assert ('admin', True) in logged_in_options, logged_in_options

    def test_3_sysadmin_changes_role(self):
        # load authz page
        offset = url_for(controller='package', action='authz', id=self.pkgname2)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.sysadmin})
        assert self.pkgname2 in res

        def _r(r):
            return 'PackageRole-%s-role' % r.id
        def _u(r):
            return 'PackageRole-%s-user_id' % r.id

        prs = self._prs(self.pkgname2)
        assert prs['visitor'].role == model.Role.EDITOR
        assert prs['logged_in'].role == model.Role.EDITOR
        form = res.forms[0]
        
        # change role assignments
        form.select(_r(prs['visitor']), model.Role.READER)
        form.select(_r(prs['logged_in']), model.Role.ADMIN)
        res = form.submit('commit', extra_environ={'REMOTE_USER': self.sysadmin})
        model.repo.commit_and_remove()

        # ensure db was changed
        prs = self._prs(self.pkgname2)
        assert len(prs) == 3, prs
        assert prs['visitor'].role == model.Role.READER
        assert prs['logged_in'].role == model.Role.ADMIN

        # ensure rerender of form is changed
        offset = url_for(controller='package', action='authz', id=self.pkgname2)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.sysadmin})
        assert self.pkgname2 in res
        fv = res.forms[0]
        visitor_options = fv[_r(prs['visitor'])].options
        assert ('reader', True) in visitor_options, visitor_options
        logged_in_options = fv[_r(prs['logged_in'])].options
        assert ('admin', True) in logged_in_options, logged_in_options
    
    def test_4_admin_deletes_role(self):
        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.roles) == 3
        # make sure not admin
        pr_id = [ r for r in pkg.roles if r.user.name != self.admin ][0].id
        offset = url_for(controller='package', action='authz', id=self.pkgname,
                role_to_delete=pr_id)
        # need this here as o/w conflicts over session binding
        model.Session.remove()
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.admin})
        assert 'Deleted role' in res, res
        assert 'error' not in res, res
        pkg = model.Package.by_name(self.pkgname)
        assert len(pkg.roles) == 2
        assert model.Session.query(model.PackageRole).filter_by(id=pr_id).count() == 0

    def test_4_sysadmin_deletes_role(self):
        pkg = model.Package.by_name(self.pkgname2)
        assert len(pkg.roles) == 3
        # make sure not admin
        pr_id = [ r for r in pkg.roles if r.user.name != self.admin ][0].id
        offset = url_for(controller='package', action='authz', id=self.pkgname2,
                role_to_delete=pr_id)
        # need this here as o/w conflicts over session binding
        model.Session.remove()
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.sysadmin})
        assert 'Deleted role' in res, res
        assert 'error' not in res, res
        pkg = model.Package.by_name(self.pkgname2)
        assert len(pkg.roles) == 2
        assert model.Session.query(model.PackageRole).filter_by(id=pr_id).count() == 0

    def test_5_admin_adds_role(self):
        offset = url_for(controller='package', action='authz', id=self.pkgname)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.admin})
        assert self.pkgname in res
        prs = self._prs(self.pkgname) 
        startlen = len(prs)
        # could be 2 or 3 depending on whether we ran this test alone or not
        # assert len(prs) == 2, prs

        assert 'Create New User Roles' in res
        assert '<select id=' in res, res
        form = res.forms[0]
        another = model.User.by_name(self.another)
        form.select('PackageRole--user_id', another.id)
        form.select('PackageRole--role', model.Role.ADMIN)
        res = form.submit('commit', extra_environ={'REMOTE_USER': self.admin})
        model.Session.remove()

        prs = self._prs(self.pkgname)
        assert len(prs) == startlen+1, prs
        assert prs[self.another].role == model.Role.ADMIN

    def test_5_sysadmin_adds_role(self):
        offset = url_for(controller='package', action='authz', id=self.pkgname2)
        res = self.app.get(offset, extra_environ={'REMOTE_USER':
            self.sysadmin})
        assert self.pkgname2 in res
        prs = self._prs(self.pkgname2) 
        startlen = len(prs)
        # could be 2 or 3 depending on whether we ran this test alone or not
        # assert len(prs) == 2, prs

        assert 'Create New User Roles' in res
        assert '<select id=' in res, res
        form = res.forms[0]
        another = model.User.by_name(self.another)
        form.select('PackageRole--user_id', another.id)
        form.select('PackageRole--role', model.Role.ADMIN)
        res = form.submit('commit', extra_environ={'REMOTE_USER': self.sysadmin})
        model.Session.remove()

        prs = self._prs(self.pkgname2)
        assert len(prs) == startlen+1, prs
        assert prs[self.another].role == model.Role.ADMIN

