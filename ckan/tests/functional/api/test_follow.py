import datetime
import paste
import pylons.test
import ckan
from ckan.lib.helpers import json
from ckan.tests import are_foreign_keys_supported, SkipTest

def datetime_from_string(s):
    '''Return a standard datetime.datetime object initialised from a string in
    the same format used for timestamps in dictized activities (the format
    produced by datetime.datetime.isoformat())

    '''
    return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f')

def follow_user(app, follower_id, apikey, object_id, object_arg):
    '''Test a user starting to follow another user via the API.

    :param follower_id: id of the user that will be following something.
    :param apikey: API key of the user that will be following something.
    :param object_id: id of the user that will be followed.
    :param object_arg: the argument to pass to follow_user as the id of
        the object that will be followed, could be the object's id or name.

    '''
    # Record the object's followers count before.
    params = json.dumps({'id': object_id})
    response = app.post('/api/action/user_follower_count',
            params=params).json
    assert response['success'] is True
    follower_count_before = response['result']

    # Record the follower's followees count before.
    params = json.dumps({'id': follower_id})
    response = app.post('/api/action/user_followee_count',
            params=params).json
    assert response['success'] is True
    followee_count_before = response['result']

    # Check that the user is not already following the object.
    params = json.dumps({'id': object_id})
    extra_environ = {'Authorization': str(apikey)}
    response = app.post('/api/action/am_following_user',
            params=params, extra_environ=extra_environ).json
    assert response['success'] is True
    assert response['result'] is False

    # Make the  user start following the object.
    before = datetime.datetime.now()
    params = {'id': object_arg}
    extra_environ = {'Authorization': str(apikey)}
    response = app.post('/api/action/follow_user',
        params=json.dumps(params), extra_environ=extra_environ).json
    after = datetime.datetime.now()
    assert response['success'] is True
    assert response['result']
    follower = response['result']
    assert follower['follower_id'] == follower_id
    assert follower['object_id'] == object_id
    timestamp = datetime_from_string(follower['datetime'])
    assert (timestamp >= before and timestamp <= after), str(timestamp)

    # Check that am_following_user now returns True.
    params = json.dumps({'id': object_id})
    extra_environ = {'Authorization': str(apikey)}
    response = app.post('/api/action/am_following_user',
            params=params, extra_environ=extra_environ).json
    assert response['success'] is True
    assert response['result'] is True

    # Check that the follower appears in the object's list of followers.
    params = json.dumps({'id': object_id})
    response = app.post('/api/action/user_follower_list',
            params=params).json
    assert response['success'] is True
    assert response['result']
    followers = response['result']
    assert len(followers) == follower_count_before + 1
    assert len([follower for follower in followers if follower['id'] == follower_id]) == 1

    # Check that the object appears in the follower's list of followees.
    params = json.dumps({'id': follower_id})
    response = app.post('/api/action/user_followee_list',
            params=params).json
    assert response['success'] is True
    assert response['result']
    followees = response['result']
    assert len(followees) == followee_count_before + 1
    assert len([followee for followee in followees if followee['id'] == object_id]) == 1

    # Check that the object's follower count has increased by 1.
    params = json.dumps({'id': object_id})
    response = app.post('/api/action/user_follower_count',
            params=params).json
    assert response['success'] is True
    assert response['result'] == follower_count_before + 1

    # Check that the follower's followee count has increased by 1.
    params = json.dumps({'id': follower_id})
    response = app.post('/api/action/user_followee_count',
            params=params).json
    assert response['success'] is True
    assert response['result'] == followee_count_before + 1

def follow_dataset(app, follower_id, apikey, dataset_id, dataset_arg):
    '''Test a user starting to follow a dataset via the API.

    :param follower_id: id of the user.
    :param apikey: API key of the user.
    :param dataset_id: id of the dataset.
    :param dataset_arg: the argument to pass to follow_dataset as the id of
        the dataset that will be followed, could be the dataset's id or name.

    '''
    # Record the dataset's followers count before.
    params = json.dumps({'id': dataset_id})
    response = app.post('/api/action/dataset_follower_count',
            params=params).json
    assert response['success'] is True
    follower_count_before = response['result']

    # Record the follower's followees count before.
    params = json.dumps({'id': follower_id})
    response = app.post('/api/action/dataset_followee_count',
            params=params).json
    assert response['success'] is True
    followee_count_before = response['result']

    # Check that the user is not already following the dataset.
    params = json.dumps({'id': dataset_id})
    extra_environ = {'Authorization': str(apikey)}
    response = app.post('/api/action/am_following_dataset',
            params=params, extra_environ=extra_environ).json
    assert response['success'] is True
    assert response['result'] is False

    # Make the  user start following the dataset.
    before = datetime.datetime.now()
    params = {'id': dataset_arg}
    extra_environ = {'Authorization': str(apikey)}
    response = app.post('/api/action/follow_dataset',
        params=json.dumps(params), extra_environ=extra_environ).json
    after = datetime.datetime.now()
    assert response['success'] is True
    assert response['result']
    follower = response['result']
    assert follower['follower_id'] == follower_id
    assert follower['object_id'] == dataset_id
    timestamp = datetime_from_string(follower['datetime'])
    assert (timestamp >= before and timestamp <= after), str(timestamp)

    # Check that am_following_dataset now returns True.
    params = json.dumps({'id': dataset_id})
    extra_environ = {'Authorization': str(apikey)}
    response = app.post('/api/action/am_following_dataset',
            params=params, extra_environ=extra_environ).json
    assert response['success'] is True
    assert response['result'] is True

    # Check that the follower appears in the dataset's list of followers.
    params = json.dumps({'id': dataset_id})
    response = app.post('/api/action/dataset_follower_list',
            params=params).json
    assert response['success'] is True
    assert response['result']
    followers = response['result']
    assert len(followers) == follower_count_before + 1
    assert len([follower for follower in followers if follower['id'] == follower_id]) == 1

    # Check that the dataset appears in the follower's list of followees.
    params = json.dumps({'id': follower_id})
    response = app.post('/api/action/dataset_followee_list',
            params=params).json
    assert response['success'] is True
    assert response['result']
    followees = response['result']
    assert len(followees) == followee_count_before + 1
    assert len([followee for followee in followees if followee['id'] == dataset_id]) == 1

    # Check that the dataset's follower count has increased by 1.
    params = json.dumps({'id': dataset_id})
    response = app.post('/api/action/dataset_follower_count',
            params=params).json
    assert response['success'] is True
    assert response['result'] == follower_count_before + 1

    # Check that the follower's followee count has increased by 1.
    params = json.dumps({'id': follower_id})
    response = app.post('/api/action/dataset_followee_count',
            params=params).json
    assert response['success'] is True
    assert response['result'] == followee_count_before + 1

