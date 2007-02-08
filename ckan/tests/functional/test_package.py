from ckan.tests import *
import ckan.models

class TestPackageController(TestControllerTwill):

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
        name = 'annakarenina'
        offset = url_for(controller='package', action='read', id=name)
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        web.title('Packages - %s' % name)
        web.find(name)
        web.find('Notes: ')

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


class TestPackageController2(TestControllerTwill):

    testpkg = { 'name' : 'testpkg', 'url' : 'http://testpkg.org' }
    editpkg = ckan.models.Package(
            name='editpkgtest',
            url='editpkgurl.com',
            notes='this is editpkg'
            )

    def teardown_class(self):
        # TODO call super on this class method
        error = ''
        try:
            ckan.models.dm.packages.purge(self.testpkg['name'])
        except Exception, inst:
            error = str(inst)
        ckan.models.dm.packages.purge(self.editpkg.name)
        if error: raise Exception(error)

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
        fn = 2
        newurl = 'www.editpkgnewurl.com'
        web.fv(fn, 'url', newurl)
        web.submit()
        web.code(200)
        print web.show()
        web.find('Update successful.')
        pkg = ckan.models.Package.byName(self.editpkg.name)
        assert pkg.url == newurl

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
        fn = 2
        web.fv(fn, 'name', self.testpkg['name'])
        web.fv(fn, 'url', self.testpkg['url'])
        web.submit()
        web.code(200)
        print web.show()
        web.find('Create successful.')
        pkg = ckan.models.Package.byName(self.testpkg['name'])
        assert pkg.url == self.testpkg['url']


