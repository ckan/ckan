import datetime
import paste
import pylons.test
import ckan
from ckan.lib.helpers import json

def datetime_from_string(s):
    '''Return a standard datetime.datetime object initialised from a string in
    the same format used for timestamps in dictized activities (the format
    produced by datetime.datetime.isoformat())

    '''
    return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f')

class TestFollow(object):

    @classmethod
    def setup_class(self):
        ckan.tests.CreateTestData.create()
        self.testsysadmin = ckan.model.User.get('testsysadmin')
        self.annafan = ckan.model.User.get('annafan')
        self.russianfan = ckan.model.User.get('russianfan')
        self.tester = ckan.model.User.get('tester')
        self.tester = ckan.model.User.get('joeadmin')
        self.warandpeace = ckan.model.Package.get('warandpeace')
        self.annakarenina = ckan.model.Package.get('annakarenina')
        self.app = paste.fixture.TestApp(pylons.test.pylonsapp)

    @classmethod
    def teardown_class(self):
        ckan.model.repo.rebuild_db()

    def _start_following(self, follower_id, api_key, object_id, object_type,
            object_arg):
        '''Test a user starting to follow an object via the API.

        :param follower_id: id of the user that will be following something.
        :param api_key: API key of the user that will be following something.
        :param object_id: id of the object that will be followed by the user.
        :param object_type: type of the object that will be followed by the
            user, e.g. 'user' or 'dataset'.
        :param object_arg: the argument to pass to follower_create as the id of
            the object that will be followed, could be the object's id or name.

        '''

        # Record the object's number of followers before.
        params = json.dumps({'id': object_id})
        response = self.app.post('/api/action/follower_count',
                params=params).json
        assert response['success'] is True
        count_before = response['result']

        # Make the  user start following the object.
        before = datetime.datetime.now()
        params = json.dumps({
            'object_id': object_arg,
            'object_type': object_type,
            })
        extra_environ = {
                'Authorization': str(api_key)
                }
        response = self.app.post('/api/action/follower_create',
            params=params, extra_environ=extra_environ).json
        after = datetime.datetime.now()
        assert response['success'] is True
        assert response['result']
        follower = response['result']
        assert follower['follower_id'] == follower_id
        assert follower['follower_type'] == 'user'
        assert follower['object_id'] == object_id
        assert follower['object_type'] == object_type
        timestamp = datetime_from_string(follower['datetime'])
        assert (timestamp >= before and timestamp <= after), str(timestamp)

        # Check that the user appears in the object's list of followers.
        params = json.dumps({'id': object_id})
        response = self.app.post('/api/action/follower_list',
                params=params).json
        assert response['success'] is True
        assert response['result']
        followers = response['result']
        assert len(followers) == 1
        follower = followers[0]
        assert follower['id'] == follower_id

        # Check that the object's follower count has increased by 1.
        params = json.dumps({'id': object_id})
        response = self.app.post('/api/action/follower_count',
                params=params).json
        assert response['success'] is True
        assert response['result'] == count_before + 1

    def test_user_follow_user(self):

        # Test with a bad API key.
        params = json.dumps({
            'object_id': self.russianfan.id,
            'object_type': 'user',
            })
        extra_environ = {
                'Authorization': 'bad api key'
                }
        response = self.app.post('/api/action/follower_create',
            params=params, extra_environ=extra_environ, status=403).json
        assert response['success'] == False
        assert response['error']['message'] == 'Access denied'

        # Test with a bad object ID.
        params = json.dumps({
            'object_id': 'bad id',
            'object_type': 'user',
            })
        extra_environ = {
                'Authorization': str(self.annafan.apikey),
                }
        response = self.app.post('/api/action/follower_create',
            params=params, extra_environ=extra_environ, status=409).json
        assert response['success'] == False
        assert response['error']['object_id'] == ['Not found: User']

        # Test with a bad object type.
        params = json.dumps({
            'object_id': self.russianfan.id,
            'object_type': 'foobar',
            })
        extra_environ = {
                'Authorization': str(self.annafan.apikey),
                }
        response = self.app.post('/api/action/follower_create',
            params=params, extra_environ=extra_environ, status=409).json
        assert response['success'] == False
        assert response['error']['object_id'] == ['object_type foobar not recognised']

        # Test with missing API key.
        params = json.dumps({
            'object_id': self.russianfan.id,
            'object_type': 'user',
            })
        response = self.app.post('/api/action/follower_create',
            params=params, status=403).json
        assert response['success'] == False
        assert response['error']['message'] == 'Access denied'

        # Test with missing object_id.
        params = json.dumps({
            'object_type': 'user',
            })
        extra_environ = {
                'Authorization': str(self.annafan.apikey),
                }
        response = self.app.post('/api/action/follower_create',
            params=params, extra_environ=extra_environ, status=409).json
        assert response['success'] == False
        assert response['error']['object_id'] == ['Missing value']

        # Test with missing object_type.
        params = json.dumps({
            'object_id': self.russianfan.id,
            })
        extra_environ = {
                'Authorization': str(self.annafan.apikey),
                }
        response = self.app.post('/api/action/follower_create',
            params=params, extra_environ=extra_environ, status=409).json
        assert response['success'] == False
        assert response['error']['object_type'] == ['Missing value']

        # Test with good arguments.
        self._start_following(self.annafan.id, self.annafan.apikey,
                self.russianfan.id, 'user', self.russianfan.id)

        # Test with good arguments, by name.
        self._start_following(self.annafan.id, self.annafan.apikey,
                self.testsysadmin.id, 'user', self.testsysadmin.name)

        # Test trying to follow a user that the user is already following.
        for object_id in (self.russianfan.id, self.russianfan.name,
                self.testsysadmin.id, self.testsysadmin.name):
            params = json.dumps({
                'object_id': object_id,
                'object_type': 'user',
                })
            extra_environ = {
                    'Authorization': str(self.annafan.apikey),
                    }
            response = self.app.post('/api/action/follower_create',
                params=params, extra_environ=extra_environ, status=409).json
            assert response['success'] == False
            assert response['error']['message'].startswith(
                    'Follower {follower_id} -> '.format(
                        follower_id = self.annafan.id))
            assert response['error']['message'].endswith(' already exists')

        # Test that a user cannot follow herself.
        params = json.dumps({
            'object_id': self.annafan.id,
            'object_type': 'user',
            })
        extra_environ = {
                'Authorization': str(self.annafan.apikey),
                }
        response = self.app.post('/api/action/follower_create',
            params=params, extra_environ=extra_environ, status=409).json
        assert response['success'] == False
        assert response['error']['object_id'] == [
                'An object cannot follow itself']

    def test_user_follow_dataset(self):

        # Test with a bad API key.
        params = json.dumps({
            'object_id': self.warandpeace.id,
            'object_type': 'dataset',
            })
        extra_environ = {
                'Authorization': 'bad api key'
                }
        response = self.app.post('/api/action/follower_create',
            params=params, extra_environ=extra_environ, status=403).json
        assert response['success'] == False
        assert response['error']['message'] == 'Access denied'

        # Test with a bad object ID.
        params = json.dumps({
            'object_id': 'bad id',
            'object_type': 'dataset',
            })
        extra_environ = {
                'Authorization': str(self.annafan.apikey),
                }
        response = self.app.post('/api/action/follower_create',
            params=params, extra_environ=extra_environ, status=409).json
        assert response['success'] == False
        assert response['error']['object_id'] == ['Not found: Dataset']

        # Test with a bad object type.
        params = json.dumps({
            'object_id': self.warandpeace.id,
            'object_type': 'foobar',
            })
        extra_environ = {
                'Authorization': str(self.annafan.apikey),
                }
        response = self.app.post('/api/action/follower_create',
            params=params, extra_environ=extra_environ, status=409).json
        assert response['success'] == False
        assert response['error']['object_id'] == ['object_type foobar not recognised']

        # Test with missing API key.
        params = json.dumps({
            'object_id': self.warandpeace.id,
            'object_type': 'dataset',
            })
        response = self.app.post('/api/action/follower_create',
            params=params, status=403).json
        assert response['success'] == False
        assert response['error']['message'] == 'Access denied'

        # Test with missing object_id.
        params = json.dumps({
            'object_type': 'dataset',
            })
        extra_environ = {
                'Authorization': str(self.annafan.apikey),
                }
        response = self.app.post('/api/action/follower_create',
            params=params, extra_environ=extra_environ, status=409).json
        assert response['success'] == False
        assert response['error']['object_id'] == ['Missing value']

        # Test with missing object_type.
        params = json.dumps({
            'object_id': self.warandpeace.id,
            })
        extra_environ = {
                'Authorization': str(self.annafan.apikey),
                }
        response = self.app.post('/api/action/follower_create',
            params=params, extra_environ=extra_environ, status=409).json
        assert response['success'] == False
        assert response['error']['object_type'] == ['Missing value']

        # Test with good arguments.
        self._start_following(self.annafan.id, self.annafan.apikey,
                self.warandpeace.id, 'dataset', self.warandpeace.id)

        # Test with good arguments, by name.
        self._start_following(self.annafan.id, self.annafan.apikey,
                self.annakarenina.id, 'dataset', self.annakarenina.name)

        # Test trying to follow a dataset that the user is already following.
        for object_id in (self.warandpeace.id, self.warandpeace.name,
                self.annakarenina.id, self.annakarenina.name):
            params = json.dumps({
                'object_id': object_id,
                'object_type': 'dataset',
                })
            extra_environ = {
                    'Authorization': str(self.annafan.apikey),
                    }
            response = self.app.post('/api/action/follower_create',
                params=params, extra_environ=extra_environ, status=409).json
            assert response['success'] == False
            assert response['error']['message'].startswith(
                    'Follower {follower_id} -> '.format(
                        follower_id = self.annafan.id))
            assert response['error']['message'].endswith(' already exists')

# Test follow with datetime, should be ignored.
