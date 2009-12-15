import simplejson
import sqlalchemy as sa

from ckan.model import Package
from ckan.lib.search import Search, SearchOptions
import ckan.model as model
from ckan.tests import *

class TestSearch(object):
    q_all = u'penguin'

    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateSearchTestData.create()

        # now remove a tag so we can test search with deleted tags
        model.repo.new_revision()
        gils = model.Package.by_name(u'gils')
        # an existing tag used only by gils
        self.tagname = u'registry'
        # we aren't guaranteed it is last ...
        idx = [ t.name for t in gils.tags].index(self.tagname)
        del gils.tags[idx]
        model.repo.commit_and_remove()

        self.gils = model.Package.by_name(u'gils')
        self.war = model.Package.by_name(u'warandpeace')
        self.russian = model.Tag.by_name(u'russian')
        self.tolstoy = model.Tag.by_name(u'tolstoy')

    @classmethod
    def teardown_class(self):
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

# Can't search for all records in postgres
    def test_1_all_records(self):
        # all records
        result = Search().search(self.q_all)
        assert 'gils' in result['results'], result['results']
        assert result['count'] > 5, result['count']

    def test_1_name(self):
        # exact name
        result = Search().search(u'gils')
        assert self._pkg_names(result) == 'gils', self._pkg_names(result)
        assert result['count'] == 1, result

# Can't search for partial words in postgres
##    def test_1_name_partial(self):
##        # partial name
##        result = Search().search(u'gil')
##        assert self._pkg_names(result) == 'gils', self._pkg_names(result)
##        assert result['count'] == 1, self._pkg_names(result)

    def test_1_name_multiple_results(self):
        result = Search().search(u'gov')
        assert self._check_pkg_names(result, ('us-gov-images', 'usa-courts-gov')), self._pkg_names(result)
        assert result['count'] == 4, self._pkg_names(result)

    def test_1_name_token(self):
        result = Search().search(u'name:gils')
        assert self._pkg_names(result) == 'gils', self._pkg_names(result)

        result = Search().search(u'title:gils')
        assert not self._check_pkg_names(result, ('gils')), self._pkg_names(result)

    def test_2_title(self):
        # exact title, one word
        result = Search().search(u'Opengov.se')
        assert self._pkg_names(result) == 'se-opengov', self._pkg_names(result)

##        # part word
##        result = Search().search(u'gov.se')
##        assert self._pkg_names(result) == 'se-opengov', self._pkg_names(result)

        # multiple words
        result = Search().search(u'Government Expenditure')
        assert self._pkg_names(result) == 'uk-government-expenditure', self._pkg_names(result)

        # multiple words wrong order
        result = Search().search(u'Expenditure Government')
        assert self._pkg_names(result) == 'uk-government-expenditure', self._pkg_names(result)

        # multiple words, one doesn't match
        result = Search().search(u'Expenditure Government China')
        assert self._pkg_names(result) == '', self._pkg_names(result)

# Quotation not supported now
##        # multiple words quoted
##        result = Search().search(u'"Government Expenditure"')
##        assert self._pkg_names(result) == 'uk-government-expenditure', self._pkg_names(result)

