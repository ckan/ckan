import time

import sqlalchemy as sa

from ckan.tests import *
from ckan import model
import ckan.lib.search as search

class TestSearchIndex(TestController):
    '''Tests that a package is indexed when the packagenotification is
    received by the indexer.'''
    worker = None
    
    @classmethod
    def setup_class(cls):
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        CreateTestData.delete()        

    def test_index(self):
        search.dispatch_by_operation('Package', {'title': 'penguin'}, 'new', 
            backend=search.get_backend(backend='sql'))

        sql = "select search_vector from package_search where package_id='%s'" % self.anna.id
        vector = model.Session.execute(sql).fetchone()[0]
        assert 'annakarenina' in vector, vector
        assert not 'penguin' in vector, vector


class PostgresSearch(object):
    '''Demo of how postgres search works.'''
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
        q = self.filter_by(model.Session.query(model.Package), terms)
        q = self.order_by(q)
        q = q.distinct()
        results = [pkg_tuple[0].name for pkg_tuple in q.all()]
        return {'results':results, 'count':q.count()}


def allow_time_to_create_search_index():
    time.sleep(0.5)

class TestPostgresSearch:
    @classmethod
    def setup_class(self):
        tsi = TestSearchIndexer()
        CreateTestData.create_search_test_data()
        tsi.index()

        self.gils = model.Package.by_name(u'gils')
        self.war = model.Package.by_name(u'warandpeace')
        self.russian = model.Tag.by_name(u'russian')
        self.tolstoy = model.Tag.by_name(u'tolstoy')

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()

    def test_0_indexing(self):
        searches = model.metadata.bind.execute('SELECT package_id, search_vector FROM package_search').fetchall()
        assert searches[0][1], searches
        q = model.Session.query(model.Package).filter(model.package_search_table.c.package_id==model.Package.id)
        assert q.count() == 6, q.count()
        
    def test_1_basic(self):
        result = PostgresSearch().search(u'sweden')
        assert 'se-publications' in result['results'], result['results']
        assert result['count'] == 2, result['count']

