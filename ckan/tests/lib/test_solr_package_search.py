from pylons import config
from ckan.tests import TestController, CreateTestData
from ckan import model
import ckan.lib.search as search


class TestSearch(TestController):
    # 'penguin' is in all test search packages
    q_all = u'penguin'

    @classmethod
    def setup_class(cls):
        model.Session.remove()
        CreateTestData.create_search_test_data()
        # now remove a tag so we can test search with deleted tags
        model.repo.new_revision()
        gils = model.Package.by_name(u'gils')
        # an existing tag used only by gils
        cls.tagname = u'registry'
        idx = [t.name for t in gils.tags].index(cls.tagname)
        del gils.tags[idx]
        model.repo.commit_and_remove()
        # solr
        config['search_backend'] = 'solr'
        search.rebuild()
        cls.backend = search.get_backend()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        search.get_backend().index_for('Package').clear()

    def _pkg_names(self, result):
        return ' '.join(result['results'])

    def _check_entity_names(self, result, names_in_result):
        names = result['results']
        for name in names_in_result:
            if name not in names:
                return False
        return True

    def test_1_all_records(self):
        result = self.backend.query_for(model.Package).run(query=self.q_all)
        assert 'gils' in result['results'], result['results']
        assert result['count'] == 6, result['count']

    def test_1_name(self):
        # exact name
        result = self.backend.query_for(model.Package).run(query=u'gils')
        assert result['count'] == 1, result
        assert self._pkg_names(result) == 'gils', result

    def test_1_name_multiple_results(self):
        result = self.backend.query_for(model.Package).run(query=u'gov')
        assert self._check_entity_names(result, ('us-gov-images', 'usa-courts-gov')), self._pkg_names(result)
        assert result['count'] == 4, self._pkg_names(result)

    def test_1_name_token(self):
        result = self.backend.query_for(model.Package).run(query=u'name:gils')
        assert self._pkg_names(result) == 'gils', self._pkg_names(result)
        result = self.backend.query_for(model.Package).run(query=u'title:gils')
        assert not self._check_entity_names(result, ('gils')), self._pkg_names(result)

    def test_2_title(self):
        # exact title, one word
        result = self.backend.query_for(model.Package).run(query=u'Opengov.se')
        assert self._pkg_names(result) == 'se-opengov', self._pkg_names(result)
        # multiple words
        result = self.backend.query_for(model.Package).run(query=u'Government Expenditure')
        assert self._pkg_names(result) == 'uk-government-expenditure', self._pkg_names(result)
        # multiple words wrong order
        result = self.backend.query_for(model.Package).run(query=u'Expenditure Government')
        assert self._pkg_names(result) == 'uk-government-expenditure', self._pkg_names(result)
        # multiple words, one doesn't match
        result = self.backend.query_for(model.Package).run(query=u'Expenditure Government China')
        assert len(result['results']) == 0, self._pkg_names(result)

    def test_3_licence(self):
        # this should result, but it is here to check that at least it does not error
        result = self.backend.query_for(model.Package).run(query=u'license:"OKD::Other (PublicsDomain)"')
        assert result['count'] == 0, result

    def test_quotation(self):
        # multiple words quoted
        result = self.backend.query_for(model.Package).run(query=u'"Government Expenditure"')
        assert self._pkg_names(result) == 'uk-government-expenditure', self._pkg_names(result)
        # multiple words quoted wrong order
        result = self.backend.query_for(model.Package).run(query=u'"Expenditure Government"')
        assert self._pkg_names(result) == '', self._pkg_names(result)

    def test_string_not_found(self):
        result = self.backend.query_for(model.Package).run(query=u'randomthing')
        assert self._pkg_names(result) == '', self._pkg_names(result)

    def test_tags_field(self):
        result = self.backend.query_for(model.Package).run(query=u'country-sweden')
        assert self._check_entity_names(result, ['se-publications', 'se-opengov']), self._pkg_names(result)

    def test_tags_token_simple(self):
        result = self.backend.query_for(model.Package).run(query=u'tags:country-sweden')
        assert self._check_entity_names(result, ['se-publications', 'se-opengov']), self._pkg_names(result)
        result = self.backend.query_for(model.Package).run(query=u'tags:wildlife')
        assert self._pkg_names(result) == 'us-gov-images', self._pkg_names(result)

    def test_tags_token_simple_with_deleted_tag(self):
        # registry has been deleted
        result = self.backend.query_for(model.Package).run(query=u'tags:registry')
        assert self._pkg_names(result) == '', self._pkg_names(result)

    def test_tags_token_multiple(self):
        result = self.backend.query_for(model.Package).run(query=u'tags:country-sweden tags:format-pdf')
        assert self._pkg_names(result) == 'se-publications', self._pkg_names(result)

    def test_tags_token_complicated(self):
        result = self.backend.query_for(model.Package).run(query=u'tags:country-sweden tags:somethingrandom')
        assert self._pkg_names(result) == '', self._pkg_names(result)

    def test_pagination(self):
        # large search
        all_results = self.backend.query_for(model.Package).run(query=self.q_all)
        all_pkgs = all_results['results']
        all_pkg_count = all_results['count']

        # limit
        options = search.QueryOptions()
        options.limit = 2
        result = self.backend.query_for(model.Package).run(query=self.q_all, options=options)
        pkgs = result['results']
        count = result['count']
        assert len(pkgs) == 2, pkgs
        assert count == all_pkg_count
        assert pkgs == all_pkgs[:2]

        # offset
        options = search.QueryOptions()
        options.limit = 2
        options.offset = 2
        result = self.backend.query_for(model.Package).run(query=self.q_all, options=options)
        pkgs = result['results']
        assert len(pkgs) == 2, pkgs
        assert pkgs == all_pkgs[2:4]

        # larger offset
        options = search.QueryOptions()
        options.limit = 2
        options.offset = 4
        result = self.backend.query_for(model.Package).run(query=self.q_all, options=options)
        pkgs = result['results']
        assert len(pkgs) == 2, pkgs
        assert pkgs == all_pkgs[4:6]

    def test_order_by(self):
        # large search
        all_results = self.backend.query_for(model.Package).run(query=self.q_all)
        all_pkgs = all_results['results']
        all_pkg_count = all_results['count']

        # rank
        # TODO: fix this test
        # options = search.QueryOptions()
        # options.order_by = 'rank'
        # result = self.backend.query_for(model.Package).run(query='penguin', options=options)
        # pkgs = result['results']
        # fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        # assert fields[0] == 'usa-courts-gov', fields # has penguin three times
        # assert pkgs == all_pkgs, pkgs #default ordering        

        # name
        options = search.QueryOptions()
        options.order_by = 'name'
        result = self.backend.query_for(model.Package).run(query=self.q_all, options=options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        sorted_fields = fields; sorted_fields.sort()
        assert fields == sorted_fields, repr(fields) + repr(sorted_fields)

        # title
        options = search.QueryOptions()
        options.order_by = 'title'
        result = self.backend.query_for(model.Package).run(query=self.q_all, options=options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).title for pkg_name in pkgs]
        sorted_fields = fields; sorted_fields.sort()
        assert fields == sorted_fields, repr(fields) + repr(sorted_fields)

        # notes
        options = search.QueryOptions()
        options.order_by = 'notes'
        result = self.backend.query_for(model.Package).run(query=self.q_all, options=options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).notes for pkg_name in pkgs]
        sorted_fields = fields; sorted_fields.sort()
        assert fields == sorted_fields, repr(fields) + repr(sorted_fields)

        # extra field
        options = search.QueryOptions()
        options.order_by = 'date_released'
        result = self.backend.query_for(model.Package).run(query=self.q_all, options=options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name) for pkg_name in pkgs]
        fields = [field.extras.get('date_released') for field in fields]
        sorted_fields = fields; sorted_fields.sort()
        assert fields == sorted_fields, repr(fields) + repr(sorted_fields)

    def test_search_notes_on(self):
        result = self.backend.query_for(model.Package).run(query=u'restrictions')
        pkgs = result['results']
        count = result['count']
        assert len(pkgs) == 2, pkgs
        
    def test_search_foreign_chars(self):
        result = self.backend.query_for(model.Package).run(query='umlaut')
        assert result['results'] == ['gils'], result['results']
        result = self.backend.query_for(model.Package).run(query=u'thumb')
        assert result['count'] == 0, result['results']
        result = self.backend.query_for(model.Package).run(query=u'th\xfcmb')
        assert result['results'] == ['gils'], result['results']

    def test_groups(self):
        result = self.backend.query_for(model.Package).run(query=u'groups:random')
        assert self._pkg_names(result) == '', self._pkg_names(result)
        result = self.backend.query_for(model.Package).run(query=u'groups:ukgov')
        assert result['count'] == 4, self._pkg_names(result)
        result = self.backend.query_for(model.Package).run(query=u'groups:ukgov tags:us')
        assert result['count'] == 2, self._pkg_names(result)

