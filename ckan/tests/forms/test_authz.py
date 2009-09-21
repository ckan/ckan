import ckan.model as model
import ckan.forms
from ckan.tests import *
import ckan.authz

class DummyContext(object):
    name = u'testuser'
c = DummyContext
form_words = ['reader', 'editor', 'admin', 'visitor', 'logged_in', 'annafan']

class TestRender(object):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        ckan.tests.CreateTestData.create()
        self.authorizer = ckan.authz.Authorizer()
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def test_1_render_not_authorized(self):
        fs = ckan.forms.authz_fs
        anna = model.Package.by_name(u'annakarenina')
        c.user = u'test'
        fs = fs.bind(anna.roles) # bind
        out = fs.render()
        assert out
        print out
        for s in form_words:
            assert s in out, s

    def test_1_render_not_authorized_visitor(self):
        fs = ckan.forms.authz_fs
        anna = model.Package.by_name(u'annakarenina')
        c.user = u''
        c.author = u'123.123.123.123'
        fs = fs.bind(anna.roles) # bind
        out = fs.render()
        assert out
        print out
        for s in form_words:
            assert s in out, s

    def test_1_render_authorized(self):
        fs = ckan.forms.authz_fs
        anna = model.Package.by_name(u'annakarenina')
        c.user = u'annafan'
        fs = fs.bind(anna.roles) # bind
        out = fs.render()
        assert out
        print out
        assert '<tr>' in out
        for s in form_words:
            assert s in out, s

    def test_1_render_authorized_sysadmin(self):
        fs = ckan.forms.authz_fs
        anna = model.Package.by_name(u'annakarenina')
        c.user = u'testsysadmin'
        fs = fs.bind(anna.roles) # bind
        out = fs.render()
        assert out
        print out
        for s in form_words:
            assert s in out, s

class TestSync:
    @classmethod
    def setup_class(self):
        model.Session.remove()
        ckan.tests.CreateTestData.create()
        self.authorizer = ckan.authz.Authorizer()
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def _check_package_roles(self, roles1, roles2):
        assert_str = '%r != %r' % (roles1, roles2)
        for role in roles1:
            if role[1]:
                assert role in roles2, assert_str
        for role in roles2:
            if role[1]:
                assert role in roles1, assert_str

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
                user = model.User.by_name(user)
                params.extend(self._make_param(u'', user.id, role))
        return params

    def _pretty_package_roles(self, package_roles):
        pretty_prs = []
        for pr in package_roles:
            if pr.user:
                pretty_prs.append((pr.user.name, pr.role))
            else:
                pretty_prs.append(('None', pr.role))                
        return pretty_prs

    def _new_pkg(self, index):
        pkg_name = u'testpkg%i' % index
        model.Package(name=pkg_name)
        model.User(name=u'friend')
        model.repo.new_revision()
        model.repo.commit_and_remove()

        pkg = model.Package.by_name(pkg_name)
        user = model.User.by_name(u'annafan')
        model.setup_default_user_roles(pkg, [user])

        user = model.User.by_name(u'annafan')        
        return pkg_name, user

    def _test_change(self, before_roles, after_roles, pkg_name):
        pkg = model.Package.by_name(pkg_name)
##        model.PackageRole(package_id=pkg.id)
##        model.PackageRole(package_id=pkg.id)
##        model.PackageRole(package_id=pkg.id)
        model.repo.new_revision()
        model.repo.commit_and_remove()
        
        pkg = model.Package.by_name(pkg_name)
        pprs = self._pretty_package_roles(pkg.roles)
        self._check_package_roles(pprs, before_roles.items())

#        user = model.User.by_name(u'friend')
#        print "ROLES", model.PackageRole.query.filter_by(user_id=user.id).count()
#        for pr in model.PackageRole.query.filter_by(user_id=user.id).all():
#            print "ROLE %s %s" % (pr.package.name if pr.package else None, pr.role)
            
        params = self._make_params(pkg.roles, after_roles)
        print 'PARAMS', params
        roles = pkg.roles
        blank_roles = model.PackageRole.query.filter_by(package_id=pkg.id).all()
#        roles.extend(blank_roles)
        fs = ckan.forms.authz_fs.bind(roles, data=params)
        model.repo.new_revision()
        fs.sync()

        model.repo.commit_and_remove()

#        user = model.User.by_name(u'friend')
#        print "ROLES", model.PackageRole.query.filter_by(user_id=user.id).count()
#        for pr in model.PackageRole.query.filter_by(user_id=user.id).all():
#            print "ROLE %s %s" % (pr.package.name if pr.package else None, pr.role)
       
        pkg = model.Package.by_name(pkg_name)
        pprs = self._pretty_package_roles(pkg.roles)
        self._check_package_roles(pprs, after_roles.items())

    def test_0_no_change(self):
        pkg_name, user = self._new_pkg(0)
        before_roles = { 'visitor': 'editor',
                         'logged_in': 'editor',
                         user.name: 'admin' }
        after_roles  = { 'visitor': 'editor',
                         'logged_in': 'editor',
                         user.name: 'admin' }
        num_prs_before = model.PackageRole.query.filter_by(user_id=user.id).count()
        self._test_change(before_roles, after_roles, pkg_name)
        num_prs_after = model.PackageRole.query.filter_by(user_id=user.id).count()
        assert num_prs_before == num_prs_after, '%i %i' % (num_prs_before, num_prs_after)


    def test_1_add_role(self):
        pkg_name, user = self._new_pkg(1)

        before_roles = { 'visitor': 'editor',
                         'logged_in': 'editor',
                         user.name: 'admin' }
        after_roles  = { 'visitor': 'editor',
                         'logged_in': 'editor',
                         user.name: 'admin',
                         'friend': 'admin'}

        self._test_change(before_roles, after_roles, pkg_name)

