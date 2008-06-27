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

    def test_list_long(self):
        self.create_100_revisions()
        try:
            # Revisions are most recent first, with first rev on last page.
            # Todo: Look at the model to see which revision is last.
            # Todo: Test for last revision on first page.
            # Todo: Test for first revision on last page.
            # Todo: Test for last revision minus 50 on second page.
            # Page 1.   (Implied id=0)
            offset = url_for(controller='revision', action='list')
            res = self.app.get(offset)
            self.assert_click(res, '2', 'Revision 2')
            # Page 1.
            offset = url_for(controller='revision', action='list', id=0)
            res = self.app.get(offset)
            self.assert_click(res, '4', 'Revision 4')
            # Page 2.
            offset = url_for(controller='revision', action='list', id=50)
            res = self.app.get(offset)
            self.assert_click(res, '52', 'Revision 52')
            # Last page.
        finally:
            self.purge_100_revisions()

    def assert_click(self, res, link_exp, res2_exp):
        # NB: Must .click('^2$') and not just '2' as twill with otherwise
        #     follow the second link found on the page.
        try:
            res2 = res.click('^%s$' % link_exp)
        except:
            print "\nThe first response (list):\n\n"
            print str(res)
            print "\nThe link that couldn't be followed:"
            print str(link_exp)
            raise
        try:
            assert res2_exp in res2
        except:
            print "\nThe first response (list):\n\n"
            print str(res)
            print "\nThe second response (item):\n\n"
            print str(res2)
            print "\nThe followed link:"
            print str(link_exp)
            print "\nThe expression that couldn't be found:"
            print str(res2_exp)
            raise


    def create_100_revisions(self):
        # Todo: Need to generate revisions, not sure how.....
        self.create_100_tags()

    def purge_100_revisions(self):
        self.purge_100_tags()

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