def follow_group(app, user_id, apikey, group_id, group_arg):
    '''Test a user starting to follow a group via the API.

    :param user_id: id of the user
    :param apikey: API key of the user
    :param group_id: id of the group
    :param group_arg: the argument to pass to follow_group as the id of
        the group that will be followed, could be the group's id or name

    '''
    # Record the group's followers count before.
    params = json.dumps({'id': group_id})
    response = app.post('/api/action/group_follower_count',
            params=params).json
    assert response['success'] is True
    follower_count_before = response['result']

    # Record the user's followees count before.
    params = json.dumps({'id': user_id})
    response = app.post('/api/action/group_followee_count',
            params=params).json
    assert response['success'] is True
    followee_count_before = response['result']

    # Check that the user is not already following the group.
    params = json.dumps({'id': group_id})
    extra_environ = {'Authorization': str(apikey)}
    response = app.post('/api/action/am_following_group',
            params=params, extra_environ=extra_environ).json
    assert response['success'] is True
    assert response['result'] is False

    # Make the  user start following the group.
    before = datetime.datetime.now()
    params = {'id': group_id}
    extra_environ = {'Authorization': str(apikey)}
    response = app.post('/api/action/follow_group',
        params=json.dumps(params), extra_environ=extra_environ).json
    after = datetime.datetime.now()
    assert response['success'] is True
    assert response['result']
    follower = response['result']
    assert follower['follower_id'] == user_id
    assert follower['object_id'] == group_id
    timestamp = datetime_from_string(follower['datetime'])
    assert (timestamp >= before and timestamp <= after), str(timestamp)

    # Check that am_following_group now returns True.
    params = json.dumps({'id': group_id})
    extra_environ = {'Authorization': str(apikey)}
    response = app.post('/api/action/am_following_group',
            params=params, extra_environ=extra_environ).json
    assert response['success'] is True
    assert response['result'] is True

    # Check that the user appears in the group's list of followers.
    params = json.dumps({'id': group_id})
    response = app.post('/api/action/group_follower_list',
            params=params).json
    assert response['success'] is True
    assert response['result']
    followers = response['result']
    assert len(followers) == follower_count_before + 1
    assert len([follower for follower in followers
        if follower['id'] == user_id]) == 1

    # Check that the group appears in the user's list of followees.
    params = json.dumps({'id': user_id})
    response = app.post('/api/action/group_followee_list',
            params=params).json
    assert response['success'] is True
    assert response['result']
    followees = response['result']
    assert len(followees) == followee_count_before + 1
    assert len([followee for followee in followees
        if followee['id'] == group_id]) == 1

    # Check that the group's follower count has increased by 1.
    params = json.dumps({'id': group_id})
    response = app.post('/api/action/group_follower_count',
            params=params).json
    assert response['success'] is True
    assert response['result'] == follower_count_before + 1

    # Check that the user's followee count has increased by 1.
    params = json.dumps({'id': user_id})
    response = app.post('/api/action/group_followee_count',
            params=params).json
    assert response['success'] is True
    assert response['result'] == followee_count_before + 1


class AttributeDict(dict):
    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value


