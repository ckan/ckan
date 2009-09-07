import simplejson

from ckan.model import Package
from ckan.lib.search import Search, SearchOptions
import ckan.model as model
from ckan.tests import *

class TestSearch(object):

    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateSearchTestData.create()
        self.gils = model.Package.by_name(u'gils')
        self.war = model.Package.by_name(u'warandpeace')
        self.russian = model.Tag.by_name(u'russian')
        self.tolstoy = model.Tag.by_name(u'tolstoy')

    @classmethod
    def teardown_class(self):
        # CreateTestData.delete()
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def _pkg_names(self, result):
        return ' '.join(result['results'])

    def _check_pkg_names(self, result, names_in_result):
        names = result['results']
        for name in names_in_result:
            if name not in names:
                return False
        return True

    def test_1_all_records(self):
        # all records (g)
        result = Search().search(u'g')
        assert 'gils' in result['results'], result['results']
        assert result['count'] > 5, result['count']

    def test_1_name(self):
        # exact name
        result = Search().search(u'gils')
        assert self._pkg_names(result) == 'gils', self._pkg_names(result)
        assert result['count'] == 1, result

    def test_1_name_partial(self):
        # partial name
        result = Search().search(u'gil')
        assert self._pkg_names(result) == 'gils', self._pkg_names(result)
        assert result['count'] == 1, self._pkg_names(result)

    def test_1_name_multiple_results(self):
        result = Search().search(u'gov')
        assert self._check_pkg_names(result, ('us-gov-images', 'usa-courts-gov')), self._pkg_names(result)
        assert result['count'] == 6, self._pkg_names(result)

    def test_1_name_token(self):
        result = Search().search(u'name:gils')
        assert self._pkg_names(result) == 'gils', self._pkg_names(result)

        result = Search().search(u'title:gils')
        assert not self._check_pkg_names(result, ('gils')), self._pkg_names(result)

    def test_2_title(self):
        # exact title, one word
        result = Search().search(u'Opengov.se')
        assert self._pkg_names(result) == 'se-opengov', self._pkg_names(result)

        # part word
        result = Search().search(u'gov.se')
        assert self._pkg_names(result) == 'se-opengov', self._pkg_names(result)

        # multiple words
        result = Search().search(u'Government Expenditure')
        assert self._pkg_names(result) == 'uk-government-expenditure', self._pkg_names(result)

        # multiple words wrong order
        result = Search().search(u'Expenditure Government')
        assert self._pkg_names(result) == 'uk-government-expenditure', self._pkg_names(result)

        # multiple words, one doesn't match
        result = Search().search(u'Expenditure Government China')
        assert self._pkg_names(result) == '', self._pkg_names(result)

        # multiple words quoted
        result = Search().search(u'"Government Expenditure"')
        assert self._pkg_names(result) == 'uk-government-expenditure', self._pkg_names(result)

        # multiple words quoted wrong order
        result = Search().search(u'"Expenditure Government"')
        assert self._pkg_names(result) == '', self._pkg_names(result)

        # token
        result = Search().search(u'title:gov.se')
        assert self._pkg_names(result) == 'se-opengov', self._pkg_names(result)

        # token
        result = Search().search(u'title:gils')
        assert self._pkg_names(result) == '', self._pkg_names(result)

        # token
        result = Search().search(u'randomthing')
        assert self._pkg_names(result) == '', self._pkg_names(result)

    def test_tags_field(self):
        result = Search().search(u'country-sweden')
        assert self._check_pkg_names(result, ['se-publications', 'se-opengov']), self._pkg_names(result)

    def test_tags_token_simple(self):
        result = Search().search(u'tags:country-sweden')
        assert self._check_pkg_names(result, ['se-publications', 'se-opengov']), self._pkg_names(result)

        result = Search().search(u'tags:wildlife')
        assert self._pkg_names(result) == 'us-gov-images', self._pkg_names(result)

    def test_tags_token_multiple(self):
        result = Search().search(u'tags:country-sweden tags:format-pdf')
        assert self._pkg_names(result) == 'se-publications', self._pkg_names(result)

    def test_tags_token_complicated(self):
        result = Search().search(u'tags:country-sweden tags:somethingrandom')
        assert self._pkg_names(result) == '', self._pkg_names(result)

    def test_pagination(self):
        # large search
        all_results = Search().search(u'g')
        all_pkgs = all_results['results']
        all_pkg_count = all_results['count']

        # limit
        options = SearchOptions({'q':u'g'})
        options.limit = 2
        result = Search().run(options)
        pkgs = result['results']
        count = result['count']
        assert len(pkgs) == 2, pkgs
        assert count == all_pkg_count
        assert pkgs == all_pkgs[:2]

        # offset
        options = SearchOptions({'q':u'g'})
        options.limit = 2
        options.offset = 2
        results = Search().run(options)
        pkgs = results['results']
        assert len(pkgs) == 2, pkgs
        assert pkgs == all_pkgs[2:4]

        # larger offset
        options = SearchOptions({'q':u'g'})
        options.limit = 2
        options.offset = 4
        result = Search().run(options)
        pkgs = result['results']
        assert len(pkgs) == 2, pkgs
        assert pkgs == all_pkgs[4:6]

    def test_order_by(self):
        # large search
        all_results = Search().search(u'g')
        all_pkgs = all_results['results']
        all_pkg_count = all_results['count']

        # name
        options = SearchOptions({'q':u'g'})
        options.order_by = 'name'
        result = Search().run(options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        sorted_fields = fields; sorted_fields.sort()
        assert fields == sorted_fields, repr(fields) + repr(sorted_fields)
        assert pkgs == all_pkgs, pkgs #default ordering        

        # title
        options = SearchOptions({'q':u'g'})
        options.order_by = 'title'
        result = Search().run(options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).title for pkg_name in pkgs]
        sorted_fields = fields; sorted_fields.sort()
        assert fields == sorted_fields, repr(fields) + repr(sorted_fields)

        # notes
        options = SearchOptions({'q':u'g'})
        options.order_by = 'notes'
        result = Search().run(options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).notes for pkg_name in pkgs]
        sorted_fields = fields; sorted_fields.sort()
        assert fields == sorted_fields, repr(fields) + repr(sorted_fields)

    def test_search_notes_off(self):
        options = SearchOptions({'q':u'restrictions'})
        options.search_notes = False
        result = Search().run(options)
        pkgs = result['results']
        count = result['count']
        assert len(pkgs) == 0, pkgs

    def test_search_notes_on(self):
        options = SearchOptions({'q':u'restrictions'})
        options.search_notes = True
        result = Search().run(options)
        pkgs = result['results']
        count = result['count']
        assert len(pkgs) == 2, pkgs
        # TODO fix this

        
