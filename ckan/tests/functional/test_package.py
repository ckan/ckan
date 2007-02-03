from ckan.tests import *

class TestPackageController(TestControllerTwill):

    def test_index(self):
        offset = url_for(controller='package')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        web.title('Packages - Index')

    def test_layout(self)
        # test sidebar and minor navigation
        offset = url_for(controller='package')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        # sidebar
        web.find('Packages section')
        # minor navigation
        # TODO: make this a bit more rigorous!
        web.find('List')

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

