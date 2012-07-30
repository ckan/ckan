import json
import sqlalchemy
import ckan.plugins as p
import ckan.lib.create_test_data as ctd
import ckan.model as model
import ckan.tests as tests
import ckanext.datastore.db as db


class TestDatastoreCreate(tests.WsgiAppCase):
    sysadmin_user = None
    normal_user = None

    @classmethod
    def setup_class(cls):
        p.load('datastore')
        ctd.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_create_requires_auth(self):
        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id
        }
        postparams = '%s=1' % json.dumps(data)
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            status=403)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_create_empty_fails(self):
        postparams = '%s=1' % json.dumps({})
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_create_invalid_field_type(self):
        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'book', 'type': 'INVALID'},
                       {'id': 'author', 'type': 'INVALID'}]
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_create_invalid_field_name(self):
        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id,
            'fields': [{'id': '_book', 'type': 'text'},
                       {'id': '_author', 'type': 'text'}]
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

        data = {
            'resource_id': resource.id,
            'fields': [{'id': '"book"', 'type': 'text'},
                       {'id': '"author', 'type': 'text'}]
        }
        postparams = '%s=1' % json.dumps(data)
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_create_invalid_record_field(self):
        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [{'book': 'annakarenina', 'author': 'tolstoy'},
                        {'book': 'warandpeace', 'published': '1869'}]
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False

    def test_bad_records(self):
        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': ['bad'] # treat author as null
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is False

        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [{'book': 'annakarenina', 'author': 'tolstoy'},
                        [],
                        {'book': 'warandpeace'}]  # treat author as null
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is False

    def test_create_basic(self):
        resource = model.Package.get('annakarenina').resources[0]
        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [{'book': 'annakarenina', 'author': 'tolstoy'},
                        {'book': 'crime', 'author': ['tolstoy', 'dostoevsky']},
                        {'book': 'warandpeace'}]  # treat author as null
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True
        assert res_dict['result']['resource_id'] == data['resource_id']
        assert res_dict['result']['fields'] == data['fields']
        assert res_dict['result']['records'] == data['records']

        c = model.Session.connection()
        results = c.execute('select * from "{0}"'.format(resource.id))

        assert results.rowcount == 3
        for i, row in enumerate(results):
            assert data['records'][i].get('book') == row['book']
            assert (data['records'][i].get('author') == row['author']
                    or data['records'][i].get('author') == json.loads(row['author']))

        results = c.execute('''select * from "{0}" where _full_text @@ 'warandpeace' '''.format(resource.id))
        assert results.rowcount == 1

        results = c.execute('''select * from "{0}" where _full_text @@ 'tolstoy' '''.format(resource.id))
        assert results.rowcount == 2
        model.Session.remove()

        #######  insert again simple
        data2 = {
            'resource_id': resource.id,
            'records': [{'book': 'hagji murat', 'author': 'tolstoy'}]
        }

        postparams = '%s=1' % json.dumps(data2)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

        c = model.Session.connection()
        results = c.execute('select * from "{0}"'.format(resource.id))

        assert results.rowcount == 4

        all_data = data['records'] + data2['records']
        for i, row in enumerate(results):
            assert all_data[i].get('book') == row['book']
            assert (all_data[i].get('author') == row['author']
                    or all_data[i].get('author') == json.loads(row['author']))

        results = c.execute('''select * from "{0}" where _full_text @@ 'tolstoy' '''.format(resource.id))
        assert results.rowcount == 3
        model.Session.remove()

        #######  insert again extra field
        data3 = {
            'resource_id': resource.id,
            'records': [{'book': 'crime and punsihment',
                         'author': 'dostoevsky', 'rating': 'good'}]
        }

        postparams = '%s=1' % json.dumps(data3)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is True

        c = model.Session.connection()
        results = c.execute('select * from "{0}"'.format(resource.id))

        assert results.rowcount == 5

        all_data = data['records'] + data2['records'] + data3['records']
        print all_data
        for i, row in enumerate(results):
            assert all_data[i].get('book') == row['book'], (i, all_data[i].get('book'), row['book'])
            assert (all_data[i].get('author') == row['author']
                    or all_data[i].get('author') == json.loads(row['author']))

        results = c.execute('''select * from "{0}" where _full_text @@ 'dostoevsky' '''.format(resource.id))
        assert results.rowcount == 2
        model.Session.remove()

    def test_guess_types(self):
        resource = model.Package.get('annakarenina').resources[1]
        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'author', 'type': 'text'},
                       {'id': 'count'},
                       {'id': 'book'},
                       {'id': 'date'}],
            'records': [{'book': 'annakarenina', 'author': 'tolstoy',
                         'count': 1, 'date': '2005-12-01', 'count2': 2},
                        {'book': 'crime', 'author': ['tolstoy', 'dostoevsky']},
                        {'book': 'warandpeace'}]  # treat author as null
        }
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        c = model.Session.connection()
        results = c.execute('''select * from "{0}" '''.format(resource.id))

        types = [db._pg_types[field[1]] for field in results.cursor.description]

        assert types == [u'int4', u'tsvector', u'text', u'int4',
                         u'text', u'timestamp', u'int4'], types

        assert results.rowcount == 3
        for i, row in enumerate(results):
            assert data['records'][i].get('book') == row['book']
            assert (data['records'][i].get('author') == row['author']
                    or data['records'][i].get('author') == json.loads(row['author']))
        model.Session.remove()

        ### extend types

        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'author', 'type': 'text'},
                       {'id': 'count'},
                       {'id': 'book'},
                       {'id': 'date'},
                       {'id': 'count2'},
                       {'id': 'extra', 'type':'text'},
                       {'id': 'date2'},
                      ],
            'records': [{'book': 'annakarenina', 'author': 'tolstoy',
                         'count': 1, 'date': '2005-12-01', 'count2': 2,
                         'count3': 432, 'date2': '2005-12-01'}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)

        c = model.Session.connection()
        results = c.execute('''select * from "{0}" '''.format(resource.id))

        types = [db._pg_types[field[1]] for field in results.cursor.description]

        assert types == [u'int4',  # id
                         u'tsvector',  # fulltext
                         u'text',  # author
                         u'int4',  # count
                         u'text',  # book
                         u'timestamp',  # date
                         u'int4',  # count2
                         u'text',  # extra
                         u'timestamp',  # date2
                         u'int4',  # count3
                        ], types

        ### fields resupplied in wrong order

        data = {
            'resource_id': resource.id,
            'fields': [{'id': 'author', 'type': 'text'},
                       {'id': 'count'},
                       {'id': 'date'},  # date and book in wrong order
                       {'id': 'book'},
                       {'id': 'count2'},
                       {'id': 'extra', 'type':'text'},
                       {'id': 'date2'},
                      ],
            'records': [{'book': 'annakarenina', 'author': 'tolstoy',
                         'count': 1, 'date': '2005-12-01', 'count2': 2,
                         'count3': 432, 'date2': '2005-12-01'}]
        }

        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth, status=409)
        res_dict = json.loads(res.body)

        assert res_dict['success'] is False