class TestSearchOverall(TestController):
    @classmethod
    def setup_class(cls):
        CreateTestData.create()
        config['search_backend'] = 'solr'
        search.rebuild()
        cls.backend = search.get_backend()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
        search.get_backend().index_for('Package').clear()

    def _check_search_results(self, terms, expected_count, expected_packages=[], only_open=False, only_downloadable=False):
        options = search.QueryOptions()
        options.filter_by_openness = only_open
        options.filter_by_downloadable = only_downloadable
        result = self.backend.query_for(model.Package).run(query=unicode(terms))
        pkgs = result['results']
        count = result['count']
        assert count == expected_count, (count, expected_count)
        for expected_pkg in expected_packages:
            assert expected_pkg in pkgs, '%s : %s' % (expected_pkg, result)

    def test_overall(self):
        print 'test_overall'
        self._check_search_results('annakarenina', 1, ['annakarenina'])
        self._check_search_results('warandpeace', 1, ['warandpeace'])
        self._check_search_results('', 2)
        self._check_search_results('A Novel By Tolstoy', 1, ['annakarenina'])
        self._check_search_results('title:Novel', 1, ['annakarenina'])
        self._check_search_results('title:peace', 0)
        self._check_search_results('name:warandpeace', 1)
        self._check_search_results('groups:david', 2)
        self._check_search_results('groups:roger', 1)
        self._check_search_results('groups:lenny', 0)
        self._check_search_results('annakarenina', 1, ['annakarenina'], True, False)
        self._check_search_results('annakarenina', 1, ['annakarenina'], False, True)
        self._check_search_results('annakarenina', 1, ['annakarenina'], True, True)
        

