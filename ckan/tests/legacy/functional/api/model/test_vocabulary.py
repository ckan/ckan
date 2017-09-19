# encoding: utf-8

import ckan
import pylons.test
import paste.fixture
import ckan.lib.helpers as helpers
import ckan.lib.dictization.model_dictize as model_dictize


class TestVocabulary(object):

    @classmethod
    def setup_class(self):
        self.app = paste.fixture.TestApp(pylons.test.pylonsapp)

    @classmethod
    def teardown_class(self):
        ckan.model.repo.rebuild_db()

    def setup(self):
        self.clean_vocab()
        model = ckan.model
        context = {'model': model}

        genre = model.Vocabulary("Genre")
        time_period = ckan.model.Vocabulary("Time Period")
        composers = ckan.model.Vocabulary("Composers")
        model.Session.add_all([genre, time_period, composers])

        self.genre_vocab = model_dictize.vocabulary_dictize(genre, context)
        self.timeperiod_vocab = model_dictize.vocabulary_dictize(time_period,
                context)
        self.composers_vocab = model_dictize.vocabulary_dictize(composers,
                context)
        ckan.model.Session.commit()

        self.sysadmin_user = ckan.model.User.get('admin')
        self.normal_user = ckan.model.User.get('normal')
        if not self.sysadmin_user:
            normal_user = ckan.model.User(name=u'normal', password=u'annafan')
            sysadmin_user = ckan.model.User(name=u'admin',
                    password=u'testsysadmin')
            sysadmin_user.sysadmin = True
            ckan.model.Session.add(normal_user)
            ckan.model.Session.add(sysadmin_user)
            ckan.model.Session.commit()
            self.sysadmin_user = ckan.model.User.get('admin')
            self.normal_user = ckan.model.User.get('normal')
        self.sysadmin_apikey = self.sysadmin_user.apikey

    def clean_vocab(self):
        ckan.model.Session.execute('delete from package_tag_revision')
        ckan.model.Session.execute('delete from package_tag')
        ckan.model.Session.execute('delete from tag')
        ckan.model.Session.execute('delete from vocabulary')
        ckan.model.Session.commit()

    @classmethod
    def _post(self, url, params=None, extra_environ=None):
        if params is None:
            params = {}
        param_string = helpers.json.dumps(params)
        response = self.app.post(url, params=param_string,
                extra_environ=extra_environ)
        assert not response.errors
        return response.json

    @classmethod
    def _create_vocabulary(self, vocab_name=None, user=None):
        # Create a new vocabulary.
        params = {'name': vocab_name}
        if user:
            extra_environ = {'Authorization': str(user.apikey)}
        else:
            extra_environ = None
        response = self._post('/api/action/vocabulary_create', params=params,
                extra_environ=extra_environ)

        # Check the values of the response.
        assert response['success'] is True
        assert response['result']
        created_vocab = response['result']
        assert created_vocab['name'] == vocab_name
        assert created_vocab['id']

        # Get the list of vocabularies.
        response = self._post('/api/action/vocabulary_list')
        # Check that the vocabulary we created is in the list.
        assert response['success'] is True
        assert response['result']
        assert response['result'].count(created_vocab) == 1

        # Get the created vocabulary.
        params = {'id': created_vocab['id']}
        response = self._post('/api/action/vocabulary_show', params)
        # Check that retrieving the vocab by name gives the same result.
        by_name_params = {'id': created_vocab['name']}
        assert response == self._post('/api/action/vocabulary_show',
                by_name_params)
        # Check that it matches what we created.
        assert response['success'] is True
        assert response['result'] == created_vocab

        return created_vocab

    def _update_vocabulary(self, params, user=None):
        if user:
            extra_environ = {'Authorization': str(user.apikey)}
        else:
            extra_environ = None

        original_vocab = self._post('/api/action/vocabulary_show',
                {'id': params.get('id') or params.get('name')})['result']

        response = self._post('/api/action/vocabulary_update', params=params,
                extra_environ=extra_environ)

        # Check the values of the response.
        assert response['success'] is True
        assert response['result']
        updated_vocab = response['result']
        # id should never change.
        assert updated_vocab['id'] == original_vocab['id']
        if 'id' in params:
            assert updated_vocab['id'] == params['id']
        # name should change only if given in params.
        if 'name' in params:
            assert updated_vocab['name'] == params['name']
        else:
            assert updated_vocab['name'] == original_vocab['name']
        # tags should change only if given in params.
        if 'tags' in params:
            assert sorted([tag['name'] for tag in params['tags']]) \
                    == sorted([tag['name'] for tag in updated_vocab['tags']])
        else:
            assert updated_vocab['tags'] == original_vocab['tags']

        # Get the list of vocabularies.
        response = self._post('/api/action/vocabulary_list')
        # Check that the vocabulary we created is in the list.
        assert response['success'] is True
        assert response['result']
        assert response['result'].count(updated_vocab) == 1

        # Get the created vocabulary.
        params = {'id': updated_vocab['id']}
        response = self._post('/api/action/vocabulary_show', params)
        # Check that retrieving the vocab by name gives the same result.
        by_name_params = {'id': updated_vocab['name']}
        assert response == self._post('/api/action/vocabulary_show',
                by_name_params)
        # Check that it matches what we created.
        assert response['success'] is True
        assert response['result'] == updated_vocab

        return updated_vocab

    def _delete_vocabulary(self, vocab_id, user=None):
        if user:
            extra_environ = {'Authorization': str(user.apikey)}
        else:
            extra_environ = None
        params = {'id': vocab_id}
        response = self._post('/api/action/vocabulary_delete', params=params,
                extra_environ=extra_environ)

        # Check the values of the response.
        assert response['success'] is True
        assert response['result'] is None
        response['result']

        # Get the list of vocabularies.
        response = self._post('/api/action/vocabulary_list')
        assert response['success'] is True
        assert response['result']
        # Check that the vocabulary we deleted is not in the list.
        assert vocab_id not in [vocab['id'] for vocab in response['result']]

        # Check that the deleted vocabulary can no longer be retrieved.
        response = self.app.post('/api/action/vocabulary_show',
                params=helpers.json.dumps(params),
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=404)
        assert response.json['success'] is False

    def _list_tags(self, vocabulary=None, user=None):
        params = {}
        if vocabulary:
            params['vocabulary_id'] = vocabulary['id']
        if user:
            extra_environ = {'Authorization': str(user.apikey)}
        else:
            extra_environ = None
        response = self._post('/api/action/tag_list', params=params,
                extra_environ=extra_environ)
        assert response['success'] is True
        return response['result']

    def _create_tag(self, user, tag_name, vocabulary=None):
        tag_dict = {'name': tag_name}
        if vocabulary:
            tag_dict['vocabulary_id'] = vocabulary['id']
        if user:
            extra_environ = {'Authorization': str(user.apikey)}
        else:
            extra_environ = None
        response = self._post('/api/action/tag_create', params=tag_dict,
                extra_environ=extra_environ)
        assert response['success'] is True
        return response['result']

    def _delete_tag(self, user, tag_id_or_name, vocab_id_or_name=None):
        params = {'id': tag_id_or_name}
        if vocab_id_or_name:
            params['vocabulary_id'] = vocab_id_or_name
        if user:
            extra_environ = {'Authorization': str(user.apikey)}
        else:
            extra_environ = None
        response = self._post('/api/action/tag_delete', params=params,
                extra_environ=extra_environ)
        assert response['success'] is True
        return response['result']

    def test_vocabulary_create(self):
        '''Test adding a new vocabulary to a CKAN instance via the action
        API.

        '''
        self._create_vocabulary(vocab_name="My cool vocab",
                user=self.sysadmin_user)

    def test_vocabulary_create_with_tags(self):
        '''Test adding a new vocabulary with some tags.

        '''
        params = {'name': 'foobar'}
        tag1 = {'name': 'foo'}
        tag2 = {'name': 'bar'}
        params['tags'] = [tag1, tag2]
        response = self._post('/api/action/vocabulary_create',
                params=params,
                extra_environ={'Authorization': str(self.sysadmin_apikey)})
        assert response['success'] is True
        assert response['result']
        created_vocab = response['result']
        assert created_vocab['name'] == 'foobar'
        assert created_vocab['id']

        # Get the list of vocabularies.
        response = self._post('/api/action/vocabulary_list')
        # Check that the vocabulary we created is in the list.
        assert response['success'] is True
        assert response['result']
        assert response['result'].count(created_vocab) == 1

        # Get the created vocabulary.
        params = {'id': created_vocab['id']}
        response = self._post('/api/action/vocabulary_show', params)
        # Check that retrieving the vocab by name gives the same result.
        by_name_params = {'id': created_vocab['name']}
        assert response == self._post('/api/action/vocabulary_show',
                by_name_params)
        # Check that it matches what we created.
        assert response['success'] is True
        assert response['result'] == created_vocab

        # Get the list of tags for the vocabulary.
        tags = self._list_tags(created_vocab)
        assert len(tags) == 2
        assert tags.count('foo') == 1
        assert tags.count('bar') == 1

    def test_vocabulary_create_bad_tags(self):
        '''Test creating new vocabularies with invalid tags.

        '''
        for tags in (
                [{'id': 'xxx'}, {'name': 'foo'}],
                [{'name': 'foo'}, {'name': None}],
                [{'name': 'foo'}, {'name': ''}],
                [{'name': 'foo'}, {'name': 'f'}],
                [{'name': 'f' * 200}, {'name': 'foo'}],
                [{'name': 'Invalid!'}, {'name': 'foo'}],
                ):
            params = {'name': 'foobar', 'tags': tags}
            response = self.app.post('/api/action/vocabulary_create',
                    params=helpers.json.dumps(params),
                    extra_environ={'Authorization': str(self.sysadmin_apikey)},
                    status=409)
            assert response.json['success'] is False
            assert 'tags' in response.json['error']
            assert len(response.json['error']) == 2

    def test_vocabulary_create_none_tags(self):
        '''Test creating new vocabularies with None for 'tags'.

        '''
        params = {'name': 'foobar', 'tags': None}
        response = self.app.post('/api/action/vocabulary_create',
                params=helpers.json.dumps(params),
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=400)
        assert "Integrity Error" in response.body

    def test_vocabulary_create_empty_tags(self):
        '''Test creating new vocabularies with [] for 'tags'.

        '''
        params = {'name': 'foobar', 'tags': []}
        response = self.app.post('/api/action/vocabulary_create',
                params=helpers.json.dumps(params),
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=200)
        assert response.json['success'] is True
        assert response.json['result']
        created_vocab = response.json['result']
        assert created_vocab['name'] == 'foobar'
        assert created_vocab['id']
        assert created_vocab['tags'] == []
        params = {'id': created_vocab['id']}
        response = self._post('/api/action/vocabulary_show', params)
        assert response['success'] is True
        assert response['result'] == created_vocab
        tags = self._list_tags(created_vocab)
        assert tags == []

    def test_vocabulary_create_id(self):
        '''Test error response when user tries to supply their own ID when
        creating a vocabulary.

        '''
        params = {'id': 'xxx', 'name': 'foobar'}
        param_string = helpers.json.dumps(params)
        response = self.app.post('/api/action/vocabulary_create',
                params=param_string,
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=409)
        assert response.json['success'] is False
        assert response.json['error']['id'] == [u'The input field id was '
            'not expected.']

    def test_vocabulary_create_no_name(self):
        '''Test error response when user tries to create a vocab without a
        name.

        '''
        params = {}
        param_string = helpers.json.dumps(params)
        response = self.app.post('/api/action/vocabulary_create',
                params=param_string,
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=409)
        assert response.json['success'] is False
        assert response.json['error']['name'] == [u'Missing value']

    def test_vocabulary_create_invalid_name(self):
        '''Test error response when user tries to create a vocab with an
        invalid name.

        '''
        for name in (None, '', 'a', 'foobar' * 100):
            params = {'name': name}
            param_string = helpers.json.dumps(params)
            response = self.app.post('/api/action/vocabulary_create',
                    params=param_string,
                    extra_environ={'Authorization':
                        str(self.sysadmin_apikey)},
                    status=409)
            assert response.json['success'] is False
            assert response.json['error']['name']

    def test_vocabulary_create_exists(self):
        '''Test error response when user tries to create a vocab that already
        exists.

        '''
        params = {'name': self.genre_vocab['name']}
        param_string = helpers.json.dumps(params)
        response = self.app.post('/api/action/vocabulary_create',
                params=param_string,
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=409)
        assert response.json['success'] is False
        assert response.json['error']['name'] == [u'That vocabulary name is '
            'already in use.']

    def test_vocabulary_create_not_logged_in(self):
        '''Test that users who are not logged in cannot create vocabularies.'''

        params = {'name':
            "Spam Vocabulary: SpamCo Duck Rental: Rent Your Ducks From Us!"}
        param_string = helpers.json.dumps(params)
        response = self.app.post('/api/action/vocabulary_create',
                params=param_string,
                status=403)
        assert response.json['success'] is False
        assert response.json['error']['__type'] == 'Authorization Error'

    def test_vocabulary_create_not_authorized(self):
        '''Test that users who are not authorized cannot create vocabs.'''

        params = {'name': 'My Unauthorised Vocabulary'}
        param_string = helpers.json.dumps(params)
        response = self.app.post('/api/action/vocabulary_create',
                params=param_string,
                extra_environ={'Authorization':
                    str(self.normal_user.apikey)},
                status=403)
        assert response.json['success'] is False
        assert response.json['error']['__type'] == 'Authorization Error'

    def test_vocabulary_update_id_only(self):
        self._update_vocabulary({'id': self.genre_vocab['id']},
                self.sysadmin_user)

    def test_vocabulary_update_id_and_same_name(self):
        self._update_vocabulary({'id': self.genre_vocab['id'],
            'name': self.genre_vocab['name']}, self.sysadmin_user)

    def test_vocabulary_update_id_and_new_name(self):
        self._update_vocabulary({'id': self.genre_vocab['id'],
            'name': 'new name'}, self.sysadmin_user)

    def test_vocabulary_update_id_and_same_tags(self):
        self._update_vocabulary({'id': self.genre_vocab['id'],
            'tags': self.genre_vocab['tags']}, self.sysadmin_user)

    def test_vocabulary_update_id_and_new_tags(self):
        tags = [
                {'name': 'new test tag one'},
                {'name': 'new test tag two'},
                {'name': 'new test tag three'},
                ]
        self._update_vocabulary({'id': self.genre_vocab['id'], 'tags': tags},
                self.sysadmin_user)

    def test_vocabulary_update_id_same_name_and_same_tags(self):
        self._update_vocabulary({'id': self.genre_vocab['id'],
            'name': self.genre_vocab['name'],
            'tags': self.genre_vocab['tags']}, self.sysadmin_user)

    def test_vocabulary_update_id_same_name_and_new_tags(self):
        tags = [
                {'name': 'new test tag one'},
                {'name': 'new test tag two'},
                {'name': 'new test tag three'},
                ]
        self._update_vocabulary({'id': self.genre_vocab['id'],
            'name': self.genre_vocab['name'],
            'tags': tags}, self.sysadmin_user)

    def test_vocabulary_update_id_new_name_and_same_tags(self):
        self._update_vocabulary({'id': self.genre_vocab['id'],
            'name': 'new name',
            'tags': self.genre_vocab['tags']}, self.sysadmin_user)

    def test_vocabulary_update_not_exists(self):
        '''Test the error response given when a user tries to update a
        vocabulary that doesn't exist.

        '''
        params = {'id': 'xxxxxxx', 'name': 'updated_name'}
        param_string = helpers.json.dumps(params)
        response = self.app.post('/api/action/vocabulary_update',
                params=param_string,
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=404)
        assert response.json['success'] is False
        assert response.json['error']['message'].startswith('Not found: ')

    def test_vocabulary_update_no_id(self):
        params = {'name': 'bagel radio'}
        param_string = helpers.json.dumps(params)
        response = self.app.post('/api/action/vocabulary_update',
                params=param_string,
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=409)
        assert response.json['success'] is False
        assert 'id' in response.json['error']
        assert response.json['error']['id'] == 'id not in data'

    def test_vocabulary_update_not_logged_in(self):
        '''Test that users who are not logged in cannot update vocabularies.'''
        params = {'id': self.genre_vocab['id']}
        param_string = helpers.json.dumps(params)
        response = self.app.post('/api/action/vocabulary_update',
                params=param_string,
                status=403)
        assert response.json['success'] is False
        assert response.json['error']['__type'] == 'Authorization Error'

    def test_vocabulary_update_with_tags(self):
        tags = [
                {'name': 'drone'},
                {'name': 'noise'},
                {'name': 'fuzz'},
                {'name': 'field recordings'},
                {'name': 'hypnagogia'},
                {'name': 'textures without rhythm'},
                ]
        self._update_vocabulary(
                {
                    'id': self.genre_vocab['id'],
                    'name': self.genre_vocab['name'],
                    'tags': tags
                },
                self.sysadmin_user)

        params = {'id': self.genre_vocab['id']}
        response = self._post('/api/action/vocabulary_show', params)
        # Check that retrieving the vocab by name gives the same result.
        assert len(response['result']['tags']) == len(tags)

    def test_vocabulary_update_not_authorized(self):
        '''Test that users who are not authorized cannot update vocabs.'''
        params = {'id': self.genre_vocab['id']}
        param_string = helpers.json.dumps(params)
        response = self.app.post('/api/action/vocabulary_update',
                params=param_string,
                extra_environ={'Authorization':
                    str(self.normal_user.apikey)},
                status=403)
        assert response.json['success'] is False
        assert response.json['error']['message'] == 'Access denied'

    def test_vocabulary_update_bad_tags(self):
        '''Test updating vocabularies with invalid tags.

        '''
        apikey = str(self.sysadmin_user.apikey)

        for tags in (
                [{'id': 'xxx'}, {'name': 'foo'}],
                [{'name': 'foo'}, {'name': None}],
                [{'name': 'foo'}, {'name': ''}],
                [{'name': 'foo'}, {'name': 'f'}],
                [{'name': 'f' * 200}, {'name': 'foo'}],
                [{'name': 'Invalid!'}, {'name': 'foo'}],
                ):
            params = {'id': self.genre_vocab['name'], 'tags': tags}
            response = self.app.post('/api/action/vocabulary_update',
                    params=helpers.json.dumps(params),
                    extra_environ={'Authorization': apikey},
                    status=409)
            assert response.json['success'] is False
            assert response.json['error']['tags']

    def test_vocabulary_update_none_tags(self):
        '''Test updating vocabularies with None for 'tags'.

        '''
        params = {'id': self.genre_vocab['id'], 'tags': None}
        response = self.app.post('/api/action/vocabulary_update',
                params=helpers.json.dumps(params),
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=400)
        assert "Integrity Error" in response.body, response.body

    def test_vocabulary_update_empty_tags(self):
        '''Test updating vocabularies with [] for 'tags'.

        '''
        params = {'id': self.genre_vocab['id'], 'tags': []}
        response = self.app.post('/api/action/vocabulary_update',
                params=helpers.json.dumps(params),
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=200)
        assert response.json['success'] is True
        assert response.json['result']
        updated_vocab = response.json['result']
        assert updated_vocab['name'] == self.genre_vocab['name']
        assert updated_vocab['id'] == self.genre_vocab['id']
        assert updated_vocab['tags'] == []
        params = {'id': updated_vocab['id']}
        response = self._post('/api/action/vocabulary_show', params)
        assert response['success'] is True
        assert response['result'] == updated_vocab
        tags = self._list_tags(updated_vocab)
        assert tags == []

    def test_vocabulary_delete(self):
        self._delete_vocabulary(self.genre_vocab['id'], self.sysadmin_user)

    def test_vocabulary_delete_not_exists(self):
        '''Test the error response given when a user tries to delete a
        vocabulary that doesn't exist.

        '''
        params = {'id': 'xxxxxxx'}
        param_string = helpers.json.dumps(params)
        response = self.app.post('/api/action/vocabulary_delete',
                params=param_string,
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=404)
        assert response.json['success'] is False
        assert response.json['error']['message'].startswith('Not found: '
                'Could not find vocabulary')

    def test_vocabulary_delete_no_id(self):
        '''Test the error response given when a user tries to delete a
        vocabulary without giving the vocabulary id.

        '''
        params = {}
        param_string = helpers.json.dumps(params)
        response = self.app.post('/api/action/vocabulary_delete',
                params=param_string,
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=409)
        assert response.json['success'] is False
        assert 'id' in response.json['error']
        assert response.json['error']['id'] == 'id not in data'

    def test_vocabulary_delete_not_logged_in(self):
        '''Test that users who are not logged in cannot delete vocabularies.'''
        params = {'id': self.genre_vocab['id']}
        param_string = helpers.json.dumps(params)
        response = self.app.post('/api/action/vocabulary_delete',
                params=param_string,
                status=403)
        assert response.json['success'] is False
        assert response.json['error']['__type'] == 'Authorization Error'

    def test_vocabulary_delete_not_authorized(self):
        '''Test that users who are not authorized cannot delete vocabs.'''
        params = {'id': self.genre_vocab['id']}
        param_string = helpers.json.dumps(params)
        response = self.app.post('/api/action/vocabulary_delete',
                params=param_string,
                extra_environ={'Authorization':
                    str(self.normal_user.apikey)},
                status=403)
        assert response.json['success'] is False
        assert response.json['error']['__type'] == 'Authorization Error'

    def test_add_tag_to_vocab(self):
        '''Test that a tag can be added to and then retrieved from a vocab.'''
        vocab = self.genre_vocab
        tags_before = self._list_tags(vocab)
        tag_created = self._create_tag(self.sysadmin_user, 'noise', vocab)
        tags_after = self._list_tags(vocab)
        new_tag_names = [tag_name for tag_name in tags_after if tag_name not in
                tags_before]
        assert len(new_tag_names) == 1
        assert tag_created['name'] in new_tag_names

    def test_add_tag_no_vocab(self):
        '''Test the error response when a user tries to create a tag without
        specifying a vocab.

        '''
        tag_dict = {'name': 'noise'}
        tag_string = helpers.json.dumps(tag_dict)
        response = self.app.post('/api/action/tag_create',
                params=tag_string,
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=409)
        assert response.json['success'] is False
        assert response.json['error']['vocabulary_id'] == ['Missing value']

    def test_add_tag_vocab_not_exists(self):
        '''Test the error response when a user tries to add a tag to a vocab
        that doesn't exist.

        '''
        tag_dict = {'name': 'noise', 'vocabulary_id': 'does not exist'}
        tag_string = helpers.json.dumps(tag_dict)
        response = self.app.post('/api/action/tag_create',
                params=tag_string,
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=409)
        assert response.json['success'] is False
        assert response.json['error']['vocabulary_id'] == [
                'Tag vocabulary was not found.']

    def test_add_tag_already_added(self):
        '''Test the error response when a user tries to add a tag to a vocab
        that already has a tag with the same name.

        '''
        self.test_add_tag_to_vocab()
        vocab = self.genre_vocab
        tag_dict = {'name': 'noise', 'vocabulary_id': vocab['id']}
        tag_string = helpers.json.dumps(tag_dict)
        response = self.app.post('/api/action/tag_create',
                params=tag_string,
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=409)
        assert response.json['success'] is False
        assert response.json['error']['vocabulary_id'][0].startswith(
            'Tag noise already belongs to vocabulary')

    def test_add_tag_with_id(self):
        '''Test the error response when a user tries to specify the tag ID when
        adding a tag to a vocab.

        '''
        tag_dict = {
                'id': 'dsagdsgsgsd',
                'name': 'noise',
                'vocabulary_id': self.genre_vocab['id']
                }
        tag_string = helpers.json.dumps(tag_dict)
        response = self.app.post('/api/action/tag_create',
                params=tag_string,
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=409)
        assert response.json['success'] is False
        assert response.json['error']['id'] == [u'The input field id was not '
            'expected.']

    def test_add_tag_without_name(self):
        '''Test the error response when a user tries to create a tag without a
        name.

        '''
        tag_dict = {
                'vocabulary_id': self.genre_vocab['id']
                }
        tag_string = helpers.json.dumps(tag_dict)
        response = self.app.post('/api/action/tag_create',
                params=tag_string,
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=409)
        assert response.json['success'] is False
        assert response.json['error']['name'] == [u'Missing value']

    def test_add_tag_invalid_name(self):
        for name in ('Not a valid tag name!', '', None):
            tag_dict = {
                    'name': name,
                    'vocabulary_id': self.genre_vocab['id']
                    }
            tag_string = helpers.json.dumps(tag_dict)
            response = self.app.post('/api/action/tag_create',
                    params=tag_string,
                    extra_environ={'Authorization':
                        str(self.sysadmin_apikey)},
                    status=409)
            assert response.json['success'] is False
            assert response.json['error']['name']

    def test_add_tag_invalid_vocab_id(self):
        tag_dict = {
                'name': 'noise',
                'vocabulary_id': 'xxcxzczxczxc',
                }
        tag_string = helpers.json.dumps(tag_dict)
        response = self.app.post('/api/action/tag_create',
                params=tag_string,
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=409)
        assert response.json['success'] is False
        assert response.json['error']['vocabulary_id'] == [
                u'Tag vocabulary was not found.']

    def test_add_tag_not_logged_in(self):
        tag_dict = {
                'name': 'noise',
                'vocabulary_id': self.genre_vocab['id']
                }
        tag_string = helpers.json.dumps(tag_dict)
        response = self.app.post('/api/action/tag_create',
                params=tag_string,
                status=403)
        assert response.json['success'] is False
        assert response.json['error']['__type'] == 'Authorization Error'

    def test_add_tag_not_authorized(self):
        tag_dict = {
                'name': 'noise',
                'vocabulary_id': self.genre_vocab['id']
                }
        tag_string = helpers.json.dumps(tag_dict)
        response = self.app.post('/api/action/tag_create',
                params=tag_string,
                    extra_environ={'Authorization':
                        str(self.normal_user.apikey)},
                status=403)
        assert response.json['success'] is False
        assert response.json['error']['__type'] == 'Authorization Error'

    def test_add_vocab_tag_to_dataset(self):
        '''Test that a tag belonging to a vocab can be added to a dataset,
        retrieved from the dataset, and then removed from the dataset.'''

        ckan.model.repo.rebuild_db()
        self.setup()
        ckan.tests.legacy.CreateTestData.create()
        # First add a tag to the vocab.
        vocab = self.genre_vocab
        tag = self._create_tag(self.sysadmin_user, 'noise', vocab)

        # Get a package from the API.
        package = (self._post('/api/action/package_show',
            {'id': self._post('/api/action/package_list')['result'][0]})
            ['result'])

        # Add the new vocab tag to the package.
        package['tags'].append(tag)

        updated_package = self._post('/api/action/package_update',
                params={'id': package['id'], 'tags': package['tags']},
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)})['result']

        # Test that the new vocab tag was added to the package.
        tags_in_pkg = [tag_in_pkg for tag_in_pkg in updated_package['tags'] if
                tag_in_pkg['name'] == tag['name'] and
                tag_in_pkg['vocabulary_id'] == tag['vocabulary_id']]
        assert len(tags_in_pkg) == 1

        # Test that the package appears in tag_show.
        noise_tag = self._post('/api/action/tag_show',
                               params={'id': 'noise',
                                       'vocabulary_id': vocab['id'],
                                       'include_datasets': True}
                               )['result']
        assert len([p for p in noise_tag['packages'] if
                    p['id'] == updated_package['id']]) == 1

        # Remove the new vocab tag from the package.
        package['tags'].remove(tag)
        updated_package = self._post('/api/action/package_update',
                params={'id': package['id'], 'tags': package['tags']},
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)})['result']

        # Test that the tag no longer appears in the list of tags for the
        # package.
        package = (self._post('/api/action/package_show',
            {'id': self._post('/api/action/package_list')['result'][0]})
            ['result'])
        tags_in_pkg = [tag_in_pkg for tag_in_pkg in package['tags'] if
                tag_in_pkg['name'] == tag['name'] and
                tag_in_pkg['vocabulary_id'] == tag['vocabulary_id']]
        assert len(tags_in_pkg) == 0

    def test_delete_tag_from_vocab(self):
        '''Test that a tag can be deleted from a vocab.'''

        ckan.model.repo.rebuild_db()
        self.setup()
        ckan.tests.legacy.CreateTestData.create()
        vocab = self.genre_vocab

        # First add some tags to the vocab.
        noise_tag = self._create_tag(self.sysadmin_user, 'noise', vocab)
        ragga_tag = self._create_tag(self.sysadmin_user, 'ragga', vocab)
        grunge_tag = self._create_tag(self.sysadmin_user, 'grunge', vocab)
        funk_tag = self._create_tag(self.sysadmin_user, 'funk', vocab)
        tags = (noise_tag, ragga_tag, grunge_tag, funk_tag)

        # Get a package from the API.
        package = (self._post('/api/action/package_show',
            {'id': self._post('/api/action/package_list')['result'][0]})
            ['result'])

        # Add the new vocab tags to the package.
        for tag in tags:
            package['tags'].append(tag)

        updated_package = self._post('/api/action/package_update',
                params={'id': package['id'], 'tags': package['tags']},
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)})['result']

        # Test that the new vocab tags were added to the package.
        for tag in tags:
            tags_in_pkg = [tag_in_pkg for tag_in_pkg in
                    updated_package['tags'] if tag_in_pkg['name'] ==
                    tag['name'] and tag_in_pkg['vocabulary_id'] ==
                    tag['vocabulary_id']]
            assert len(tags_in_pkg) == 1

        # Now delete the tags from the vocab.
        tags_before = self._list_tags(vocab)
        self._delete_tag(self.sysadmin_user, noise_tag['name'], vocab['name'])
        self._delete_tag(self.sysadmin_user, ragga_tag['id'], vocab['name'])
        self._delete_tag(self.sysadmin_user, grunge_tag['id'], vocab['id'])
        self._delete_tag(self.sysadmin_user, funk_tag['name'], vocab['id'])

        # Test that the tags no longer appear in the list of tags for the
        # vocab.
        tags_after = self._list_tags(vocab)
        assert len(tags_after) == len(tags_before) - 4
        assert tag['name'] not in tags_after
        difference = [tag_name for tag_name in tags_before if tag_name not in
                tags_after]
        assert sorted(difference) == sorted([tag['name'] for tag in tags])

        # Test that the tags no longer appear in the list of tags for the
        # package.
        package = (self._post('/api/action/package_show',
            {'id': self._post('/api/action/package_list')['result'][0]})
            ['result'])
        for tag in tags:
            tags_in_pkg = [tag_in_pkg for tag_in_pkg in package['tags'] if
                    tag_in_pkg['name'] == tag['name'] and
                    tag_in_pkg['vocabulary_id'] == tag['vocabulary_id']]
            assert len(tags_in_pkg) == 0

    def test_delete_free_tag(self):
        '''Test that a free tag can be deleted via the API, and is
        automatically removed from datasets.

        '''
        ckan.model.repo.rebuild_db()
        self.setup()
        ckan.tests.legacy.CreateTestData.create()
        # Get a package from the API.
        package = (self._post('/api/action/package_show',
            {'id': self._post('/api/action/package_list')['result'][0]})
            ['result'])
        package_id = package['id']

        # Add some new free tags to the package.
        tags = package['tags']
        tags.append({'name': 'ducks'})
        tags.append({'name': 'birds'})
        self._post('/api/action/package_update',
                params={'id': package['id'], 'tags': tags},
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)})

        # Test that the new tags appear in the list of tags.
        tags = self._list_tags()
        assert [tag for tag in tags].count('ducks') == 1
        assert [tag for tag in tags].count('birds') == 1

        # Test that the new tags appear in the package's list of tags.
        package = (self._post('/api/action/package_show',
            {'id': package_id})['result'])
        packages_tags = [tag['name'] for tag in package['tags']]
        assert [tag for tag in packages_tags].count('ducks') == 1
        assert [tag for tag in packages_tags].count('birds') == 1

        # Now delete the tags.
        self._delete_tag(self.sysadmin_user, 'ducks')
        birds_tag_id = self._post('/api/action/tag_show',
                {'id': 'birds'})['result']['id']
        self._delete_tag(self.sysadmin_user, birds_tag_id)

        # Test that the tags no longer appear in the list of tags.
        tags = self._list_tags()
        assert [tag for tag in tags].count('ducks') == 0
        assert [tag for tag in tags].count('birds') == 0

        # Test that the tags no longer appear in the package's list of tags.
        package = (self._post('/api/action/package_show',
            {'id': package_id})['result'])
        packages_tags = [tag['name'] for tag in package['tags']]
        assert [tag for tag in packages_tags].count('ducks') == 0
        assert [tag for tag in packages_tags].count('birds') == 0

    def test_delete_tag_no_id(self):
        '''Test the error response when a user tries to delete a tag without
        giving the tag id.

        '''
        vocab = self.genre_vocab
        self._create_tag(self.sysadmin_user, 'noise', vocab)

        for tag_id in ('missing', '', None):
            # Now try to delete the tag from the vocab.
            params = {'vocabulary_id': vocab['name']}
            if tag_id != 'missing':
                params['id'] = tag_id
            response = self.app.post('/api/action/tag_delete',
                    params=helpers.json.dumps(params),
                    extra_environ={'Authorization':
                        str(self.sysadmin_user.apikey)},
                    status=409)
            assert response.json['success'] is False
            assert 'id' in response.json['error']
            assert response.json['error']['id'] == 'id not in data'

    def test_delete_tag_no_vocab(self):
        '''Test the error response when a user tries to delete a vocab tag
        without giving the vocab name.

        '''
        vocab = self.genre_vocab
        tag = self._create_tag(self.sysadmin_user, 'noise', vocab)

        # Now try to delete the tag from the vocab.
        for vocab_name in ('', None, 'missing'):
            params = {'id': tag['name']}
            if vocab_name != 'missing':
                params['vocabulary_id'] = vocab_name
            response = self.app.post('/api/action/tag_delete',
                    params=helpers.json.dumps(params),
                    extra_environ={'Authorization':
                        str(self.sysadmin_user.apikey)},
                    status=404)
            assert response.json['success'] is False
            msg = response.json['error']['message']
            assert msg == u'Not found: Could not find tag "{0}"'.format(
                    tag['name']), msg

    def test_delete_tag_not_exists(self):
        '''Test the error response when a user tries to delete a from a vocab
        but there is no tag with that name in the vocab.

        '''
        vocab = self.genre_vocab
        self._create_tag(self.sysadmin_user, 'noise', vocab)

        params = {'id': 'nonexistent',
                'vocabulary_id': self.genre_vocab['name']}
        response = self.app.post('/api/action/tag_delete',
                params=helpers.json.dumps(params),
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=404)
        assert response.json['success'] is False
        msg = response.json['error']['message']
        assert msg == u'Not found: Could not find tag "%s"' % 'nonexistent', \
                msg

    def test_delete_tag_vocab_not_exists(self):
        '''Test the error response when a user tries to delete a from a vocab
        but there is no vocab with that name.

        '''
        vocab = self.genre_vocab
        tag = self._create_tag(self.sysadmin_user, 'noise', vocab)

        params = {'id': tag['name'],
                'vocabulary_id': 'nonexistent'}
        response = self.app.post('/api/action/tag_delete',
                params=helpers.json.dumps(params),
                extra_environ={'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=404)
        assert response.json['success'] is False
        msg = response.json['error']['message']
        assert msg == u"Not found: could not find vocabulary 'nonexistent'", \
                msg

    def test_delete_tag_invalid_tag(self):
        '''Test the error response when a user tries to delete a tag but gives
        an invalid tag name.

        '''
        vocab = self.genre_vocab
        self._create_tag(self.sysadmin_user, 'noise', vocab)

        for tag_name in ('Invalid!', ' '):
            params = {'id': tag_name,
                    'vocabulary_id': self.genre_vocab['name']}
            response = self.app.post('/api/action/tag_delete',
                    params=helpers.json.dumps(params),
                    extra_environ={'Authorization':
                        str(self.sysadmin_user.apikey)},
                    status=404)
            assert response.json['success'] is False
            msg = response.json['error']['message']
            assert msg == u'Not found: Could not find tag "%s"' % tag_name, msg

    def test_delete_tag_invalid_vocab(self):
        '''Test the error response when a user tries to delete a tag but gives
        an invalid vocab name.

        '''
        vocab = self.genre_vocab
        tag = self._create_tag(self.sysadmin_user, 'noise', vocab)

        for vocab_name in ('Invalid!', ' '):
            params = {'id': tag['name'], 'vocabulary_id': vocab_name}
            response = self.app.post('/api/action/tag_delete',
                    params=helpers.json.dumps(params),
                    extra_environ={'Authorization':
                        str(self.sysadmin_user.apikey)},
                    status=404)
            assert response.json['success'] is False
            msg = response.json['error']['message']
            assert msg == u"Not found: could not find vocabulary '%s'" \
                    % vocab_name, msg

    def test_delete_tag_not_logged_in(self):
        vocab = self.genre_vocab
        tag = self._create_tag(self.sysadmin_user, 'noise', vocab)

        params = {'id': tag['name'],
                'vocabulary_id': self.genre_vocab['name']}
        response = self.app.post('/api/action/tag_delete',
                params=helpers.json.dumps(params),
                status=403)
        assert response.json['success'] is False
        error = response.json['error']['__type']
        assert error == u"Authorization Error", error

    def test_delete_tag_not_authorized(self):
        vocab = self.genre_vocab
        tag = self._create_tag(self.sysadmin_user, 'noise', vocab)

        params = {'id': tag['name'],
                'vocabulary_id': self.genre_vocab['name']}
        response = self.app.post('/api/action/tag_delete',
                params=helpers.json.dumps(params),
                extra_environ={'Authorization':
                    str(self.normal_user.apikey)},
                status=403)
        assert response.json['success'] is False
        msg = response.json['error']['__type']
        assert msg == u"Authorization Error"