class TestFollow(object):
    '''Tests for the follower API.'''

    @classmethod
    def setup_class(self):
        ckan.tests.CreateTestData.create()
        self.testsysadmin = AttributeDict(
            id = ckan.model.User.get('testsysadmin').id,
            apikey = ckan.model.User.get('testsysadmin').apikey,
            name = ckan.model.User.get('testsysadmin').name,
            )
        self.annafan = AttributeDict({
            'id': ckan.model.User.get('annafan').id,
            'apikey': ckan.model.User.get('annafan').apikey,
            'name': ckan.model.User.get('annafan').name,
            })
        self.russianfan = AttributeDict({
            'id': ckan.model.User.get('russianfan').id,
            'apikey': ckan.model.User.get('russianfan').apikey,
            'name': ckan.model.User.get('russianfan').name,
            })
        self.joeadmin = AttributeDict({
            'id': ckan.model.User.get('joeadmin').id,
            'apikey': ckan.model.User.get('joeadmin').apikey,
            'name': ckan.model.User.get('joeadmin').name,
            })
        self.warandpeace = AttributeDict({
            'id': ckan.model.Package.get('warandpeace').id,
            'name': ckan.model.Package.get('warandpeace').name,
            })
        self.annakarenina = AttributeDict({
            'id': ckan.model.Package.get('annakarenina').id,
            'name': ckan.model.Package.get('annakarenina').name,
            })
        self.rogers_group = AttributeDict({
            'id': ckan.model.Group.get('roger').id,
            'name': ckan.model.Group.get('roger').name,
            })
        self.davids_group = AttributeDict({
            'id': ckan.model.Group.get('david').id,
            'name': ckan.model.Group.get('david').name,
            })
        self.app = paste.fixture.TestApp(pylons.test.pylonsapp)

    @classmethod
    def teardown_class(self):
        ckan.model.repo.rebuild_db()

    def test_01_user_follow_user_bad_apikey(self):
        for apikey in ('bad api key', '', '     ', 'None', '3', '35.7', 'xxx'):
            params = json.dumps({'id': self.russianfan.id})
            extra_environ = {'Authorization': apikey}
            response = self.app.post('/api/action/follow_user',
                params=params, extra_environ=extra_environ, status=403).json
            assert response['success'] is False
            assert response['error']['message'] == 'Access denied'

    def test_01_user_follow_dataset_bad_apikey(self):
        for apikey in ('bad api key', '', '     ', 'None', '3', '35.7', 'xxx'):
            params = json.dumps({'id': self.warandpeace.id})
            extra_environ = {'Authorization': apikey}
            response = self.app.post('/api/action/follow_dataset',
                params=params, extra_environ=extra_environ, status=403).json
            assert response['success'] is False
            assert response['error']['message'] == 'Access denied'

    def test_01_user_follow_group_bad_apikey(self):
        for apikey in ('bad api key', '', '     ', 'None', '3', '35.7', 'xxx'):
            params = json.dumps({'id': self.rogers_group.id})
            extra_environ = {'Authorization': apikey}
            response = self.app.post('/api/action/follow_group',
                params=params, extra_environ=extra_environ, status=403).json
            assert response['success'] is False
            assert response['error']['message'] == 'Access denied'

    def test_01_user_follow_user_missing_apikey(self):
        params = json.dumps({'id': self.russianfan.id})
        response = self.app.post('/api/action/follow_user',
            params=params, status=403).json
        assert response['success'] is False
        assert response['error']['message'] == 'Access denied'

    def test_01_user_follow_dataset_missing_apikey(self):
        params = json.dumps({'id': self.warandpeace.id})
        response = self.app.post('/api/action/follow_dataset',
            params=params, status=403).json
        assert response['success'] is False
        assert response['error']['message'] == 'Access denied'

    def test_01_user_follow_group_missing_apikey(self):
        params = json.dumps({'id': self.rogers_group.id})
        response = self.app.post('/api/action/follow_group',
            params=params, status=403).json
        assert response['success'] is False
        assert response['error']['message'] == 'Access denied'

    def test_01_follow_bad_object_id(self):
        for action in ('follow_user', 'follow_dataset', 'follow_group'):
            for object_id in ('bad id', '     ', 3, 35.7, 'xxx'):
                params = json.dumps({'id': object_id})
                extra_environ = {'Authorization': str(self.annafan.apikey)}
                response = self.app.post('/api/action/{0}'.format(action),
                    params=params, extra_environ=extra_environ,
                    status=409).json
                assert response['success'] is False
                assert response['error']['id'][0].startswith('Not found')

    def test_01_follow_empty_object_id(self):
        for action in ('follow_user', 'follow_dataset', 'follow_group'):
            for object_id in ('', None):
                params = json.dumps({'id': object_id})
                extra_environ = {'Authorization': str(self.annafan.apikey)}
                response = self.app.post('/api/action/{0}'.format(action),
                    params=params, extra_environ=extra_environ,
                    status=409).json
                assert response['success'] is False
                assert response['error']['id'] == ['Missing value']

    def test_01_follow_missing_object_id(self):
        for action in ('follow_user', 'follow_dataset', 'follow_group'):
            params = json.dumps({})
            extra_environ = {'Authorization': str(self.annafan.apikey)}
            response = self.app.post('/api/action/{0}'.format(action),
                params=params, extra_environ=extra_environ, status=409).json
            assert response['success'] is False
            assert response['error']['id'] == ['Missing value']

    def test_02_user_follow_user_by_id(self):
        follow_user(self.app, self.annafan.id, self.annafan.apikey,
                self.russianfan.id, self.russianfan.id)

    def test_02_user_follow_dataset_by_id(self):
        follow_dataset(self.app, self.annafan.id, self.annafan.apikey,
                self.warandpeace.id, self.warandpeace.id)

    def test_02_user_follow_group_by_id(self):
        follow_group(self.app, self.annafan.id, self.annafan.apikey,
                self.rogers_group.id, self.rogers_group.id)

    def test_02_user_follow_user_by_name(self):
        follow_user(self.app, self.annafan.id, self.annafan.apikey,
                self.testsysadmin.id, self.testsysadmin.name)

    def test_02_user_follow_dataset_by_name(self):
        follow_dataset(self.app, self.joeadmin.id, self.joeadmin.apikey,
                self.warandpeace.id, self.warandpeace.name)

    def test_02_user_follow_group_by_name(self):
        follow_group(self.app, self.joeadmin.id, self.joeadmin.apikey,
                self.rogers_group.id, self.rogers_group.name)

    def test_03_user_follow_user_already_following(self):
        for object_id in (self.russianfan.id, self.russianfan.name,
                self.testsysadmin.id, self.testsysadmin.name):
            params = json.dumps({'id': object_id})
            extra_environ = {
                    'Authorization': str(self.annafan.apikey),
                    }
            response = self.app.post('/api/action/follow_user',
                params=params, extra_environ=extra_environ, status=409).json
            assert response['success'] == False
            assert response['error']['message'].startswith(
                    'You are already following ')

    def test_03_user_follow_dataset_already_following(self):
        for object_id in (self.warandpeace.id, self.warandpeace.name):
            params = json.dumps({'id': object_id})
            extra_environ = {
                    'Authorization': str(self.annafan.apikey),
                    }
            response = self.app.post('/api/action/follow_dataset',
                params=params, extra_environ=extra_environ, status=409).json
            assert response['success'] == False
            assert response['error']['message'].startswith(
                    'You are already following ')

    def test_03_user_follow_group_already_following(self):
        for group_id in (self.rogers_group.id, self.rogers_group.name):
            params = json.dumps({'id': group_id})
            extra_environ = {
                    'Authorization': str(self.annafan.apikey),
                    }
            response = self.app.post('/api/action/follow_group',
                params=params, extra_environ=extra_environ, status=409).json
            assert response['success'] is False
            assert response['error']['message'].startswith(
                    'You are already following ')

    def test_03_user_cannot_follow_herself(self):
        params = json.dumps({'id': self.annafan.id})
        extra_environ = {
                'Authorization': str(self.annafan.apikey),
                }
        response = self.app.post('/api/action/follow_user',
            params=params, extra_environ=extra_environ, status=409).json
        assert response['success'] is False
        assert response['error']['message'] == 'You cannot follow yourself'

    def test_04_follower_count_bad_id(self):
        for action in ('user_follower_count', 'dataset_follower_count',
                'group_follower_count'):
            for object_id in ('bad id', '     ', 3, 35.7, 'xxx', ''):
                params = json.dumps({'id': object_id})
                response = self.app.post('/api/action/{0}'.format(action),
                        params=params, status=409).json
                assert response['success'] is False
                assert 'id' in response['error']

    def test_04_follower_count_missing_id(self):
        for action in ('user_follower_count', 'dataset_follower_count',
                'group_follower_count'):
            params = json.dumps({})
            response = self.app.post('/api/action/{0}'.format(action),
                    params=params, status=409).json
            assert response['success'] is False
            assert response['error']['id'] == ['Missing value']

    def test_04_user_follower_count_no_followers(self):
        params = json.dumps({'id': self.annafan.id})
        response = self.app.post('/api/action/user_follower_count',
                params=params).json
        assert response['success'] is True
        assert response['result'] == 0

    def test_04_dataset_follower_count_no_followers(self):
        params = json.dumps({'id': self.annakarenina.id})
        response = self.app.post('/api/action/dataset_follower_count',
                params=params).json
        assert response['success'] is True
        assert response['result'] == 0

    def test_04_group_follower_count_no_followers(self):
        params = json.dumps({'id': self.davids_group.id})
        response = self.app.post('/api/action/group_follower_count',
                params=params).json
        assert response['success'] is True
        assert response['result'] == 0

    def test_04_follower_list_bad_id(self):
        for action in ('user_follower_list', 'dataset_follower_list',
                'group_follower_list'):
            for object_id in ('bad id', '     ', 3, 35.7, 'xxx', ''):
                params = json.dumps({'id': object_id})
                response = self.app.post('/api/action/{0}'.format(action),
                        params=params, status=409).json
                assert response['success'] is False
                assert response['error']['id']

    def test_04_follower_list_missing_id(self):
        for action in ('user_follower_list', 'dataset_follower_list',
                'group_follower_list'):
            params = json.dumps({})
            response = self.app.post('/api/action/{0}'.format(action),
                    params=params, status=409).json
            assert response['success'] is False
            assert response['error']['id'] == ['Missing value']

    def test_04_user_follower_list_no_followers(self):
        params = json.dumps({'id': self.annafan.id})
        response = self.app.post('/api/action/user_follower_list',
                params=params).json
        assert response['success'] is True
        assert response['result'] == []

    def test_04_dataset_follower_list_no_followers(self):
        params = json.dumps({'id': self.annakarenina.id})
        response = self.app.post('/api/action/dataset_follower_list',
                params=params).json
        assert response['success'] is True
        assert response['result'] == []

    def test_04_group_follower_list_no_followers(self):
        params = json.dumps({'id': self.davids_group.id})
        response = self.app.post('/api/action/group_follower_list',
                params=params).json
        assert response['success'] is True
        assert response['result'] == []

    def test_04_am_following_bad_id(self):
        for action in ('am_following_dataset', 'am_following_user',
                'am_following_group'):
            for object_id in ('bad id', '     ', 3, 35.7, 'xxx'):
                params = json.dumps({'id': object_id})
                extra_environ = {'Authorization': str(self.annafan.apikey)}
                response = self.app.post('/api/action/{0}'.format(action),
                        params=params, extra_environ=extra_environ,
                        status=409).json
                assert response['success'] is False
                assert response['error']['id'][0].startswith('Not found: ')

    def test_04_am_following_missing_id(self):
        for action in ('am_following_dataset', 'am_following_user',
                'am_following_group'):
            for id in ('missing', None, ''):
                if id == 'missing':
                    params = json.dumps({})
                else:
                    params = json.dumps({'id':id})
                extra_environ = {'Authorization': str(self.annafan.apikey)}
                response = self.app.post('/api/action/{0}'.format(action),
                        params=params, extra_environ=extra_environ,
                        status=409).json
                assert response['success'] is False
                assert response['error']['id'] == [u'Missing value']

    def test_04_am_following_dataset_bad_apikey(self):
        for apikey in ('bad api key', '', '     ', 'None', '3', '35.7', 'xxx'):
            params = json.dumps({'id': self.warandpeace.id})
            extra_environ = {'Authorization': apikey}
            response = self.app.post('/api/action/am_following_dataset',
                params=params, extra_environ=extra_environ, status=403).json
            assert response['success'] == False
            assert response['error']['message'] == 'Access denied'

    def test_04_am_following_dataset_missing_apikey(self):
        params = json.dumps({'id': self.warandpeace.id})
        response = self.app.post('/api/action/am_following_dataset',
            params=params, status=403).json
        assert response['success'] == False
        assert response['error']['message'] == 'Access denied'

    def test_04_am_following_user_bad_apikey(self):
        for apikey in ('bad api key', '', '     ', 'None', '3', '35.7', 'xxx'):
            params = json.dumps({'id': self.annafan.id})
            extra_environ = {'Authorization': apikey}
            response = self.app.post('/api/action/am_following_user',
                params=params, extra_environ=extra_environ, status=403).json
            assert response['success'] == False
            assert response['error']['message'] == 'Access denied'

    def test_04_am_following_user_missing_apikey(self):
        params = json.dumps({'id': self.annafan.id})
        response = self.app.post('/api/action/am_following_user',
            params=params, status=403).json
        assert response['success'] == False
        assert response['error']['message'] == 'Access denied'

    def test_04_am_following_group_bad_apikey(self):
        for apikey in ('bad api key', '', '     ', 'None', '3', '35.7', 'xxx'):
            params = json.dumps({'id': self.rogers_group.id})
            extra_environ = {'Authorization': apikey}
            response = self.app.post('/api/action/am_following_group',
                params=params, extra_environ=extra_environ, status=403).json
            assert response['success'] == False
            assert response['error']['message'] == 'Access denied'

    def test_04_am_following_group_missing_apikey(self):
        params = json.dumps({'id': self.rogers_group.id})
        response = self.app.post('/api/action/am_following_group',
            params=params, status=403).json
        assert response['success'] == False
        assert response['error']['message'] == 'Access denied'


