from ckan.tests import *

class TestRevisionController(TestController2):

    def test_link_major_navigation(self):
        offset = url_for(controller='home')
        res = self.app.get(offset)
        res = res.click('Recent Changes')
        assert 'Repository History' in res

    def test_index(self):
        offset = url_for(controller='revision')
        res = self.app.get(offset)
        self._test_list(res)

    def test_list(self):
        offset = url_for(controller='revision', action='list')
        res = self.app.get(offset)
        self._test_list(res)

    def _test_list(self, res):
        # order that tests are run in is not guaranteed so we only know that
        # there are at least 2 revisions in the system
        print str(res)
        assert 'Repository History' in res
        assert '1' in res
        assert 'Author' in res
        assert 'tolstoy' in res
        assert 'Log Message' in res
        assert 'Creating test data.' in res

    def test_list_2(self):
        offset = url_for(controller='revision', action='list')
        res = self.app.get(offset)
        print str(res)
        # must be ^2$ and not just 2 as twill with otherwise follow the second
        # link found on the page
        res = res.click('^2$')
        print str(res)
        assert 'Revision 2' in res

    def test_read_redirect_at_base(self):
        # have to put None as o/w seems to still be at url set in previous test
        offset = url_for(controller='revision', action='read', id=None)
        res = self.app.get(offset)
        # redirect
        res = res.follow()
        print str(res)
        assert 'Repository History' in res

    def test_read(self):
        offset = url_for(controller='revision', action='read', id='2')
        res = self.app.get(offset)
        print str(res)
        assert 'Revision 2' in res
        assert 'Revision: 2' in res
        assert 'Author:</strong> tolstoy' in res
        assert 'Log Message:' in res
        assert 'Creating test data.' in res
        assert 'Package: annakarenina' in res
        assert "Packages' Tags" in res
        res = res.click('annakarenina', index=0)
        assert 'Packages - annakarenina' in res
        
    def test_purge(self):
        offset = url_for(controller='revision', action='purge', id=None)
        res = self.app.get(offset)
        assert 'No revision id specified' in res
        # hmmm i have to be logged in to do proper testing 
        # TODO: come back once login is sorted out
