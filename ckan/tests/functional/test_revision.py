from ckan.tests import *

class TestRevisionController(TestControllerTwill):

    def test_link_major_navigation(self):
        offset = url_for(controller='home')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        web.follow('Recent Changes')
        web.code(200)
        web.title('Repository History')

    def test_index(self):
        offset = url_for(controller='revision')
        url = self.siteurl + offset
        self._test_list(url)

    def test_list(self):
        offset = url_for(controller='revision', action='list')
        url = self.siteurl + offset
        self._test_list(url)

    def _test_list(self, url):
        # order that tests are run in is not guaranteed so we only know that
        # there are at least 2 revisions in the system
        web.go(url)
        web.code(200)
        print web.show()
        web.title('Repository History')
        web.find('1')
        web.find('Author')
        web.find('tolstoy')
        web.find('Log Message')
        web.find('Creating test data.')

    def test_list_2(self):
        offset = url_for(controller='revision', action='list')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        print web.show()
        print web.showlinks()
        # must be ^2$ and not just 2 as twill with otherwise follow the second
        # link found on the page
        web.follow('^2$')
        web.code(200)
        print web.show()
        web.title('Revision 2')

    def test_read_redirect_at_base(self):
        # have to put None as o/w seems to still be at url set in previous test
        offset = url_for(controller='revision', action='read', id=None)
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        print web.show()
        web.title('Repository History')

    def test_read(self):
        offset = url_for(controller='revision', action='read', id='2')
        url = self.siteurl + offset
        web.go(url)
        web.code(200)
        print web.show()
        web.title('Revision 2')
        web.find('Revision: 2')
        web.find('Author:.* tolstoy')
        web.find('Log Message:')
        web.find('Creating test data.')
        web.find(' * Package: annakarenina')
        web.find("Packages' Tags")
        web.follow('annakarenina')
        web.title('Packages - annakarenina')
        