class TestFollowerDelete(object):
    '''Tests for the unfollow_* APIs.'''

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
        self.rogers_group = ckan.model.Group.get('roger')
        self.davids_group = ckan.model.Group.get('david')
        self.app = paste.fixture.TestApp(pylons.test.pylonsapp)
        follow_user(self.app, self.testsysadmin.id, self.testsysadmin.apikey,
                self.joeadmin.id, self.joeadmin.id)
        follow_user(self.app, self.tester.id, self.tester.apikey,
                self.joeadmin.id, self.joeadmin.id)
        follow_user(self.app, self.russianfan.id, self.russianfan.apikey,
                self.joeadmin.id, self.joeadmin.id)
        follow_user(self.app, self.annafan.id, self.annafan.apikey,
                self.joeadmin.id, self.joeadmin.id)
        follow_user(self.app, self.annafan.id, self.annafan.apikey,
                self.tester.id, self.tester.id)
        follow_dataset(self.app, self.testsysadmin.id,
                self.testsysadmin.apikey, self.warandpeace.id,
                self.warandpeace.id)
        follow_dataset(self.app, self.tester.id, self.tester.apikey,
                self.warandpeace.id, self.warandpeace.id)
        follow_dataset(self.app, self.russianfan.id, self.russianfan.apikey,
                self.warandpeace.id, self.warandpeace.id)
        follow_dataset(self.app, self.annafan.id, self.annafan.apikey,
                self.warandpeace.id, self.warandpeace.id)
        follow_group(self.app, self.annafan.id, self.annafan.apikey,
                self.davids_group.id, self.davids_group.id)

    @classmethod
    def teardown_class(self):
        ckan.model.repo.rebuild_db()

    def test_01_unfollow_user_not_exists(self):
        '''Test the error response when a user tries to unfollow a user that
        she is not following.

        '''
        params = json.dumps({'id': self.russianfan.id})
        extra_environ = {
                'Authorization': str(self.annafan.apikey),
                }
        response = self.app.post('/api/action/unfollow_user',
            params=params, extra_environ=extra_environ, status=404).json
        assert response['success'] == False
        assert response['error']['message'].startswith(
                'Not found: You are not following ')

    def test_01_unfollow_dataset_not_exists(self):
        '''Test the error response when a user tries to unfollow a dataset that
        she is not following.

        '''
        params = json.dumps({'id': self.annakarenina.id})
        extra_environ = {
                'Authorization': str(self.annafan.apikey),
                }
        response = self.app.post('/api/action/unfollow_dataset',
            params=params, extra_environ=extra_environ, status=404).json
        assert response['success'] == False
        assert response['error']['message'].startswith(
                'Not found: You are not following ')

    def test_01_unfollow_group_not_exists(self):
        '''Test the error response when a user tries to unfollow a group that
        she is not following.

        '''
        params = json.dumps({'id': self.rogers_group.id})
        extra_environ = {
                'Authorization': str(self.annafan.apikey),
                }
        response = self.app.post('/api/action/unfollow_group',
            params=params, extra_environ=extra_environ, status=404).json
        assert response['success'] is False
        assert response['error']['message'].startswith(
                'Not found: You are not following ')

    def test_01_unfollow_bad_apikey(self):
        '''Test the error response when a user tries to unfollow something
        but provides a bad API key.

        '''
        for action in ('unfollow_user', 'unfollow_dataset', 'unfollow_group'):
            for apikey in ('bad api key', '', '     ', 'None', '3', '35.7',
                    'xxx'):
                params = json.dumps({
                    'id': self.joeadmin.id,
                    })
                extra_environ = {
                        'Authorization': apikey,
                        }
                response = self.app.post('/api/action/{0}'.format(action),
                    params=params, extra_environ=extra_environ,
                    status=(403,409)).json
                assert response['success'] is False
                assert response['error']['message'] == 'Access denied'

    def test_01_unfollow_missing_apikey(self):
        '''Test error response when calling unfollow_* without api key.'''
        for action in ('unfollow_user', 'unfollow_dataset', 'unfollow_group'):
            params = json.dumps({
                'id': self.joeadmin.id,
                })
            response = self.app.post('/api/action/{0}'.format(action),
                params=params, status=403).json
            assert response['success'] is False
            assert response['error']['message'] == 'Access denied'

    def test_01_unfollow_bad_object_id(self):
        '''Test error response when calling unfollow_* with bad object id.'''
        for action in ('unfollow_user', 'unfollow_dataset', 'unfollow_group'):
            for object_id in ('bad id', '     ', 3, 35.7, 'xxx'):
                params = json.dumps({
                    'id': object_id,
                    })
                extra_environ = {
                        'Authorization': str(self.annafan.apikey),
                        }
                response = self.app.post('/api/action/{0}'.format(action),
                    params=params, extra_environ=extra_environ,
                    status=409).json
                assert response['success'] is False
                assert response['error']['id'][0].startswith('Not found')

    def test_01_unfollow_missing_object_id(self):
        for action in ('unfollow_user', 'unfollow_dataset', 'unfollow_group'):
            for id in ('missing', None, ''):
                if id == 'missing':
                    params = json.dumps({})
                else:
                    params = json.dumps({'id': id})
                extra_environ = {'Authorization': str(self.annafan.apikey)}
                response = self.app.post('/api/action/{0}'.format(action),
                    params=params, extra_environ=extra_environ,
                    status=409).json
                assert response['success'] is False
                assert response['error']['id'] == [u'Missing value']

    def _unfollow_user(self, follower_id, apikey, object_id, object_arg):
        '''Test a user unfollowing a user via the API.

        :param follower_id: id of the follower.
        :param apikey: API key of the follower.
        :param object_id: id of the object to unfollow.
        :param object_arg: the argument to pass to unfollow_user as the id of
            the object to unfollow, could be the object's id or name.

        '''
        # Record the user's number of followers before.
        params = json.dumps({'id': object_id})
        response = self.app.post('/api/action/user_follower_count',
                params=params).json
        assert response['success'] is True
        count_before = response['result']

        # Check that the user is following the object.
        params = json.dumps({'id': object_id})
        extra_environ = {'Authorization': str(apikey)}
        response = self.app.post('/api/action/am_following_user',
                params=params, extra_environ=extra_environ).json
        assert response['success'] is True
        assert response['result'] is True

        # Make the user unfollow the object.
        params = {
            'id': object_arg,
            }
        extra_environ = {'Authorization': str(apikey)}
        response = self.app.post('/api/action/unfollow_user',
            params=json.dumps(params), extra_environ=extra_environ).json
        assert response['success'] is True

        # Check that am_following_user now returns False.
        params = json.dumps({'id': object_id})
        extra_environ = {'Authorization': str(apikey)}
        response = self.app.post('/api/action/am_following_user',
                params=params, extra_environ=extra_environ).json
        assert response['success'] is True
        assert response['result'] is False

        # Check that the user doesn't appear in the object's list of followers.
        params = json.dumps({'id': object_id})
        response = self.app.post('/api/action/user_follower_list',
                params=params).json
        assert response['success'] is True
        assert response['result']
        followers = response['result']
        assert len([follower for follower in followers if follower['id'] ==
                follower_id]) == 0

        # Check that the object's follower count has decreased by 1.
        params = json.dumps({'id': object_id})
        response = self.app.post('/api/action/user_follower_count',
                params=params).json
        assert response['success'] is True
        assert response['result'] == count_before - 1

    def _unfollow_dataset(self, user_id, apikey, dataset_id, dataset_arg):
        '''Test a user unfollowing a dataset via the API.

        :param user_id: id of the follower.
        :param apikey: API key of the follower.
        :param dataset_id: id of the object to unfollow.
        :param dataset_arg: the argument to pass to unfollow_dataset as the id
            of the object to unfollow, could be the object's id or name.

        '''
        # Record the dataset's number of followers before.
        params = json.dumps({'id': dataset_id})
        response = self.app.post('/api/action/dataset_follower_count',
                params=params).json
        assert response['success'] is True
        count_before = response['result']

        # Check that the user is following the dataset.
        params = json.dumps({'id': dataset_id})
        extra_environ = {'Authorization': str(apikey)}
        response = self.app.post('/api/action/am_following_dataset',
                params=params, extra_environ=extra_environ).json
        assert response['success'] is True
        assert response['result'] is True

        # Make the user unfollow the dataset.
        params = {
            'id': dataset_arg,
            }
        extra_environ = {'Authorization': str(apikey)}
        response = self.app.post('/api/action/unfollow_dataset',
            params=json.dumps(params), extra_environ=extra_environ).json
        assert response['success'] is True

        # Check that am_following_dataset now returns False.
        params = json.dumps({'id': dataset_id})
        extra_environ = {'Authorization': str(apikey)}
        response = self.app.post('/api/action/am_following_dataset',
                params=params, extra_environ=extra_environ).json
        assert response['success'] is True
        assert response['result'] is False

        # Check that the user doesn't appear in the dataset's list of
        # followers.
        params = json.dumps({'id': dataset_id})
        response = self.app.post('/api/action/dataset_follower_list',
                params=params).json
        assert response['success'] is True
        assert response['result']
        followers = response['result']
        assert len([follower for follower in followers if follower['id'] ==
                user_id]) == 0

        # Check that the dataset's follower count has decreased by 1.
        params = json.dumps({'id': dataset_id})
        response = self.app.post('/api/action/dataset_follower_count',
                params=params).json
        assert response['success'] is True
        assert response['result'] == count_before - 1

    def _unfollow_group(self, user_id, apikey, group_id, group_arg):
        '''Test a user unfollowing a group via the API.

        :param user_id: id of the user
        :param apikey: API key of the user
        :param group_id: id of the group
        :param group_arg: the argument to pass to unfollow_group as the id
            of the group, could be the group's id or name.

        '''
        # Record the group's number of followers before.
        params = json.dumps({'id': group_id})
        response = self.app.post('/api/action/group_follower_count',
                params=params).json
        assert response['success'] is True
        count_before = response['result']

        # Check that the user is following the group.
        params = json.dumps({'id': group_id})
        extra_environ = {'Authorization': str(apikey)}
        response = self.app.post('/api/action/am_following_group',
                params=params, extra_environ=extra_environ).json
        assert response['success'] is True
        assert response['result'] is True

        # Make the user unfollow the group.
        params = {
            'id': group_arg,
            }
        extra_environ = {'Authorization': str(apikey)}
        response = self.app.post('/api/action/unfollow_group',
            params=json.dumps(params), extra_environ=extra_environ).json
        assert response['success'] is True

        # Check that am_following_group now returns False.
        params = json.dumps({'id': group_id})
        extra_environ = {'Authorization': str(apikey)}
        response = self.app.post('/api/action/am_following_group',
                params=params, extra_environ=extra_environ).json
        assert response['success'] is True
        assert response['result'] is False

        # Check that the user doesn't appear in the group's list of
        # followers.
        params = json.dumps({'id': group_id})
        response = self.app.post('/api/action/group_follower_list',
                params=params).json
        assert response['success'] is True
        assert 'result' in response
        followers = response['result']
        assert len([follower for follower in followers if follower['id'] ==
                user_id]) == 0

        # Check that the group's follower count has decreased by 1.
        params = json.dumps({'id': group_id})
        response = self.app.post('/api/action/group_follower_count',
                params=params).json
        assert response['success'] is True
        assert response['result'] == count_before - 1

    def test_02_follower_delete_by_id(self):
        self._unfollow_user(self.annafan.id, self.annafan.apikey,
                self.joeadmin.id, self.joeadmin.id)
        self._unfollow_dataset(self.annafan.id, self.annafan.apikey,
                self.warandpeace.id, self.warandpeace.id)
        self._unfollow_group(self.annafan.id, self.annafan.apikey,
                self.davids_group.id, self.davids_group.id)

