import ckan.model as model
import ckan.forms
from ckan.tests import *
from ckan.lib.create_test_data import CreateTestData
import ckan.authz
import ckan.forms.authz

class TestRender(object):
    @classmethod
    def setup_class(self):
        CreateTestData.create()
        self.authorizer = ckan.authz.Authorizer()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_render_authorized(self):
        fs = ckan.forms.get_authz_fieldset('package_authz_fs')
        anna = model.Package.by_name(u'annakarenina')
        assert len(anna.roles) == 3, [ (r.user, r.role) for r in anna.roles ]
        fs = fs.bind(anna.roles) # bind
        out = fs.render()
        assert '<tr>' in out
        form_words = ['reader', 'editor', 'admin', 'visitor', 'logged_in', 'annafan']
        for s in form_words:
            assert s in out, s

    def test_get_package_linker(self):
        anna = model.Package.by_name(u'annakarenina')
        linker = ckan.forms.authz.get_package_linker('delete')
        pr = anna.roles[0]
        out = linker(pr)
        assert '<a href="/dataset/authz/%s' % pr.package.name in out, out


class TestSync:
    @classmethod
    def setup_class(self):
        CreateTestData.create_arbitrary([], extra_user_names=[u'friend'])
        self.authorizer = ckan.authz.Authorizer()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_0_no_change(self):
        pkg_name, user = self._new_pkg(0)
        before_roles = { 'visitor': 'editor',
                         'logged_in': 'editor',
                         user.name: 'admin' }
        after_roles  = { 'visitor': 'editor',
                         'logged_in': 'editor',
                         user.name: 'admin' }
        num_prs_before = model.Session.query(model.PackageRole).filter_by(user_id=user.id).count()
        self._test_change(before_roles, after_roles, pkg_name)
        num_prs_after = model.Session.query(model.PackageRole).filter_by(user_id=user.id).count()
        assert num_prs_before == num_prs_after, '%i %i' % (num_prs_before, num_prs_after)

    def _test_1_add_role(self):
        # disabled this test. Adding roles can't be tested here at form level
        # because the code is only in the controller(!)
        pkg_name, user = self._new_pkg(1)
        before_roles = { 'visitor': 'editor',
                         'logged_in': 'editor',
                         user.name: 'admin' }
        after_roles  = { 'visitor': 'editor',
                         'logged_in': 'editor',
                         'friend': 'admin',
                         }
        self._test_change(before_roles, after_roles, pkg_name)

    def _check_package_roles(self, pkgroles, roles2):
        assert len(pkgroles) == len(roles2)
        for r in pkgroles:
            assert roles2[r.user.name] == r.role, (r.user.name, r.role)

    def _make_param(self, package_role_id, user_id, role):
        user_id_key = u'PackageRole-%s-user_id' % package_role_id
        role_key    = u'PackageRole-%s-role' % package_role_id
        return [(user_id_key, unicode(user_id)), (role_key, unicode(role))]

    def _make_params(self, package_roles, new_roles):
        params = []
        usernames_done = []
        for pr in package_roles:
            if pr.user:
                name = pr.user.name
                id = pr.user.id
            else:
                name = ''
                id = ''
            role = unicode(new_roles.get(name, pr.role))
            params.extend(self._make_param(pr.id, id, role))
            usernames_done.append(name)
        for user, role in new_roles.items():
            if user not in usernames_done:
                user = model.User.by_name(unicode(user))
                params.extend(self._make_param(u'', user.id, role))
        return params

    def _new_pkg(self, index):
        pkg_name = u'testpkg%i' % index
        CreateTestData.create_arbitrary([{'name':pkg_name,
                                          'admins':[u'annafan']}])
        pkg = model.Package.by_name(pkg_name)
        user = model.User.by_name(u'annafan')
        assert pkg
        assert user
        model.repo.commit_and_remove()

        user = model.User.by_name(u'annafan')        
        return pkg_name, user

    def _test_change(self, before_roles, after_roles, pkg_name):
        pkg = model.Package.by_name(pkg_name)
        self._check_package_roles(pkg.roles, before_roles)

        params = self._make_params(pkg.roles, after_roles)
        roles = pkg.roles
        fs = ckan.forms.get_authz_fieldset('package_authz_fs').bind(roles, data=params)
        fs.sync()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(pkg_name)
        self._check_package_roles(pkg.roles, after_roles)

