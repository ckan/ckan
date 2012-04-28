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
    '''Tests for the follow API.'''

    @classmethod
    def setup_class(self):
        ckan.tests.CreateTestData.create()
        self.testsysadmin = ckan.model.User.get('testsysadmin')
        self.annafan = ckan.model.User.get('annafan')
        self.russianfan = ckan.model.User.get('russianfan')
        self.tester = ckan.model.User.get('tester')
        self.joeadmin = ckan.model.User.get('joeadmin')
        self.warandpeace = ckan.model.Package.get('warandpeace')
        self.annakarenina = ckan.model.Package.get('annakarenina')
        self.app = paste.fixture.TestApp(pylons.test.pylonsapp)

    @classmethod
    def teardown_class(self):
        ckan.model.repo.rebuild_db()

    def _start_following(self, follower_id, api_key, object_id, object_type,
            object_arg, datetime_param=None):
        '''Test a user starting to follow an object via the API.

        :param follower_id: id of the user that will be following something.
        :param api_key: API key of the user that will be following something.
        :param object_id: id of the object that will be followed by the user.
        :param object_type: type of the object that will be followed by the
            user, e.g. 'user' or 'dataset'.
        :param object_arg: the argument to pass to follower_create as the id of
            the object that will be followed, could be the object's id or name.
        :param datetime_param Will be passed as 'datetime' arg to
            follower_create

        '''

        # Record the object's number of followers before.
        params = json.dumps({'id': object_id})
        response = self.app.post('/api/action/follower_count',
                params=params).json
        assert response['success'] is True
        count_before = response['result']

        # Check that the user is not already following the object.
        params = json.dumps({'id': object_id})
        extra_environ = {'Authorization': str(api_key)}
        response = self.app.post('/api/action/am_following',
                params=params, extra_environ=extra_environ).json
        assert response['success'] is True
        assert response['result'] is False

        # Make the  user start following the object.
        before = datetime.datetime.now()
        params = {
            'object_id': object_arg,
            'object_type': object_type,
            }
        if datetime_param:
            params['datetime'] = datetime_param
        extra_environ = {'Authorization': str(api_key)}
        response = self.app.post('/api/action/follower_create',
            params=json.dumps(params), extra_environ=extra_environ).json
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

        # Check that am_following now returns True.
        params = json.dumps({'id': object_id})
        extra_environ = {'Authorization': str(api_key)}
        response = self.app.post('/api/action/am_following',
                params=params, extra_environ=extra_environ).json
        assert response['success'] is True
        assert response['result'] is True

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

    def test_01_user_follow_user_bad_api_key(self):
        for apikey in ('bad api key', '', '     ', 'None', '3', '35.7', 'xxx'):
            params = json.dumps({
                'object_id': self.russianfan.id,
                'object_type': 'user',
                })
            extra_environ = {
                    'Authorization': apikey,
                    }
            response = self.app.post('/api/action/follower_create',
                params=params, extra_environ=extra_environ, status=403).json
            assert response['success'] == False
            assert response['error']['message'] == 'Access denied'

    def test_01_user_follow_dataset_bad_api_key(self):
        for apikey in ('bad api key', '', '     ', 'None', '3', '35.7', 'xxx'):
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

    def test_01_user_follow_user_missing_api_key(self):
        params = json.dumps({
            'object_id': self.russianfan.id,
            'object_type': 'user',
            })
        response = self.app.post('/api/action/follower_create',
            params=params, status=403).json
        assert response['success'] == False
        assert response['error']['message'] == 'Access denied'

    def test_01_user_follow_dataset_missing_api_key(self):
        params = json.dumps({
            'object_id': self.warandpeace.id,
            'object_type': 'dataset',
            })
        response = self.app.post('/api/action/follower_create',
            params=params, status=403).json
        assert response['success'] == False
        assert response['error']['message'] == 'Access denied'

    def test_01_user_follow_user_bad_object_id(self):
        for object_id in ('bad id', '', '     ', None, 3, 35.7, 'xxx'):
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

    def test_01_user_follow_dataset_bad_object_id(self):
        for object_id in ('bad id', '', '     ', None, 3, 35.7, 'xxx'):
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

    def test_01_user_follow_user_missing_object_id(self):
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

    def test_01_user_follow_dataset_missing_object_id(self):
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

    def test_01_user_follow_user_bad_object_type(self):
        for object_type in ('foobar', 'dataset', '', '     ', None, 3, 35.7):
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

    def test_01_user_follow_dataset_bad_object_type(self):
        for object_type in ('foobar', 'user', '', '     ', None, 3, 35.7):
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

    def test_01_user_follow_user_missing_object_type(self):
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

    def test_01_user_follow_dataset_missing_object_type(self):
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

    def test_02_user_follow_user_by_id(self):
        self._start_following(self.annafan.id, self.annafan.apikey,
                self.russianfan.id, 'user', self.russianfan.id)

    def test_02_user_follow_dataset_by_id(self):
        self._start_following(self.annafan.id, self.annafan.apikey,
                self.warandpeace.id, 'dataset', self.warandpeace.id)

    def test_02_user_follow_user_by_name(self):
        self._start_following(self.annafan.id, self.annafan.apikey,
                self.testsysadmin.id, 'user', self.testsysadmin.name)

    def test_02_user_follow_dataset_by_name(self):
        self._start_following(self.annafan.id, self.annafan.apikey,
                self.annakarenina.id, 'dataset', self.annakarenina.name)

    def test_02_user_follow_user_with_datetime(self):
        'Test that a datetime passed to follower_create is ignored.'
        self._start_following(self.annafan.id, self.annafan.apikey,
                self.joeadmin.id, 'user', self.joeadmin.name,
                datetime_param = str(datetime.datetime.min))

    def test_03_user_follow_user_already_following(self):
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

    def test_03_user_follow_dataset_already_following(self):
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

    def test_03_user_cannot_follow_herself(self):
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
