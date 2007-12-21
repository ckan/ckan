from ckan.tests import *

class TestPackageController(TestController2):

    def test_index(self):
        offset = url_for(controller='tag')
        res = self.app.get(offset)
        assert 'Tags - Index' in res

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
    
    def test_search(self):
        offset = url_for(controller='tag', action='search')
        res = self.app.get(offset)
        assert 'Tags - Search' in res
        search_term = 's'
        fv = res.forms[0]
        fv['search_terms'] =  search_term
        res = fv.submit()
        assert 'Tags - Search' in res
        assert 'There are 2 results' in res
        assert 'russian' in res
        assert 'tolstoy' in res

