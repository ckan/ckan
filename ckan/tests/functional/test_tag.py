from ckan.tests import *

class TestTagController(TestController2):

    def test_index(self):
        offset = url_for(controller='tag')
        res = self.app.get(offset)
        assert 'Tags - Index' in res
        assert 'list of tags' in res
        assert 'search for tags' in res

    def test_read(self):
        name = 'tolstoy'
        pkgname = 'warandpeace'
        offset = url_for(controller='tag', action='read', id=name)
        res = self.app.get(offset)
        assert 'Tags - %s' % name in res
        assert name in res
        res = res.click(pkgname)
        assert 'Packages - %s' % pkgname in res

    def test_list_short(self):
        offset = url_for(controller='tag', action='list')
        res = self.app.get(offset)
        print str(res)
        assert 'Tags - List' in res
        tagname = 'tolstoy'
        assert tagname in res
        #assert '(2 packages)' in res
        res = res.click(tagname)
        assert 'Tag: %s' % tagname in res
        offset = url_for(controller='tag', action='list', id=0)
        res = self.app.get(offset)
        print str(res)
        assert 'Tags - List' in res
        assert tagname in res
        #assert '(2 packages)' in res
        assert 'There are 2 tags.' in res
        offset = url_for(controller='tag', action='list', id=50)
        res = self.app.get(offset)
        print str(res)
        assert 'Tags - List' in res
        assert tagname in res
        assert 'There are 2 tags.' in res
        # Avoid interactions.
        offset = url_for(controller='tag', action='list', id=0)
    
    def test_list_long(self):
        self.create_100_tags()
        try:
            # Page 1.
            print
            offset = url_for(controller='tag', action='list', id=1)
            print offset
            res = self.app.get(offset)
            print str(res)
            assert 'Tags - List' in res
            # tolstoy not in because now a 100 tags starting 'test'
            assert 'tolstoy' not in res
            assert 'testtag31' in res
            assert not 'testtag81' in res
            assert not 'testtag99' in res
            assert 'Next' in res
            assert not 'Previous' in res
            assert 'Displaying tags 1 - 50 of 102' in res
            # Page 2.
            offset = url_for(controller='tag', action='list', id=2)
            print offset
            print "Path offset: %s" % offset
            res = self.app.get(offset)
            print str(res)
            assert 'Tags - List' in res
            assert not 'tolstoy' in res
            assert not 'testtag31' in res
            assert 'testtag81' in res
            assert 'Next' in res
            assert 'Previous' in res
            assert 'Displaying tags 51 - 100 of 102' in res
            # Page 3.
            offset = url_for(controller='tag', action='list', id=3)
            res = self.app.get(offset)
            print str(res)
            assert 'Tags - List' in res
            assert not 'testtag31' in res
            assert not 'testtag81' in res
            assert 'tolstoy' in res
            assert 'testtag99' in res
            assert not 'Next' in res
            assert 'Previous' in res
            assert 'Displaying tags 101 - 102 of 102' in res
        finally:
            self.purge_100_tags()

    def test_search(self):
        offset = url_for(controller='tag', action='search')
        res = self.app.get(offset)
        assert 'Tags - Search' in res
        search_term = 's'
        fv = res.forms[0]
        print fv.fields
        fv['search_terms'] =  str(search_term)
        res = fv.submit()
        assert 'Tags - Search' in res
        assert 'There are 2 results' in res
        assert 'russian' in res
        assert 'tolstoy' in res

    def test_autocomplete(self):
        offset = url_for(controller='tag', action='autocomplete')
        res = self.app.get(offset)
        assert '[]' in res
        offset = url_for(controller='tag', action='autocomplete', incomplete='russian')
        res = self.app.get(offset)
        assert 'russian' in res
        assert 'tolstoy' not in res
        offset = url_for(controller='tag', action='autocomplete', incomplete='tolstoy')
        res = self.app.get(offset)
        assert 'russian' not in res
        assert 'tolstoy' in res