##        # multiple words quoted wrong order
##        result = Search().search(u'Expenditure Government')
##        assert self._pkg_names(result) == '', self._pkg_names(result)

        # token
        result = Search().search(u'title:Opengov.se')
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

    def test_tags_token_simple_with_deleted_tag(self):
        # registry has been deleted
        result = Search().search(u'tags:registry')
        assert self._pkg_names(result) == '', self._pkg_names(result)

    def test_tags_token_multiple(self):
        result = Search().search(u'tags:country-sweden tags:format-pdf')
        assert self._pkg_names(result) == 'se-publications', self._pkg_names(result)

    def test_tags_token_complicated(self):
        result = Search().search(u'tags:country-sweden tags:somethingrandom')
        assert self._pkg_names(result) == '', self._pkg_names(result)

    def test_tags_token_blank(self):
        options = SearchOptions({'q':u'tags: wildlife'})
        result = Search().run(options)
        assert self._pkg_names(result) == 'us-gov-images', self._pkg_names(result)

    def test_tag_basic(self):
        options = SearchOptions({'q':u'gov',
                                 'entity':'tag'})
        result = Search().run(options)
        assert result['count'] == 2, result
        assert self._check_pkg_names(result, ('gov', 'government')), self._pkg_names(result)

    def test_tag_basic_2(self):
        options = SearchOptions({'q':u'wildlife',
                                 'entity':'tag'})
        result = Search().run(options)
        assert self._pkg_names(result) == 'wildlife', self._pkg_names(result)

    def test_tag_with_tags_option(self):
        options = SearchOptions({'q':u'tags:wildlife',
                                 'entity':'tag'})
        result = Search().run(options)
        assert self._pkg_names(result) == 'wildlife', self._pkg_names(result)

    def test_tag_with_blank_tags(self):
        options = SearchOptions({'q':u'tags: wildlife',
                                 'entity':'tag'})
        result = Search().run(options)
        assert self._pkg_names(result) == 'wildlife', self._pkg_names(result)

    def test_pagination(self):
        # large search
        all_results = Search().search(self.q_all)
        all_pkgs = all_results['results']
        all_pkg_count = all_results['count']

        # limit
        options = SearchOptions({'q':self.q_all})
        options.limit = 2
        result = Search().run(options)
        pkgs = result['results']
        count = result['count']
        assert len(pkgs) == 2, pkgs
        assert count == all_pkg_count
        assert pkgs == all_pkgs[:2]

        # offset
        options = SearchOptions({'q':self.q_all})
        options.limit = 2
        options.offset = 2
        results = Search().run(options)
        pkgs = results['results']
        assert len(pkgs) == 2, pkgs
        assert pkgs == all_pkgs[2:4]

        # larger offset
        options = SearchOptions({'q':self.q_all})
        options.limit = 2
        options.offset = 4
        result = Search().run(options)
        pkgs = result['results']
        assert len(pkgs) == 2, pkgs
        assert pkgs == all_pkgs[4:6]

    def test_order_by(self):
        # large search
        all_results = Search().search(self.q_all)
        all_pkgs = all_results['results']
        all_pkg_count = all_results['count']

        # rank
        options = SearchOptions({'q':u'penguin'})
        options.order_by = 'rank'
        result = Search().run(options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        assert fields[0] == 'usa-courts-gov', fields # has penguin three times
        assert pkgs == all_pkgs, pkgs #default ordering        

        # name
        options = SearchOptions({'q':self.q_all})
        options.order_by = 'name'
        result = Search().run(options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        sorted_fields = fields; sorted_fields.sort()
        assert fields == sorted_fields, repr(fields) + repr(sorted_fields)

        # title
        options = SearchOptions({'q':self.q_all})
        options.order_by = 'title'
        result = Search().run(options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).title for pkg_name in pkgs]
        sorted_fields = fields; sorted_fields.sort()
        assert fields == sorted_fields, repr(fields) + repr(sorted_fields)

        # notes
        options = SearchOptions({'q':self.q_all})
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

    # TODO: 2009-09-23 re-enable this and get this functionality working
    def _test_search_notes_on(self):
        options = SearchOptions({'q':u'restrictions'})
        options.search_notes = True
        result = Search().run(options)
        pkgs = result['results']
        count = result['count']
        assert len(pkgs) == 2, pkgs
        # TODO fix this
        
    def test_groups(self):
        result = Search().search(u'groups:random')
        assert self._pkg_names(result) == '', self._pkg_names(result)

        result = Search().search(u'groups:ukgov')
        assert result['count'] == 4, self._pkg_names(result)

        result = Search().search(u'groups:ukgov tags:us')
        assert result['count'] == 2, self._pkg_names(result)

class TestSearchOverall(object):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()

    def _check_search_results(self, terms, expected_count, expected_packages=[], only_open=False, only_downloadable=False):
        options = SearchOptions({'q':unicode(terms)})
        options.filter_by_openness = only_open
        options.filter_by_downloadable = only_downloadable
        result = Search().run(options)
        pkgs = result['results']
        count = result['count']
        assert count == expected_count, count
        for expected_pkg in expected_packages:
            assert expected_pkg in pkgs, '%s : %s' % (expected_pkg, result)

    def test_overall(self):
        self._check_search_results('annakarenina', 1, ['annakarenina'] )
        self._check_search_results('warandpeace', 1, ['warandpeace'] )
        self._check_search_results('', 0 )
        self._check_search_results('A Novel By Tolstoy', 1, ['annakarenina'] )
        self._check_search_results('title:Novel', 1, ['annakarenina'] )
        self._check_search_results('title:peace', 0 )
        self._check_search_results('name:warandpeace', 1 )
        self._check_search_results('groups:david', 2 )
        self._check_search_results('groups:roger', 1 )
        self._check_search_results('groups:lenny', 0 )
        self._check_search_results('annakarenina', 1, ['annakarenina'], True, False )
        self._check_search_results('annakarenina', 1, ['annakarenina'], False, True )
        self._check_search_results('annakarenina', 1, ['annakarenina'], True, True )
        

class TestRank(object):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        self.data = [(u'test1-penguin-canary', u'canary goose squirrel wombat wombat'),
                     (u'test2-squirrel-squirrel-canary-goose', u'penguin wombat'),
                     ]
        self.pkgs = []
        model.repo.new_revision()
        for name, notes in self.data:
            model.Package(name=name, notes=notes)
            self.pkgs.append(name)
        model.repo.commit_and_remove()

    @classmethod
    def teardown_class(self):
        # CreateTestData.delete()
        model.Session.remove()
        model.repo.rebuild_db()
        model.Session.remove()
    
    def _do_search(self, q, results):
        options = SearchOptions({'q':q})
        options.order_by = 'rank'
        result = Search().run(options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        assert fields[0] == results[0], fields
        assert fields[1] == results[1], fields

    def test_0_basic(self):
        self._do_search(u'wombat', self.pkgs)
        self._do_search(u'squirrel', self.pkgs[::-1])
        self._do_search(u'canary', self.pkgs)

    def test_1_weighting(self):
        self._do_search(u'penguin', self.pkgs)
        self._do_search(u'goose', self.pkgs[::-1])

class PostgresSearch(object):
    def filter_by(self, query, terms):
        q = query
        q = q.filter(model.package_search_table.c.package_id==model.Package.id)
        q = q.filter('package_search.search_vector '\
                                       '@@ plainto_tsquery(:terms)')
        q = q.params(terms=terms)
        q = q.add_column(sa.func.ts_rank_cd('package_search.search_vector', sa.func.plainto_tsquery(terms)))
        return q

    def order_by(self, query):
        return query.order_by('ts_rank_cd_1')
        
    def search(self, terms):
        import ckan.model as model
        q = self.filter_by(model.Package.query, terms)
        q = self.order_by(q)
        q = q.distinct()
        results = [pkg_tuple[0].name for pkg_tuple in q.all()]
        return {'results':results, 'count':q.count()}

class TestPostgresSearch(object):

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

    def test_0_indexing(self):
        searches = model.metadata.bind.execute('SELECT package_id, search_vector FROM package_search').fetchall()
        print searches
        assert searches[0][1], searches
        q = model.Package.query.filter(model.package_search_table.c.package_id==model.Package.id)
        assert q.count() == 6, q.count()
        
    def test_1_basic(self):
        result = PostgresSearch().search(u'sweden')
        print result
        assert 'se-publications' in result['results'], result['results']
        assert result['count'] == 2, result['count']

