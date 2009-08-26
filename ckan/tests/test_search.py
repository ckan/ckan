from ckan.model import Package
from ckan.lib.search import Search
from ckan.controllers.package import MockMode
import ckan.model as model
from ckan.tests import *

class TestSearch(object):

    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()
        self.anna = model.Package.by_name('annakarenina')
        self.war = model.Package.by_name('warandpeace')
        self.russian = model.Tag.by_name('russian')
        self.tolstoy = model.Tag.by_name('tolstoy')

    @classmethod
    def teardown_class(self):
        # CreateTestData.delete()
        model.repo.rebuild_db()
        model.Session.remove()

    def test_name(self):
        result = Search().run(u'anna')
        assert result == ([self.anna], []), result

        result = Search().run(u'name:anna')
        assert result == ([self.anna], []), result

        result = Search().run(u'name:Novel')
        assert result == ([], []), result

        result = Search().run(u'war')
        assert result == ([self.war], []), result

        result = Search().run(u'andpeace')
        assert result == ([self.war], []), result

        result = Search().run(u'a')
        # order not important
        assert result == ([self.war, self.anna], [self.russian]) or \
               result == ([self.anna, self.war], [self.russian]), result

        result = Search().run(u'z')
        assert result == ([], []), result

    def test_title(self):
        result = Search().run(u'Novel')
        assert result == ([self.anna], []), result

        result = Search().run(u'"A Novel By Tolstoy"')
        assert result == ([self.anna], []), result

        result = Search().run(u'"Novel Tolstoy"')
        assert result == ([], []), result

        result = Search().run(u'title:Novel')
        assert result == ([self.anna], []), result

        result = Search().run(u'title:"A Novel By Tolstoy"')
        assert result == ([self.anna], []), result

        result = Search().run(u'title:anna')
        assert result == ([], []), result

        result = Search().run(u'Novel Story')
        # order not important
        assert result == ([self.war, self.anna], []) or \
               result == ([self.anna, self.war], []), result

        result = Search().run(u'Novel Tolstoy')
        assert result == ([self.anna], [self.tolstoy]), result

        result = Search().run(u'"Novel Tolstoy"')
        assert result == ([], []), result

        result = Search().run(u'"A Wonderful"')
        assert result == ([self.war], []), result

    def test_tags(self):
        result = Search().run(u'russian')
        assert result == ([], [self.russian]), result

        result = Search().run(u'russ')
        assert result == ([], [self.russian]), result

        result = Search().run(u'tolstoy')
        assert result == ([self.anna], [self.tolstoy]), result

        result = Search().run(u'russian Story')
        assert result == ([self.war], [self.russian]), result

        result = Search().run(u'tags:russian')
        # order not important
        assert result == ([self.war, self.anna], [self.russian]) or \
               result == ([self.anna, self.war], [self.russian]), result

        result = Search().run(u'tags:russian Story')
        # order important - War and Peace higher rank
        assert result == ([self.war, self.anna], [self.russian]), result

        result = Search().run(u'tags:russian Novel')
        # order important - Anna higher rank
        assert result == ([self.anna, self.war], [self.russian]), result

        
