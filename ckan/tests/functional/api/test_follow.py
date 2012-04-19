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

    def test_user_follow_user(self):
        '''Test a user following another user via the API.'''

        # TODO: Test following and retrieving followers by name as well as by ID.

        # Make one user a follower of another user.
        before = datetime.datetime.now()
        params = json.dumps({
            'follower_id': self.annafan.id,
            'follower_type': 'user',
            'followee_id': self.russianfan.id,
            'followee_type': 'user',
            })
        extra_environ = {
                'Authorization': str(self.annafan.apikey)
                }
        response = self.app.post('/api/action/follower_create',
            params=params, extra_environ=extra_environ)
        after = datetime.datetime.now()
        assert not response.errors
        response = response.json
        assert response['success'] is True
        assert response['result']
        follower = response['result']
        assert follower['follower_id'] == self.annafan.id
        assert follower['follower_type'] == 'user'
        assert follower['followee_id'] == self.russianfan.id
        assert follower['followee_type'] == 'user'
        timestamp = datetime_from_string(follower['datetime'])
        assert (timestamp >= before and timestamp <= after), str(timestamp)

        # Check that the follower appears in the followee's list of followers.
        params = json.dumps({'id': self.russianfan.id})
        response = self.app.post('/api/action/user_follower_list',
                params=params)
        assert not response.errors
        response = response.json
        assert response['success'] is True
        assert response['result']
        followers = response['result']
        assert len(followers) == 1
        follower = followers[0]
        assert follower['follower_id'] == self.annafan.id
        assert follower['follower_type'] == 'user'
        assert follower['followee_id'] == self.russianfan.id
        assert follower['followee_type'] == 'user'
        timestamp = datetime_from_string(follower['datetime'])
        assert (timestamp >= before and timestamp <= after), str(timestamp)

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

    def test_followee_id_bad(self):
        raise NotImplementedError

    def test_followee_id_missing(self):
        raise NotImplementedError

    def test_followee_type_bad(self):
        raise NotImplementedError

    def test_followee_type_missing(self):
        raise NotImplementedError

    def test_follow_with_datetime(self):
        raise NotImplementedError

    def test_follow_already_exists(self):
        raise NotImplementedError

    def test_follow_not_logged_in(self):
        raise NotImplementedError

    def test_follow_not_authorized(self):
        raise NotImplementedError
