from ckan.tests import *
import ckan.models

class TestPackageController(TestControllerTwill):

    def setup_class(self):
        repo = ckan.models.repo
        rev = repo.youngest_revision()
        self.anna = rev.model.packages.get('annakarenina')

    def test_index(self):
        offset = url_for(controller='package')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        web.title('Packages - Index')

    def _go_package_home(self):
        offset = url_for(controller='package')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)

    def test_sidebar(self):
        self._go_package_home()
        # sidebar
        web.find('Packages section')

    def test_minornavigation(self):
        self._go_package_home()
        # TODO: make this a bit more rigorous!
        web.find('List')
        web.follow('List')
        web.title('Packages - List')
    
    def test_minornavigation_2(self):
        self._go_package_home()
        web.follow('New')
        web.title('Packages - New')

    def test_read(self):
        name = self.anna.name
        offset = url_for(controller='package', action='read', id=name)
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        print web.show()
        web.title('Packages - %s' % name)
        web.find(name)
        web.find('Url:')
        web.find(self.anna.url)
        web.find('Notes:')
        web.find('Some test notes')
        web.find('<strong>Some bolded text.</strong>')
        web.find('Licenses:')
        web.find('OKD Compliant::')
        web.find('Tags:')
        web.find('russian')

    def test_read_nonexistentpackage(self):
        name = 'anonexistentpackage'
        offset = url_for(controller='package', action='read', id=name)
        url = self.siteurl + offset
        web.go(url)
        web.code(404)

    def test_list(self):
        offset = url_for(controller='package', action='list')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        web.title('Packages - List')
        name = 'annakarenina'
        web.find(name)
        web.follow(name)
        web.code(200)
        web.title('Packages - %s' % name)


class TestPackageControllerEdit(TestControllerTwill):

    def setup_method(self, method):
        super(TestPackageControllerEdit, self).setup_method(method)
        txn = ckan.models.repo.begin_transaction()
        self.editpkg = txn.model.packages.create(name='editpkgtest')
        self.editpkg.url = 'editpkgurl.com'
        self.editpkg.notes='this is editpkg'
        txn.commit()

    def teardown_method(self, method):
        super(TestPackageControllerEdit, self).teardown_method(method)
        rev = ckan.models.repo.youngest_revision()
        rev.model.packages.purge(self.editpkg.name)
        # if method == 'test_edit_2':
            # self._teardown_test_edit2()

    def test_update(self):
        offset = url_for(controller='package', action='update')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        web.title('Packages - Updating')
        web.find('There was an error')

    def test_edit(self):
        offset = url_for(controller='package', action='edit', id=self.editpkg.name)
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        web.title('Packages - Edit')
        # really want to check it is in the form ...
        web.find(self.editpkg.notes)
        fn = 1
        newurl = 'www.editpkgnewurl.com'
        newlicense = 'Non-OKD Compliant::Other'
        web.fv(fn, 'url', newurl)
        web.fv(fn, 'license', newlicense)
        web.submit()
        web.code(200)
        print web.show()
        web.find('Update successful.')
        rev = ckan.models.repo.youngest_revision()
        pkg = rev.model.packages.get(self.editpkg.name)
        assert pkg.url == newurl
        licenses = [ pkg.license.name ]
        assert newlicense in licenses

    def test_edit_2(self):
        offset = url_for(controller='package', action='edit', id=self.editpkg.name)
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        web.title('Packages - Edit')
        # really want to check it is in the form ...
        web.find(self.editpkg.notes)
        fn = 1
        newtags = ['russian']
        tagvalues = ' '.join(newtags)
        web.fv(fn, 'tags', tagvalues)
        exp_log_message = 'test_edit_2: making some changes'
        web.fv(fn, 'log_message', exp_log_message)
        web.submit()
        web.code(200)
        print web.show()
        web.find('Update successful.')
        rev = ckan.models.repo.youngest_revision()
        pkg = rev.model.packages.get(self.editpkg.name)
        assert len(pkg.tags.list()) == 1
        outtags = [ pkg2tag.tag.name for pkg2tag in pkg.tags ]
        for tag in newtags:
            assert tag in outtags 
        # for some reason environ['REMOTE_ADDR'] is undefined when using twill
        assert rev.author == 'Unknown IP Address'
        assert rev.log_message == exp_log_message


class TestPackageControllerNew(TestControllerTwill):

    def setup_class(self):
        self.testvalues = { 'name' : 'testpkg' }

    def teardown_class(self):
        rev = ckan.models.repo.youngest_revision()
        rev.model.packages.purge(self.testvalues['name'])

    def test_create(self):
        offset = url_for(controller='package', action='create')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        web.title('Packages - Creating')
        web.find('There was an error')

    def test_new(self):
        offset = url_for(controller='package', action='new')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        web.title('Packages - New')
        fn = 1
        web.fv(fn, 'name', self.testvalues['name'])
        web.submit()
        web.code(200)
        print web.show()
        web.find('Create successful.')
        rev = ckan.models.repo.youngest_revision()
        pkg = rev.model.packages.get(self.testvalues['name'])
        assert pkg.name == self.testvalues['name']
        # for some reason environ['REMOTE_ADDR'] is undefined when using twill
        assert rev.author == 'Unknown IP Address'
        exp_log_message = 'Creating package %s' % self.testvalues['name']
        assert rev.log_message == exp_log_message
        web.find('To continue editing')
        web.follow(self.testvalues['name'])
        web.code(200)
        web.title('Packages - Edit')