class TestDatastoreDelete(tests.WsgiAppCase):
    sysadmin_user = None
    normal_user = None

    @classmethod
    def setup_class(cls):
        p.load('datastore')
        ctd.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')
        resource = model.Package.get('annakarenina').resources[0]
        cls.data = {
            'resource_id': resource.id,
            'fields': [{'id': 'book', 'type': 'text'},
                       {'id': 'author', 'type': 'text'}],
            'records': [{'book': 'annakarenina', 'author': 'tolstoy'},
                        {'book': 'crime', 'author': ['tolstoy', 'dostoevsky']}]
        }

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def _create(self):
        postparams = '%s=1' % json.dumps(self.data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_create', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True

    def test_delete_basic(self):
        self._create()
        id = self.data['resource_id']
        data = {'resource_id': id}
        postparams = '%s=1' % json.dumps(data)
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_delete', params=postparams,
                            extra_environ=auth)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is True
        assert res_dict['result'] == data

        c = model.Session.connection()

        try:
            # check that data was actually deleted: this should raise a
            # ProgrammingError as the table should not exist any more
            c.execute('select * from "{0}";'.format(id))
            raise Exception("Data not deleted")
        except sqlalchemy.exc.ProgrammingError as e:
            expected_msg = 'relation "{}" does not exist'.format(id)
            assert expected_msg in str(e)

        model.Session.remove()

    def test_delete_invalid_resource_id(self):
        postparams = '%s=1' % json.dumps({'resource_id': 'bad'})
        auth = {'Authorization': str(self.sysadmin_user.apikey)}
        res = self.app.post('/api/action/datastore_delete', params=postparams,
                            extra_environ=auth, status=404)
        res_dict = json.loads(res.body)
        assert res_dict['success'] is False
