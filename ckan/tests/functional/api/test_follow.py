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
        self.warandpeace = ckan.model.Package.get('warandpeace')
        self.annakarenina = ckan.model.Package.get('annakarenina')
        self.app = paste.fixture.TestApp(pylons.test.pylonsapp)

    @classmethod
    def teardown_class(self):
        ckan.model.repo.rebuild_db()

    def _user_follow_user(self, follower_id, follower_api_key, object_id):
        '''Test a user starting to follow another user via the API.'''

        # Record the user's number of followers before.
        params = json.dumps({'id': object_id})
        response = self.app.post('/api/action/follower_count',
                params=params).json
        assert response['success'] is True
        count_before = response['result']

        # Make one user start following another user.
        before = datetime.datetime.now()
        params = json.dumps({
            'object_id': object_id,
            'object_type': 'user',
            })
        extra_environ = {
                'Authorization': str(follower_api_key)
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
        assert follower['object_type'] == 'user'
        timestamp = datetime_from_string(follower['datetime'])
        assert (timestamp >= before and timestamp <= after), str(timestamp)

        # Check that the follower appears in the user's list of followers.
        params = json.dumps({'id': object_id})
        response = self.app.post('/api/action/follower_list',
                params=params).json
        assert response['success'] is True
        assert response['result']
        followers = response['result']
        assert len(followers) == 1
        follower = followers[0]
        assert follower['id'] == follower_id

        # Check that the user's follower count has increased by 1.
        params = json.dumps({'id': object_id})
        response = self.app.post('/api/action/follower_count',
                params=params).json
        assert response['success'] is True
        assert response['result'] == count_before + 1

    def test_user_follow_user(self):
        self._user_follow_user(self.annafan.id, self.annafan.apikey,
                self.russianfan.id)

    def test_user_follow_user_by_name(self):
        self._user_follow_user(self.annafan.id, self.annafan.apikey,
                self.russianfan.name)

    def test_user_follow_dataset(self):
        '''Test a user following a dataset via the API.'''
        raise NotImplementedError

    def test_follower_id_bad(self):
        raise NotImplementedError

    def test_follower_id_missing(self):
        raise NotImplementedError

    def test_follower_type_bad(self):
        raise NotImplementedError

    def test_follower_type_missing(self):
        raise NotImplementedError

    def test_object_id_bad(self):
        raise NotImplementedError

    def test_object_id_missing(self):
        raise NotImplementedError

    def test_object_type_bad(self):
        raise NotImplementedError

    def test_object_type_missing(self):
        raise NotImplementedError

    def test_follow_with_datetime(self):
        raise NotImplementedError

    def test_follow_already_exists(self):
        raise NotImplementedError

    def test_follow_not_logged_in(self):
        raise NotImplementedError

    def test_follow_not_authorized(self):
        raise NotImplementedError
