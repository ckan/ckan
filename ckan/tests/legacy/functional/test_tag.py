# encoding: utf-8

import json

from ckan.tests.legacy import *
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

    def test_autocomplete(self):
        controller = 'api'
        action = 'tag_autocomplete'
        offset = url_for(controller=controller, action=action, ver=2)
        res = self.app.get(offset)
        assert '[]' in res
        offset = url_for(controller=controller, action=action, incomplete='russian', ver=2)
        res = self.app.get(offset)
        assert 'russian' in res
        assert 'tolstoy' not in res
        offset = url_for(controller=controller, action=action, incomplete='tolstoy', ver=2)
        res = self.app.get(offset)
        assert 'russian' not in res
        assert 'tolstoy' in res

    def test_autocomplete_with_capital_letter_in_search_term(self):
        controller = 'api'
        action = 'tag_autocomplete'
        offset = url_for(controller=controller, action=action, incomplete='Flex', ver=2)
        res = self.app.get(offset)
        data = json.loads(res.body)
        assert u'Flexible \u30a1' in data['ResultSet']['Result'][0].values()

    def test_autocomplete_with_space_in_search_term(self):
        controller = 'api'
        action = 'tag_autocomplete'
        offset = url_for(controller=controller, action=action, incomplete='Flexible ', ver=2)
        res = self.app.get(offset)
        data = json.loads(res.body)
        assert u'Flexible \u30a1' in data['ResultSet']['Result'][0].values()

    def test_autocomplete_with_unicode_in_search_term(self):
        controller = 'api'
        action = 'tag_autocomplete'
        offset = url_for(controller=controller, action=action, incomplete=u'ible \u30a1', ver=2)
        res = self.app.get(offset)
        data = json.loads(res.body)
        assert u'Flexible \u30a1' in data['ResultSet']['Result'][0].values()

