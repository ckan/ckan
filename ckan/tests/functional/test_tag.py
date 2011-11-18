import json

from ckan.tests import *
import ckan.model as model

HTTP_MOVED_PERMANENTLY = 301

class TestTagController(TestController):

    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_index(self):
        offset = url_for(controller='tag', action='index')
        res = self.app.get(offset)
        assert 'Tags' in res
        assert 'There are' in res

    def test_read_moved(self):
        name = 'tolstoy'
        offset = '/tag/read/%s' % name
        res = self.app.get(offset, status=HTTP_MOVED_PERMANENTLY)
        res = res.follow()
        assert '%s - Tags' % name in res
        assert name in res
        # res = res.click(pkgname)
        # assert '%s - Data Packages' % pkgname in res

    def test_read(self):
        name = 'tolstoy'
        pkgname = 'warandpeace'
        offset = url_for(controller='tag', action='read', id=name)
        assert offset == '/tag/tolstoy', offset
        res = self.app.get(offset)
        assert '%s - Tags' % name in res
        assert name in res
        # res = res.click(pkgname)
        # assert '%s - Data Packages' % pkgname in res

    def test_list_short(self):
        offset = url_for(controller='tag', action='index')
        res = self.app.get(offset)
        tagname = 'tolstoy'
        assert tagname in res
        #assert '(2 packages)' in res
        res = res.click(tagname)
        assert tagname in res
        offset = url_for(controller='tag', action='index')
        res = self.app.get(offset)
        assert tagname in res
        #assert '(2 packages)' in res
        tag_count = model.Session.query(model.Tag).count()
        assert 'There are <strong>%s</strong> results for tags.' % tag_count in res
        offset = url_for(controller='tag', action='index')
        res = self.app.get(offset)
        assert tagname in res
        tag_count = model.Session.query(model.Tag).count()
        assert 'There are <strong>%s</strong> results for tags.' % tag_count in res
        # Avoid interactions.
        offset = url_for(controller='tag', action='index')
    
    def test_search(self):
        offset = url_for(controller='tag', action='index', id=None)
        res = self.app.get(offset)
        search_term = 's'
        fv = res.forms['tag-search']
        fv['q'] =  str(search_term)
        res = fv.submit()
        assert 'There are <strong>2</strong> results' in res, res
        assert 'russian' in res, res
        assert 'tolstoy' in res, res

    def test_search_with_unicode_term(self):
        offset = url_for(controller='tag', action='index', id=None)
        res = self.app.get(offset)
        search_term = u' \u30a1'.encode('utf8')
        fv = res.forms['tag-search']
        fv['q'] =  str(search_term)
        res = fv.submit()
        assert 'There are <strong>1</strong> results' in res, res
        assert u'Flexible \u30a1' in res, res

    def test_autocomplete(self):
        controller = 'api'
        action = 'tag_autocomplete'
        offset = url_for(controller=controller, action=action)
        res = self.app.get(offset)
        assert '[]' in res
        offset = url_for(controller=controller, action=action, incomplete='russian')
        res = self.app.get(offset)
        assert 'russian' in res
        assert 'tolstoy' not in res
        offset = url_for(controller=controller, action=action, incomplete='tolstoy')
        res = self.app.get(offset)
        assert 'russian' not in res
        assert 'tolstoy' in res

    def test_autocomplete_with_capital_letter_in_search_term(self):
        controller = 'api'
        action = 'tag_autocomplete'
        offset = url_for(controller=controller, action=action, incomplete='Flex')
        res = self.app.get(offset)
        data = json.loads(res.body)
        assert u'Flexible \u30a1' in data['ResultSet']['Result'][0].values()
        
    def test_autocomplete_with_space_in_search_term(self):
        controller = 'api'
        action = 'tag_autocomplete'
        offset = url_for(controller=controller, action=action, incomplete='Flexible ')
        res = self.app.get(offset)
        data = json.loads(res.body)
        assert u'Flexible \u30a1' in data['ResultSet']['Result'][0].values()
        
    def test_autocomplete_with_unicode_in_search_term(self):
        controller = 'api'
        action = 'tag_autocomplete'
        offset = url_for(controller=controller, action=action, incomplete=u'ible \u30a1')
        res = self.app.get(offset)
        data = json.loads(res.body)
        assert u'Flexible \u30a1' in data['ResultSet']['Result'][0].values()

