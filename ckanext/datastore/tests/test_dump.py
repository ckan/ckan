# encoding: utf-8

import json

import nose
from nose.tools import assert_equals, assert_in
from ckan.common import config
import sqlalchemy.orm as orm
import paste.fixture

import ckan.config.middleware as middleware
import ckan.plugins as p
import ckan.lib.create_test_data as ctd
import ckan.model as model
import ckan.tests.legacy as tests
import ckanext.datastore.db as db
import ckanext.datastore.tests.helpers as helpers


class TestDatastoreDump(object):
    sysadmin_user = None
    normal_user = None

    @classmethod
    def setup_class(cls):
        wsgiapp = middleware.make_app(config['global_conf'], **config)
        cls.app = paste.fixture.TestApp(wsgiapp)
        if not tests.is_datastore_supported():
            raise nose.SkipTest("Datastore not supported")
        p.load('datastore')
        ctd.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        resource = model.Package.get('annakarenina').resources[0]
        cls.data = {
            'resource_id': resource.id,
            'force': True,
            'aliases': 'books',
            'fields': [{'id': u'b\xfck', 'type': 'text'},
                       {'id': 'author', 'type': 'text'},
                       {'id': 'published'},
                       {'id': u'characters', u'type': u'_text'},
                       {'id': 'random_letters', 'type': 'text[]'}],
            'records': [{u'b\xfck': 'annakarenina',
                         'author': 'tolstoy',
                         'published': '2005-03-01',
                         'nested': ['b', {'moo': 'moo'}],
                         u'characters': [u'Princess Anna', u'Sergius'],
                         'random_letters': ['a', 'e', 'x']},
                        {u'b\xfck': 'warandpeace', 'author': 'tolstoy',
                         'nested': {'a': 'b'}, 'random_letters': []}]
        }
        postparams = '%s=1' % json.dumps(cls.data)
        auth = {'Authorization': str(cls.sysadmin_user.apikey)}
        res = cls.app.post('/api/action/datastore_create', params=postparams,
                           extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

        engine = db._get_engine({
            'connection_url': config['ckan.datastore.write_url']})
        cls.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

    @classmethod
    def teardown_class(cls):
        helpers.rebuild_all_dbs(cls.Session)
        p.unload('datastore')

    def test_dump_basic(self):
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.get('/datastore/dump/{0}'.format(str(
            self.data['resource_id'])), extra_environ=auth)
        content = res.body.decode('utf-8')

        expected = (
            u'_id,b\xfck,author,published'
            u',characters,random_letters,nested')
        assert_equals(content[:len(expected)], expected)
        assert_in('warandpeace', content)
        assert_in('"[""Princess Anna"", ""Sergius""]"', content)

        # get with alias instead of id
        res = self.app.get('/datastore/dump/{0}'.format(str(
            self.data['aliases'])), extra_environ=auth)

    def test_dump_does_not_exist_raises_404(self):
        auth = {'Authorization': str(self.normal_user.apikey)}
        self.app.get('/datastore/dump/{0}'.format(str(
            'does-not-exist')), extra_environ=auth, status=404)

    def test_dump_limit(self):
        auth = {'Authorization': str(self.normal_user.apikey)}
        res = self.app.get('/datastore/dump/{0}?limit=1'.format(str(
            self.data['resource_id'])), extra_environ=auth)
        content = res.body.decode('utf-8')

        expected = (u'_id,b\xfck,author,published'
                    u',characters,random_letters,nested')
        assert_equals(content[:len(expected)], expected)

        expected_content = (
            u'_id,b\xfck,author,published,characters,random_letters,'
            u'nested\r\n1,annakarenina,tolstoy,2005-03-01T00:00:00,'
            u'"[""Princess Anna"", ""Sergius""]",'
            u'"[""a"", ""e"", ""x""]","[""b"", '
            u'{""moo"": ""moo""}]"\r\n')
        assert_equals(content, expected_content)