class TestFollowerCascade(object):
    '''Tests for on delete cascade of follower table rows.'''

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

        follow_user(self.app, self.joeadmin.id, self.joeadmin.apikey,
                self.testsysadmin.id, self.testsysadmin.id)

        follow_user(self.app, self.annafan.id, self.annafan.apikey,
                self.testsysadmin.id, self.testsysadmin.id)
        follow_user(self.app, self.russianfan.id, self.russianfan.apikey,
                self.testsysadmin.id, self.testsysadmin.id)

        follow_dataset(self.app, self.joeadmin.id, self.joeadmin.apikey,
                self.annakarenina.id, self.annakarenina.id)

        follow_dataset(self.app, self.annafan.id, self.annafan.apikey,
                self.annakarenina.id, self.annakarenina.id)
        follow_dataset(self.app, self.russianfan.id, self.russianfan.apikey,
                self.annakarenina.id, self.annakarenina.id)

        follow_user(self.app, self.tester.id, self.tester.apikey,
                self.joeadmin.id, self.joeadmin.id)

        follow_dataset(self.app, self.testsysadmin.id,
                self.testsysadmin.apikey, self.warandpeace.id,
                self.warandpeace.id)

        session = ckan.model.Session()
        session.delete(self.joeadmin)
        session.commit()

        session.delete(self.warandpeace)
        session.commit()

    @classmethod
    def teardown_class(self):
        ckan.model.repo.rebuild_db()

    def test_01_on_delete_cascade_api(self):
        '''
        Test that UserFollowingUser and UserFollowingDataset rows cascade.


        '''
        # It should no longer be possible to get joeadmin's follower list.
        params = json.dumps({'id': 'joeadmin'})
        response = self.app.post('/api/action/user_follower_list',
                params=params, status=409).json
        assert response['success'] is False
        assert response['error'].has_key('id')

        # It should no longer be possible to get warandpeace's follower list.
        params = json.dumps({'id': 'warandpeace'})
        response = self.app.post('/api/action/dataset_follower_list',
                params=params, status=409).json
        assert response['success'] is False
        assert response['error'].has_key('id')

        # It should no longer be possible to get joeadmin's follower count.
        params = json.dumps({'id': 'joeadmin'})
        response = self.app.post('/api/action/user_follower_count',
                params=params, status=409).json
        assert response['success'] is False
        assert response['error'].has_key('id')

        # It should no longer be possible to get warandpeace's follower count.
        params = json.dumps({'id': 'warandpeace'})
        response = self.app.post('/api/action/dataset_follower_count',
                params=params, status=409).json
        assert response['success'] is False
        assert response['error'].has_key('id')

        # It should no longer be possible to get am_following for joeadmin.
        params = json.dumps({'id': 'joeadmin'})
        extra_environ = {'Authorization': str(self.testsysadmin.apikey)}
        response = self.app.post('/api/action/am_following_user',
                params=params, extra_environ=extra_environ, status=409).json
        assert response['success'] is False
        assert response['error'].has_key('id')

        # It should no longer be possible to get am_following for warandpeace.
        params = json.dumps({'id': 'warandpeace'})
        extra_environ = {'Authorization': str(self.testsysadmin.apikey)}
        response = self.app.post('/api/action/am_following_dataset',
                params=params, extra_environ=extra_environ, status=409).json
        assert response['success'] is False
        assert response['error'].has_key('id')

        # It should no longer be possible to unfollow joeadmin.
        params = json.dumps({'id': 'joeadmin'})
        extra_environ = {'Authorization': str(self.tester.apikey)}
        response = self.app.post('/api/action/unfollow_user',
                params=params, extra_environ=extra_environ, status=409).json
        assert response['success'] is False
        assert response['error']['id'] == ['Not found: User']

        # It should no longer be possible to unfollow warandpeace.
        params = json.dumps({'id': 'warandpeace'})
        extra_environ = {'Authorization': str(self.testsysadmin.apikey)}
        response = self.app.post('/api/action/unfollow_dataset',
                params=params, extra_environ=extra_environ, status=409).json
        assert response['success'] is False
        assert response['error']['id'] == ['Not found: Dataset']

        # It should no longer be possible to follow joeadmin.
        params = json.dumps({'id': 'joeadmin'})
        extra_environ = {'Authorization': str(self.annafan.apikey)}
        response = self.app.post('/api/action/follow_user',
                params=params, extra_environ=extra_environ, status=409).json
        assert response['success'] is False
        assert response['error'].has_key('id')

        # It should no longer be possible to follow warandpeace.
        params = json.dumps({'id': 'warandpeace'})
        extra_environ = {'Authorization': str(self.annafan.apikey)}
        response = self.app.post('/api/action/follow_dataset',
                params=params, extra_environ=extra_environ, status=409).json
        assert response['success'] is False
        assert response['error'].has_key('id')

        # Users who joeadmin was following should no longer have him in their
        # follower list.
        params = json.dumps({'id': self.testsysadmin.id})
        response = self.app.post('/api/action/user_follower_list',
                params=params).json
        assert response['success'] is True
        followers = [follower['name'] for follower in response['result']]
        assert 'joeadmin' not in followers

        # Datasets who joeadmin was following should no longer have him in
        # their follower list.
        params = json.dumps({'id': self.annakarenina.id})
        response = self.app.post('/api/action/dataset_follower_list',
                params=params).json
        assert response['success'] is True
        followers = [follower['name'] for follower in response['result']]
        assert 'joeadmin' not in followers

    def test_02_on_delete_cascade_db(self):
        if not are_foreign_keys_supported():
            raise SkipTest("Search not supported")

        # After the previous test above there should be no rows with joeadmin's
        # id in the UserFollowingUser or UserFollowingDataset tables.
        from ckan.model import UserFollowingUser, UserFollowingDataset
        session = ckan.model.Session()

        query = session.query(UserFollowingUser)
        query = query.filter(UserFollowingUser.follower_id==self.joeadmin.id)
        assert query.count() == 0

        query = session.query(UserFollowingUser)
        query = query.filter(UserFollowingUser.object_id==self.joeadmin.id)
        assert query.count() == 0

        query = session.query(UserFollowingDataset)
        query = query.filter(UserFollowingUser.follower_id==self.joeadmin.id)
        assert query.count() == 0

        # There should be no rows with warandpeace's id either.
        query = session.query(UserFollowingUser)
        query = query.filter(UserFollowingUser.object_id==self.warandpeace.id)
        assert query.count() == 0

        query = session.query(UserFollowingDataset)
        query = query.filter(UserFollowingUser.object_id==self.warandpeace.id)
        assert query.count() == 0