class TestGeographicCoverage(TestController):
    @classmethod
    def setup_class(cls):
        init_data = [
            {'name':'eng',
             'extras':{'geographic_coverage':'100000: England'},},
            {'name':'eng_ni',
             'extras':{'geographic_coverage':'100100: England, Northern Ireland'},},
            {'name':'uk',
             'extras':{'geographic_coverage':'111100: United Kingdom (England, Scotland, Wales, Northern Ireland'},},
            {'name':'gb',
             'extras':{'geographic_coverage':'111000: Great Britain (England, Scotland, Wales)'},},
            {'name':'none',
             'extras':{'geographic_coverage':'000000:'},},
        ]
        CreateTestData.create_arbitrary(init_data)
        config['search_backend'] = 'solr'
        search.rebuild()
        cls.backend = search.get_backend()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()
        search.get_backend().index_for('Package').clear()
    
    def _do_search(self, q, expected_pkgs, count=None):
        options = search.QueryOptions()
        options.order_by = 'rank'
        result = self.backend.query_for(model.Package).run(query=q, options=options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        if not (count is None):
            assert result['count'] == count, result['count']
        for expected_pkg in expected_pkgs:
            assert expected_pkg in fields, expected_pkg

    def _filtered_search(self, value, expected_pkgs, count=None):
        options = search.QueryOptions()
        options.order_by = 'rank'
        result = self.backend.query_for(model.Package).run(fields={'geographic_coverage':value}, options=options)
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        if not (count is None):
            assert result['count'] == count, result['count']
        for expected_pkg in expected_pkgs:
            assert expected_pkg in fields, expected_pkg

    def test_0_basic(self):
        self._do_search(u'england', ['eng', 'eng_ni', 'uk', 'gb'], 4)
        self._do_search(u'northern ireland', ['eng_ni', 'uk'], 2)
        self._do_search(u'united kingdom', ['uk'], 1)
        self._do_search(u'great britain', ['gb'], 1)

    # TODO: solr is not currently set up to allow partial matches 
    #       and extras are not saved as multivalued so this
    #       test will fail. Make multivalued or remove?
    # def test_1_filtered(self):
    #     self._filtered_search(u'england', ['eng', 'eng_ni', 'uk', 'gb'], 4)

class TestExtraFields(TestController):
    @classmethod
    def setup_class(cls):
        init_data = [
            {'name':'a',
             'extras':{'department':'abc',
                       'agency':'ag-a'},},
            {'name':'b',
             'extras':{'department':'bcd',
                       'agency':'ag-b'},},
            {'name':'c',
             'extras':{'department':'cde abc'},},
            {'name':'none',
             'extras':{'department':''},},
            ]
        CreateTestData.create_arbitrary(init_data)
        config['search_backend'] = 'solr'
        search.rebuild()
        cls.backend = search.get_backend()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()
        search.get_backend().index_for('Package').clear()
    
    def _do_search(self, department, expected_pkgs, count=None):
        result = self.backend.query_for(model.Package).run(fields={'department': department})
        pkgs = result['results']
        fields = [model.Package.by_name(pkg_name).name for pkg_name in pkgs]
        if not (count is None):
            assert result['count'] == count, result['count']
        for expected_pkg in expected_pkgs:
            assert expected_pkg in fields, expected_pkg

    def test_0_basic(self):
        self._do_search(u'bcd', 'b', 1)
        self._do_search(u'cde abc', 'c', 1)
        # TODO: solr is not currently set up to allow partial matches 
        #       and extras are not saved as multivalued so these
        #       tests will fail. Make multivalued or remove these?
        # self._do_search(u'abc', ['a', 'c'], 2)
        # self._do_search(u'cde', 'c', 1)
        # self._do_search(u'abc cde', 'c', 1)

class TestRank(TestController):
    @classmethod
    def setup_class(cls):
        init_data = [{'name':u'test1-penguin-canary',
                      'tags':u'canary goose squirrel wombat wombat'},
                     {'name':u'test2-squirrel-squirrel-canary-goose',
                      'tags':u'penguin wombat'},
                     ]
        CreateTestData.create_arbitrary(init_data)
        cls.pkg_names = [
            u'test1-penguin-canary',
            u'test2-squirrel-squirrel-canary-goose'
        ]
        config['search_backend'] = 'solr'
        search.rebuild()
        cls.backend = search.get_backend()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()
        search.get_backend().index_for('Package').clear()
    
    def _do_search(self, q, wanted_results):
        options = search.QueryOptions()
        options.order_by = 'rank'
        result = self.backend.query_for(model.Package).run(query=q, options=options)
        results = result['results']
        err = 'Wanted %r, got %r' % (wanted_results, results)
        assert wanted_results[0] == results[0], err
        assert wanted_results[1] == results[1], err

    def test_0_basic(self):
        self._do_search(u'wombat', self.pkg_names)
        self._do_search(u'squirrel', self.pkg_names[::-1])
        self._do_search(u'canary', self.pkg_names)

    # TODO: fix this test
    # def test_1_weighting(self):
    #     self._do_search(u'penguin', self.pkg_names)
    #     self._do_search(u'goose', self.pkg_names[::-1])
