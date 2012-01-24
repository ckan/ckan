import ckan
from pylons.test import pylonsapp
import paste.fixture
from ckan.lib.helpers import json

class TestVocabulary(object):

    @classmethod
    def setup_class(cls):
        cls.app = paste.fixture.TestApp(pylonsapp)
        ckan.tests.CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        ckan.model.repo.rebuild_db()

    def post(self, url, param_dict=None):
        if param_dict is None:
            param_dict = {}
        param_string = json.dumps(param_dict)
        response = self.app.post(url, params=param_string)
        assert not response.errors
        return response.json

    def test_vocabulary_create(self):

        # Create a new vocabulary.
        vocab_name = "Genre"
        params = {'vocabulary': {'name': vocab_name}}
        response = self.post('/api/action/vocabulary_create', params)
        # Check the values of the response.
        assert response['success'] == True
        assert response['result']
        created_vocab = response['result']
        assert created_vocab['name'] == vocab_name
        assert created_vocab['id']

        # Get the list of vocabularies.
        response = self.post('/api/action/vocabulary_list')
        # Check that the vocabulary we created is in the list.
        assert response['success'] == True
        assert response['result']
        assert response['result'].count(created_vocab) == 1

        # Get the created vocabulary.
        params = {'id': created_vocab['id']}
        response = self.post('/api/action/vocabulary_show', params)
        # Check that retrieving the vocab by name gives the same result.
        by_name_params = {'name': created_vocab['name']}
        assert response == self.post('/api/action/vocabulary_show',
                by_name_params)
        # Check that it matches what we created.
        assert response['success'] == True
        assert response['result'] == created_vocab

    def test_vocabulary_update(self):
        # Create a vocab.
        # Update the vocab via the API.
        # List vocabs
        # Get vocab, assert fields correct.
        raise NotImplementedError

    def test_vocabulary_delete(self):
        # Create a vocab.
        # Delete a vocab via the API
        # List vocabs, assert that it's gone.
        raise NotImplementedError

