import ckan
from pylons.test import pylonsapp
import paste.fixture
from ckan.lib.helpers import json
import sqlalchemy
from nose.tools import raises, assert_raises

class TestVocabulary(object):

    def setup(self):
        self.app = paste.fixture.TestApp(pylonsapp)
        ckan.tests.CreateTestData.create()
        self.sysadmin_user = ckan.model.User.get('testsysadmin')
        self.normal_user = ckan.model.User.get('annafan')
        # Make a couple of test vocabularies needed later.
        self.genre_vocab = self._create_vocabulary(vocab_name="Genre",
                user=self.sysadmin_user)
        self.timeperiod_vocab = self._create_vocabulary(
                vocab_name="Time Period", user=self.sysadmin_user)
        self.composers_vocab = self._create_vocabulary(vocab_name="Composers",
                user=self.sysadmin_user)

    def teardown(self):
        ckan.model.repo.rebuild_db()

    def _post(self, url, params=None, extra_environ=None):
        if params is None:
            params = {}
        param_string = json.dumps(params)
        response = self.app.post(url, params=param_string,
                extra_environ=extra_environ)
        assert not response.errors
        return response.json

    def _create_vocabulary(self, vocab_name=None, user=None):
        # Create a new vocabulary.
        params = {'name': vocab_name}
        if user:
            extra_environ = {'Authorization' : str(user.apikey)}
        else:
            extra_environ = None
        response = self._post('/api/action/vocabulary_create', params=params,
                extra_environ=extra_environ)

        # Check the values of the response.
        assert response['success'] == True
        assert response['result']
        created_vocab = response['result']
        assert created_vocab['name'] == vocab_name
        assert created_vocab['id']

        # Get the list of vocabularies.
        response = self._post('/api/action/vocabulary_list')
        # Check that the vocabulary we created is in the list.
        assert response['success'] == True
        assert response['result']
        assert response['result'].count(created_vocab) == 1

        # Get the created vocabulary.
        params = {'id': created_vocab['id']}
        response = self._post('/api/action/vocabulary_show', params)
        # Check that retrieving the vocab by name gives the same result.
        by_name_params = {'name': created_vocab['name']}
        assert response == self._post('/api/action/vocabulary_show',
                by_name_params)
        # Check that it matches what we created.
        assert response['success'] == True
        assert response['result'] == created_vocab

        return created_vocab

    def _update_vocabulary(self, params, user=None):
        if user:
            extra_environ = {'Authorization' : str(user.apikey)}
        else:
            extra_environ = None
        response = self._post('/api/action/vocabulary_update', params=params,
                extra_environ=extra_environ)

        # Check the values of the response.
        assert response['success'] == True
        assert response['result']
        updated_vocab = response['result']
        if params.has_key('id'):
            assert updated_vocab['id'] == params['id']
        else:
            assert updated_vocab['id']
        if params.has_key('name'):
            assert updated_vocab['name'] == params['name']
        else:
            assert updated_vocab['name']

        # Get the list of vocabularies.
        response = self._post('/api/action/vocabulary_list')
        # Check that the vocabulary we created is in the list.
        assert response['success'] == True
        assert response['result']
        assert response['result'].count(updated_vocab) == 1

        # Get the created vocabulary.
        params = {'id': updated_vocab['id']}
        response = self._post('/api/action/vocabulary_show', params)
        # Check that retrieving the vocab by name gives the same result.
        by_name_params = {'name': updated_vocab['name']}
        assert response == self._post('/api/action/vocabulary_show',
                by_name_params)
        # Check that it matches what we created.
        assert response['success'] == True
        assert response['result'] == updated_vocab

        return updated_vocab

    def _delete_vocabulary(self, vocab_id, user=None):
        if user:
            extra_environ = {'Authorization' : str(user.apikey)}
        else:
            extra_environ = None
        params = {'id': vocab_id}
        response = self._post('/api/action/vocabulary_delete', params=params,
                extra_environ=extra_environ)

        # Check the values of the response.
        assert response['success'] == True
        assert response['result'] is None
        response['result']

        # Get the list of vocabularies.
        response = self._post('/api/action/vocabulary_list')
        assert response['success'] == True
        assert response['result']
        # Check that the vocabulary we deleted is not in the list.
        assert vocab_id not in [vocab['id'] for vocab in response['result']]

        # Check that the deleted vocabulary can no longer be retrieved.
        response = self.app.post('/api/action/vocabulary_show',
                params=json.dumps(params),
                extra_environ = {'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=404)
        assert response.json['success'] == False

    def _list_tags(self, vocabulary, user=None):
        params = {'vocabulary_name': vocabulary['name']}
        if user:
            extra_environ = {'Authorization' : str(user.apikey)}
        else:
            extra_environ = None
        response = self._post('/api/action/tag_list', params=params,
                extra_environ=extra_environ)
        assert response['success'] == True
        return response['result']

    def _create_tag(self, user, tag_name, vocabulary=None):
        tag_dict = {'name': tag_name}
        if vocabulary:
            tag_dict['vocabulary_id'] = vocabulary['id']
        if user:
            extra_environ = {'Authorization' : str(user.apikey)}
        else:
            extra_environ = None
        response = self._post('/api/action/tag_create', params=tag_dict,
                extra_environ=extra_environ)
        assert response['success'] == True
        return response['result']

    def test_vocabulary_create(self):
        '''Test adding a new vocabulary to a CKAN instance via the action
        API.

        '''
        self._create_vocabulary(vocab_name="My cool vocab",
                user=self.sysadmin_user)

    def test_vocabulary_create_id(self):
        '''Test error response when user tries to supply their own ID when
        creating a vocabulary.
        
        '''
        params = {'id': 'xxx', 'name': 'foobar'}
        param_string = json.dumps(params)
        response = self.app.post('/api/action/vocabulary_create',
                params=param_string,
                extra_environ = {'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=409)
        assert response.json['success'] == False

    def test_vocabulary_create_no_name(self):
        '''Test error response when user tries to create a vocab without a
        name.

        '''
        params = {}
        param_string = json.dumps(params)
        response = self.app.post('/api/action/vocabulary_create',
                params=param_string,
                extra_environ = {'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=409)
        assert response.json['success'] == False

    def test_vocabulary_create_invalid_name(self):
        '''Test error response when user tries to create a vocab with an
        invalid name.

        '''
        for name in (None, '', 'a', 'foobar'*100):
            params = {'name': name}
            param_string = json.dumps(params)
            response = self.app.post('/api/action/vocabulary_create',
                    params=param_string,
                    extra_environ = {'Authorization':
                        str(self.sysadmin_user.apikey)},
                    status=409)
            assert response.json['success'] == False

    def test_vocabulary_create_exists(self):
        '''Test error response when user tries to create a vocab that already
        exists.

        '''
        params = {'name': self.genre_vocab['name']}
        param_string = json.dumps(params)
        response = self.app.post('/api/action/vocabulary_create',
                params=param_string,
                extra_environ = {'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=409)
        assert response.json['success'] == False

    def test_vocabulary_create_not_logged_in(self):
        '''Test that users who are not logged in cannot create vocabularies.'''

        params = {'name':
            "Spam Vocabulary: SpamCo Duck Rental: Rent Your Ducks From Us!"}
        param_string = json.dumps(params)
        response = self.app.post('/api/action/vocabulary_create',
                params=param_string,
                status=403)
        assert response.json['success'] == False

    def test_vocabulary_create_not_authorized(self):
        '''Test that users who are not authorized cannot create vocabs.'''

        params = {'name': 'My Unauthorised Vocabulary'}
        param_string = json.dumps(params)
        response = self.app.post('/api/action/vocabulary_create',
                params=param_string,
                extra_environ = {'Authorization':
                    str(self.normal_user.apikey)},
                status=403)
        assert response.json['success'] == False

    def test_vocabulary_update(self):
        self._update_vocabulary({'id': self.genre_vocab['id'],
            'name': 'updated_name'}, self.sysadmin_user)

    def test_vocabulary_update_not_exists(self):
        '''Test the error response given when a user tries to update a
        vocabulary that doesn't exist.

        '''
        params = {'id': 'xxxxxxx', 'name': 'updated_name'}
        param_string = json.dumps(params)
        response = self.app.post('/api/action/vocabulary_update',
                params=param_string,
                extra_environ = {'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=404)
        assert response.json['success'] == False

    def test_vocabulary_update_no_name(self):
        params = {'id': self.genre_vocab['id']}
        param_string = json.dumps(params)
        response = self.app.post('/api/action/vocabulary_update',
                params=param_string,
                extra_environ = {'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=409)
        assert response.json['success'] == False

    def test_vocabulary_update_not_logged_in(self):
        '''Test that users who are not logged in cannot update vocabularies.'''
        params = {'id': self.genre_vocab['id']}
        param_string = json.dumps(params)
        response = self.app.post('/api/action/vocabulary_update',
                params=param_string,
                status=403)
        assert response.json['success'] == False

    def test_vocabulary_update_not_authorized(self):
        '''Test that users who are not authorized cannot update vocabs.'''
        params = {'id': self.genre_vocab['id']}
        param_string = json.dumps(params)
        response = self.app.post('/api/action/vocabulary_update',
                params=param_string,
                extra_environ = {'Authorization':
                    str(self.normal_user.apikey)},
                status=403)
        assert response.json['success'] == False

    def test_vocabulary_delete(self):
        self._delete_vocabulary(self.genre_vocab['id'], self.sysadmin_user)

    def test_vocabulary_delete_not_exists(self):
        '''Test the error response given when a user tries to delete a
        vocabulary that doesn't exist.

        '''
        params = {'id': 'xxxxxxx'}
        param_string = json.dumps(params)
        response = self.app.post('/api/action/vocabulary_delete',
                params=param_string,
                extra_environ = {'Authorization':
                    str(self.sysadmin_user.apikey)},
                status=404)
        assert response.json['success'] == False

    def test_vocabulary_delete_not_logged_in(self):
        '''Test that users who are not logged in cannot delete vocabularies.'''
        params = {'id': self.genre_vocab['id']}
        param_string = json.dumps(params)
        response = self.app.post('/api/action/vocabulary_delete',
                params=param_string,
                status=403)
        assert response.json['success'] == False

    def test_vocabulary_delete_not_authorized(self):
        '''Test that users who are not authorized cannot delete vocabs.'''
        params = {'id': self.genre_vocab['id']}
        param_string = json.dumps(params)
        response = self.app.post('/api/action/vocabulary_delete',
                params=param_string,
                extra_environ = {'Authorization':
                    str(self.normal_user.apikey)},
                status=403)
        assert response.json['success'] == False

    def test_add_tag_to_vocab(self):
        vocab = self._create_vocabulary(vocab_name="Musical Genres",
                user=self.sysadmin_user)
        tags_before = self._list_tags(vocab)
        assert len(tags_before) == 0, tags_before
        tag_created = self._create_tag(self.sysadmin_user, 'noise', vocab)
        tags_after = self._list_tags(vocab)
        assert len(tags_after) == 1
        assert tag_created['name'] in tags_after
