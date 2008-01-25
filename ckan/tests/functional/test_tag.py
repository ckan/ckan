from ckan.tests import *
# Todo: Move this file to tests/controller/test_tag.py?

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

    def test_list(self):
        tagname = 'tolstoy'
        offset = url_for(controller='tag', action='list')
        res = self.app.get(offset)
        assert 'Tags - List' in res
        assert tagname in res
        print str(res)
        assert '(2 packages)' in res
        res = res.click(tagname)
        assert 'Tags - %s' % tagname in res
    
    def test_page_short(self):
        offset = url_for(controller='tag', action='page')
        res = self.app.get(offset)
        print str(res)
        assert 'Tags - List' in res
        tagname = 'tolstoy'
        assert tagname in res
        assert '(2 packages)' in res
        res = res.click(tagname)
        assert 'Tag: %s' % tagname in res
        offset = url_for(controller='tag', action='page', id=0)
        res = self.app.get(offset)
        print str(res)
        assert 'Tags - List' in res
        assert tagname in res
        assert '(2 packages)' in res
        assert 'There are 2 tags.' in res
        offset = url_for(controller='tag', action='page', id=50)
        res = self.app.get(offset)
        print str(res)
        assert 'Tags - List' in res
        assert tagname in res
        assert 'There are 2 tags.' in res
        # Avoid interactions.
        offset = url_for(controller='tag', action='page', id=0)
    
    def test_page_long(self):
        self.create_100_tags()
        try:
            # Page 0.
            print
            offset = url_for(controller='tag', action='page', id=0)
            print offset
            res = self.app.get(offset)
            print str(res)
            assert 'Tags - List' in res
            assert 'tolstoy' in res
            assert 'pagetesttag31' in res
            assert not 'pagetesttag81' in res
            assert not 'pagetesttag99' in res
            assert 'Next' in res
            assert not 'Previous' in res
            assert 'Displaying tags 1 - 50 of 102' in res
            # Page 1.
            offset = url_for(controller='tag', action='page', id=50)
            print offset
            print "Path offset: %s" % offset
            res = self.app.get(offset)
            print str(res)
            assert 'Tags - List' in res
            assert not 'tolstoy' in res
            assert not 'pagetesttag31' in res
            assert 'pagetesttag81' in res
            assert 'Next' in res
            assert 'Previous' in res
            assert 'Displaying tags 51 - 100 of 102' in res
            # Page 2.
            offset = url_for(controller='tag', action='page', id=100)
            res = self.app.get(offset)
            print str(res)
            assert 'Tags - List' in res
            assert not 'tolstoy' in res
            assert not 'pagetesttag31' in res
            assert not 'pagetesttag81' in res
            assert 'pagetesttag98' in res
            assert 'pagetesttag99' in res
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

