from ckan.tests import *
import ckan.model as model

# TODO: purge revisions after creating them
class TestRevisionController(TestController2):

    @classmethod
    def setup_class(self):
        model.Session.remove()
        # rebuild db before this test as it depends delicately on what
        # revisions exist
        model.repo.rebuild_db()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()

    def test_link_major_navigation(self):
        offset = url_for(controller='home')
        res = self.app.get(offset)
        res = res.click('Recent Changes')
        assert 'Repository History' in res

    def test_paginated_list(self):
        try:
            self.create_100_revisions()
            revisions = model.repo.history().all()
            revision1 = revisions[0]
            revision2 = revisions[50]
            revision3 = revisions[100]
            revision4 = revisions[-1]
            # Revisions are most recent first, with first rev on last page.
            # Todo: Look at the model to see which revision is last.
            # Todo: Test for last revision on first page.
            # Todo: Test for first revision on last page.
            # Todo: Test for last revision minus 50 on second page.
            # Page 1.   (Implied id=1)
            offset = url_for(controller='revision', action='list')
            res = self.app.get(offset)
            self.assert_click(res, revision1.id, 'Revision: %s' % revision1.id)
    
            # Page 1.
            offset = url_for(controller='revision', action='list', id=1)
            res = self.app.get(offset)
            self.assert_click(res, revision1.id, 'Revision: %s' % revision1.id)
            
	    # Page 2.
            offset = url_for(controller='revision', action='list', id=2)
            res = self.app.get(offset)
            self.assert_click(res, revision2.id, 'Revision: %s' % revision2.id)
            
	    # Page 3.
            offset = url_for(controller='revision', action='list', id=3)
            res = self.app.get(offset)
            self.assert_click(res, revision3.id, 'Revision: %s' % revision3.id)
 
            # Last page.
            last_id = 1 + len(revisions) / 50
            offset = url_for(controller='revision', action='list', id=last_id)
            res = self.app.get(offset)

            print str(res)
            assert 'Repository History' in res
            assert '1' in res
            assert 'Author' in res
            assert 'tolstoy' in res
            assert 'Log Message' in res
            assert 'Creating test data.' in res

        finally:
            self.purge_100_revisions()

    def assert_click(self, res, link_exp, res2_exp):
        try:
            # paginate links are also just numbers
            # res2 = res.click('^%s$' % link_exp)
            res2 = res.click(href='revision/read/%s$' % link_exp)
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
        for i in range(0,100):
            rev = model.repo.new_revision()
            rev.author = "Test Revision %s" % i
            model.repo.commit()

    def purge_100_revisions(self):
        pass

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

    def test_list_format_atom(self):
        self.create_100_revisions()
        revisions = model.repo.history().all()
        revision1 = revisions[0]
        try:
            # Revisions are most recent first, with first rev on last page.
            # Todo: Look at the model to see which revision is last.
            # Todo: Test for last revision on first page.
            # Todo: Test for first revision on last page.
            # Todo: Test for last revision minus 50 on second page.
            # Page 1.   (Implied id=1)
            offset = url_for(controller='revision', action='list')
            res = self.app.get(offset + '?format=atom')
            print res
            assert '<feed' in res
            assert 'xmlns="http://www.w3.org/2005/Atom"' in res
            assert '</feed>' in res
            # Todo: Better test for 'days' request param.
            #  - fake some older revisions and check they aren't included.
            res = self.app.get(offset + '?format=atom&days=30')
            print res
            assert '<feed' in res
            assert 'xmlns="http://www.w3.org/2005/Atom"' in res
            assert '</feed>' in res
        finally:
            self.purge_100_revisions()


