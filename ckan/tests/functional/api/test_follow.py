'''Test for the follower API.

This module tests following, unfollowing, getting a list of what you're
following or the number of things you're following, getting a list of who's
following you or the number of followers you have, testing whether or not
you're following something, etc.

This module _does not_ test the user dashboard activity stream (which shows
activities from everything you're following), that is tested in
test_dashboard.py.

'''
import datetime
import paste
import pylons.test
import ckan
from ckan.tests import are_foreign_keys_supported, SkipTest
import ckan.tests

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
    follower_count_before = ckan.tests.call_action_api(app,
            'user_follower_count', id=object_id)

    # Record the follower's followees count before.
    followee_count_before = ckan.tests.call_action_api(app,
            'user_followee_count', id=follower_id)

    # Check that the user is not already following the object.
    result = ckan.tests.call_action_api(app, 'am_following_user',
            id=object_id, apikey=apikey)
    assert result is False

    # Make the  user start following the object.
    before = datetime.datetime.now()
    follower = ckan.tests.call_action_api(app, 'follow_user', id=object_arg,
            apikey=apikey)
    after = datetime.datetime.now()
    assert follower['follower_id'] == follower_id
    assert follower['object_id'] == object_id
    timestamp = datetime_from_string(follower['datetime'])
    assert (timestamp >= before and timestamp <= after), str(timestamp)

    # Check that am_following_user now returns True.
    result = ckan.tests.call_action_api(app, 'am_following_user',
            id=object_id, apikey=apikey)
    assert result is True

    # Check that the follower appears in the object's list of followers.
    followers = ckan.tests.call_action_api(app, 'user_follower_list',
            id=object_id)
    assert len(followers) == follower_count_before + 1
    assert len([follower for follower in followers if follower['id'] == follower_id]) == 1

    # Check that the object appears in the follower's list of followees.
    followees = ckan.tests.call_action_api(app, 'user_followee_list',
            id=follower_id)
    assert len(followees) == followee_count_before + 1
    assert len([followee for followee in followees if followee['id'] == object_id]) == 1

    # Check that the object's follower count has increased by 1.
    follower_count_after = ckan.tests.call_action_api(app,
            'user_follower_count', id=object_id)
    assert follower_count_after == follower_count_before + 1

    # Check that the follower's followee count has increased by 1.
    followee_count_after = ckan.tests.call_action_api(app,
            'user_followee_count', id=follower_id)
    assert followee_count_after == followee_count_before + 1

def follow_dataset(app, follower_id, apikey, dataset_id, dataset_arg):
    '''Test a user starting to follow a dataset via the API.

    :param follower_id: id of the user.
    :param apikey: API key of the user.
    :param dataset_id: id of the dataset.
    :param dataset_arg: the argument to pass to follow_dataset as the id of
        the dataset that will be followed, could be the dataset's id or name.

    '''
    # Record the dataset's followers count before.
    follower_count_before = ckan.tests.call_action_api(app,
            'dataset_follower_count', id=dataset_id)

    # Record the follower's followees count before.
    followee_count_before = ckan.tests.call_action_api(app,
            'dataset_followee_count', id=follower_id)

    # Check that the user is not already following the dataset.
    result = ckan.tests.call_action_api(app, 'am_following_dataset',
            id=dataset_id, apikey=apikey)
    assert result is False

    # Make the  user start following the dataset.
    before = datetime.datetime.now()
    follower = ckan.tests.call_action_api(app, 'follow_dataset',
            id=dataset_arg, apikey=apikey)
    after = datetime.datetime.now()
    assert follower['follower_id'] == follower_id
    assert follower['object_id'] == dataset_id
    timestamp = datetime_from_string(follower['datetime'])
    assert (timestamp >= before and timestamp <= after), str(timestamp)

    # Check that am_following_dataset now returns True.
    result = ckan.tests.call_action_api(app, 'am_following_dataset',
            id=dataset_id, apikey=apikey)
    assert result is True

    # Check that the follower appears in the dataset's list of followers.
    followers = ckan.tests.call_action_api(app, 'dataset_follower_list',
            id=dataset_id)
    assert len(followers) == follower_count_before + 1
    assert len([follower for follower in followers if follower['id'] == follower_id]) == 1

    # Check that the dataset appears in the follower's list of followees.
    followees = ckan.tests.call_action_api(app, 'dataset_followee_list',
            id=follower_id)
    assert len(followees) == followee_count_before + 1
    assert len([followee for followee in followees if followee['id'] == dataset_id]) == 1

    # Check that the dataset's follower count has increased by 1.
    follower_count_after = ckan.tests.call_action_api(app,
            'dataset_follower_count', id=dataset_id)
    assert follower_count_after == follower_count_before + 1

    # Check that the follower's followee count has increased by 1.
    followee_count_after = ckan.tests.call_action_api(app,
            'dataset_followee_count', id=follower_id)
    assert followee_count_after == followee_count_before + 1

def follow_group(app, user_id, apikey, group_id, group_arg):
    '''Test a user starting to follow a group via the API.

    :param user_id: id of the user
    :param apikey: API key of the user
    :param group_id: id of the group
    :param group_arg: the argument to pass to follow_group as the id of
        the group that will be followed, could be the group's id or name

    '''
    # Record the group's followers count before.
    follower_count_before = ckan.tests.call_action_api(app,
            'group_follower_count', id=group_id)

    # Record the user's followees count before.
    followee_count_before = ckan.tests.call_action_api(app,
            'group_followee_count', id=user_id)

    # Check that the user is not already following the group.
    result = ckan.tests.call_action_api(app, 'am_following_group',
            id=group_id, apikey=apikey)
    assert result is False

    # Make the  user start following the group.
    before = datetime.datetime.now()
    follower = ckan.tests.call_action_api(app, 'follow_group', id=group_id,
            apikey=apikey)
    after = datetime.datetime.now()
    assert follower['follower_id'] == user_id
    assert follower['object_id'] == group_id
    timestamp = datetime_from_string(follower['datetime'])
    assert (timestamp >= before and timestamp <= after), str(timestamp)

    # Check that am_following_group now returns True.
    result = ckan.tests.call_action_api(app, 'am_following_group',
            id=group_id, apikey=apikey)
    assert result is True

    # Check that the user appears in the group's list of followers.
    followers = ckan.tests.call_action_api(app, 'group_follower_list',
            id=group_id)
    assert len(followers) == follower_count_before + 1
    assert len([follower for follower in followers
        if follower['id'] == user_id]) == 1

    # Check that the group appears in the user's list of followees.
    followees = ckan.tests.call_action_api(app, 'group_followee_list',
            id=user_id)
    assert len(followees) == followee_count_before + 1
    assert len([followee for followee in followees
        if followee['id'] == group_id]) == 1

    # Check that the group's follower count has increased by 1.
    follower_count_after = ckan.tests.call_action_api(app,
            'group_follower_count', id=group_id)
    assert follower_count_after == follower_count_before + 1

    # Check that the user's followee count has increased by 1.
    followee_count_after = ckan.tests.call_action_api(app,
            'group_followee_count', id=user_id)
    assert followee_count_after == followee_count_before + 1


class TestFollow(object):
    '''Tests for the follower API.'''

    @classmethod
    def setup_class(self):
        ckan.tests.CreateTestData.create()
        self.testsysadmin = {
                'id': ckan.model.User.get('testsysadmin').id,
                'apikey': ckan.model.User.get('testsysadmin').apikey,
                'name': ckan.model.User.get('testsysadmin').name,
                }
        self.annafan = {
            'id': ckan.model.User.get('annafan').id,
            'apikey': ckan.model.User.get('annafan').apikey,
            'name': ckan.model.User.get('annafan').name,
            }
        self.russianfan = {
            'id': ckan.model.User.get('russianfan').id,
            'apikey': ckan.model.User.get('russianfan').apikey,
            'name': ckan.model.User.get('russianfan').name,
            }
        self.joeadmin = {
            'id': ckan.model.User.get('joeadmin').id,
            'apikey': ckan.model.User.get('joeadmin').apikey,
            'name': ckan.model.User.get('joeadmin').name,
            }
        self.warandpeace = {
            'id': ckan.model.Package.get('warandpeace').id,
            'name': ckan.model.Package.get('warandpeace').name,
            }
        self.annakarenina = {
            'id': ckan.model.Package.get('annakarenina').id,
            'name': ckan.model.Package.get('annakarenina').name,
            }
        self.rogers_group = {
            'id': ckan.model.Group.get('roger').id,
            'name': ckan.model.Group.get('roger').name,
            }
        self.davids_group = {
            'id': ckan.model.Group.get('david').id,
            'name': ckan.model.Group.get('david').name,
            }
        self.app = paste.fixture.TestApp(pylons.test.pylonsapp)

    @classmethod
    def teardown_class(self):
        ckan.model.repo.rebuild_db()

    def test_01_user_follow_user_bad_apikey(self):
        for apikey in ('bad api key', '', '     ', 'None', '3', '35.7', 'xxx'):
            error = ckan.tests.call_action_api(self.app, 'follow_user',
                    id=self.russianfan['id'], apikey=apikey,
                    status=403)
            assert error['message'] == 'Access denied'

    def test_01_user_follow_dataset_bad_apikey(self):
        for apikey in ('bad api key', '', '     ', 'None', '3', '35.7', 'xxx'):
            error = ckan.tests.call_action_api(self.app, 'follow_dataset',
                    id=self.warandpeace['id'], apikey=apikey,
                    status=403)
            assert error['message'] == 'Access denied'

    def test_01_user_follow_group_bad_apikey(self):
        for apikey in ('bad api key', '', '     ', 'None', '3', '35.7', 'xxx'):
            error = ckan.tests.call_action_api(self.app, 'follow_group',
                    id=self.rogers_group['id'], apikey=apikey,
                    status=403)
            assert error['message'] == 'Access denied'

    def test_01_user_follow_user_missing_apikey(self):
        error = ckan.tests.call_action_api(self.app, 'follow_user',
                id=self.russianfan['id'], status=403)
        assert error['message'] == 'Access denied'

    def test_01_user_follow_dataset_missing_apikey(self):
        error = ckan.tests.call_action_api(self.app, 'follow_dataset',
                id=self.warandpeace['id'], status=403)
        assert error['message'] == 'Access denied'

    def test_01_user_follow_group_missing_apikey(self):
        error = ckan.tests.call_action_api(self.app, 'follow_group',
                id=self.rogers_group['id'], status=403)
        assert error['message'] == 'Access denied'

    def test_01_follow_bad_object_id(self):
        for action in ('follow_user', 'follow_dataset', 'follow_group'):
            for object_id in ('bad id', '     ', 3, 35.7, 'xxx'):
                error = ckan.tests.call_action_api(self.app, action,
                        id=object_id,
                        apikey=self.annafan['apikey'], status=409)
                assert error['id'][0].startswith('Not found')

    def test_01_follow_empty_object_id(self):
        for action in ('follow_user', 'follow_dataset', 'follow_group'):
            for object_id in ('', None):
                error = ckan.tests.call_action_api(self.app, action,
                        id=object_id,
                        apikey=self.annafan['apikey'], status=409)
                assert error['id'] == ['Missing value']

    def test_01_follow_missing_object_id(self):
        for action in ('follow_user', 'follow_dataset', 'follow_group'):
            error = ckan.tests.call_action_api(self.app, action,
                    apikey=self.annafan['apikey'], status=409)
            assert error['id'] == ['Missing value']

    def test_02_user_follow_user_by_id(self):
        follow_user(self.app, self.annafan['id'], self.annafan['apikey'],
                self.russianfan['id'], self.russianfan['id'])

    def test_02_user_follow_dataset_by_id(self):
        follow_dataset(self.app, self.annafan['id'], self.annafan['apikey'],
                self.warandpeace['id'], self.warandpeace['id'])

    def test_02_user_follow_group_by_id(self):
        follow_group(self.app, self.annafan['id'], self.annafan['apikey'],
                self.rogers_group['id'], self.rogers_group['id'])

    def test_02_user_follow_user_by_name(self):
        follow_user(self.app, self.annafan['id'], self.annafan['apikey'],
                self.testsysadmin['id'], self.testsysadmin['name'])

    def test_02_user_follow_dataset_by_name(self):
        follow_dataset(self.app, self.joeadmin['id'], self.joeadmin['apikey'],
                self.warandpeace['id'], self.warandpeace['name'])

    def test_02_user_follow_group_by_name(self):
        follow_group(self.app, self.joeadmin['id'], self.joeadmin['apikey'],
                self.rogers_group['id'], self.rogers_group['name'])

    def test_03_user_follow_user_already_following(self):
        for object_id in (self.russianfan['id'], self.russianfan['name'],
                self.testsysadmin['id'], self.testsysadmin['name']):
            error = ckan.tests.call_action_api(self.app, 'follow_user',
                    id=object_id, apikey=self.annafan['apikey'],
                    status=409)
            assert error['message'].startswith('You are already following ')

    def test_03_user_follow_dataset_already_following(self):
        for object_id in (self.warandpeace['id'], self.warandpeace['name']):
            error = ckan.tests.call_action_api(self.app, 'follow_dataset',
                    id=object_id, apikey=self.annafan['apikey'],
                    status=409)
            assert error['message'].startswith('You are already following ')

    def test_03_user_follow_group_already_following(self):
        for group_id in (self.rogers_group['id'], self.rogers_group['name']):
            error = ckan.tests.call_action_api(self.app, 'follow_group',
                    id=group_id, apikey=self.annafan['apikey'],
                    status=409)
            assert error['message'].startswith('You are already following ')

    def test_03_user_cannot_follow_herself(self):
        error = ckan.tests.call_action_api(self.app, 'follow_user',
                apikey=self.annafan['apikey'], status=409,
                id=self.annafan['id'])
        assert error['message'] == 'You cannot follow yourself'

    def test_04_follower_count_bad_id(self):
        for action in ('user_follower_count', 'dataset_follower_count',
                'group_follower_count'):
            for object_id in ('bad id', '     ', 3, 35.7, 'xxx', ''):
                error = ckan.tests.call_action_api(self.app, action,
                        status=409, id=object_id)
                assert 'id' in error

    def test_04_follower_count_missing_id(self):
        for action in ('user_follower_count', 'dataset_follower_count',
                'group_follower_count'):
            error = ckan.tests.call_action_api(self.app, action, status=409)
            assert error['id'] == ['Missing value']

    def test_04_user_follower_count_no_followers(self):
        follower_count = ckan.tests.call_action_api(self.app,
                'user_follower_count', id=self.annafan['id'])
        assert follower_count == 0

    def test_04_dataset_follower_count_no_followers(self):
        follower_count = ckan.tests.call_action_api(self.app,
                'dataset_follower_count', id=self.annakarenina['id'])
        assert follower_count == 0

    def test_04_group_follower_count_no_followers(self):
        follower_count = ckan.tests.call_action_api(self.app,
                'group_follower_count', id=self.davids_group['id'])
        assert follower_count == 0

    def test_04_follower_list_bad_id(self):
        for action in ('user_follower_list', 'dataset_follower_list',
                'group_follower_list'):
            for object_id in ('bad id', '     ', 3, 35.7, 'xxx', ''):
                error = ckan.tests.call_action_api(self.app, action,
                        status=409, id=object_id)
                assert error['id']

    def test_04_follower_list_missing_id(self):
        for action in ('user_follower_list', 'dataset_follower_list',
                'group_follower_list'):
            error = ckan.tests.call_action_api(self.app, action, status=409)
            assert error['id'] == ['Missing value']

    def test_04_user_follower_list_no_followers(self):
        followers = ckan.tests.call_action_api(self.app, 'user_follower_list',
                id=self.annafan['id'])
        assert followers == []

    def test_04_dataset_follower_list_no_followers(self):
        followers = ckan.tests.call_action_api(self.app,
                'dataset_follower_list', id=self.annakarenina['id'])
        assert followers == []

    def test_04_group_follower_list_no_followers(self):
        followers = ckan.tests.call_action_api(self.app, 'group_follower_list',
                id=self.davids_group['id'])
        assert followers == []

    def test_04_am_following_bad_id(self):
        for action in ('am_following_dataset', 'am_following_user',
                'am_following_group'):
            for object_id in ('bad id', '     ', 3, 35.7, 'xxx'):
                error = ckan.tests.call_action_api(self.app, action,
                    apikey=self.annafan['apikey'], status=409, id=object_id)
                assert error['id'][0].startswith('Not found: ')

    def test_04_am_following_missing_id(self):
        for action in ('am_following_dataset', 'am_following_user',
                'am_following_group'):
            for id in ('missing', None, ''):
                if id == 'missing':
                    error = ckan.tests.call_action_api(self.app, action,
                            apikey=self.annafan['apikey'], status=409)
                else:
                    error = ckan.tests.call_action_api(self.app, action,
                            apikey=self.annafan['apikey'], status=409, id=id)
                assert error['id'] == [u'Missing value']

    def test_04_am_following_dataset_bad_apikey(self):
        for apikey in ('bad api key', '', '     ', 'None', '3', '35.7', 'xxx'):
            error = ckan.tests.call_action_api(self.app,
                    'am_following_dataset', apikey=apikey, status=403,
                    id=self.warandpeace['id'])
            assert error['message'] == 'Access denied'

    def test_04_am_following_dataset_missing_apikey(self):
        error = ckan.tests.call_action_api(self.app, 'am_following_dataset',
                status=403, id=self.warandpeace['id'])
        assert error['message'] == 'Access denied'

    def test_04_am_following_user_bad_apikey(self):
        for apikey in ('bad api key', '', '     ', 'None', '3', '35.7', 'xxx'):
            error = ckan.tests.call_action_api(self.app, 'am_following_user',
                    apikey=apikey, status=403, id=self.annafan['id'])
            assert error['message'] == 'Access denied'

    def test_04_am_following_user_missing_apikey(self):
        error = ckan.tests.call_action_api(self.app, 'am_following_user',
                status=403, id=self.annafan['id'])
        assert error['message'] == 'Access denied'

    def test_04_am_following_group_bad_apikey(self):
        for apikey in ('bad api key', '', '     ', 'None', '3', '35.7', 'xxx'):
            error = ckan.tests.call_action_api(self.app, 'am_following_group',
                    apikey=apikey, status=403, id=self.rogers_group['id'])
            assert error['message'] == 'Access denied'

    def test_04_am_following_group_missing_apikey(self):
        error = ckan.tests.call_action_api(self.app, 'am_following_group',
                status=403, id=self.rogers_group['id'])
        assert error['message'] == 'Access denied'


class TestFollowerDelete(object):
    '''Tests for the unfollow_* APIs.'''

    @classmethod
    def setup_class(self):
        ckan.tests.CreateTestData.create()
        self.tester = {
                'id': ckan.model.User.get('tester').id,
                'apikey': ckan.model.User.get('tester').apikey,
                'name': ckan.model.User.get('tester').name,
                }
        self.testsysadmin = {
                'id': ckan.model.User.get('testsysadmin').id,
                'apikey': ckan.model.User.get('testsysadmin').apikey,
                'name': ckan.model.User.get('testsysadmin').name,
                }
        self.annafan = {
            'id': ckan.model.User.get('annafan').id,
            'apikey': ckan.model.User.get('annafan').apikey,
            'name': ckan.model.User.get('annafan').name,
            }
        self.russianfan = {
            'id': ckan.model.User.get('russianfan').id,
            'apikey': ckan.model.User.get('russianfan').apikey,
            'name': ckan.model.User.get('russianfan').name,
            }
        self.joeadmin = {
            'id': ckan.model.User.get('joeadmin').id,
            'apikey': ckan.model.User.get('joeadmin').apikey,
            'name': ckan.model.User.get('joeadmin').name,
            }
        self.warandpeace = {
            'id': ckan.model.Package.get('warandpeace').id,
            'name': ckan.model.Package.get('warandpeace').name,
            }
        self.annakarenina = {
            'id': ckan.model.Package.get('annakarenina').id,
            'name': ckan.model.Package.get('annakarenina').name,
            }
        self.rogers_group = {
            'id': ckan.model.Group.get('roger').id,
            'name': ckan.model.Group.get('roger').name,
            }
        self.davids_group = {
            'id': ckan.model.Group.get('david').id,
            'name': ckan.model.Group.get('david').name,
            }
        self.app = paste.fixture.TestApp(pylons.test.pylonsapp)
        follow_user(self.app, self.testsysadmin['id'],
                self.testsysadmin['apikey'], self.joeadmin['id'],
                self.joeadmin['id'])
        follow_user(self.app, self.tester['id'], self.tester['apikey'],
                self.joeadmin['id'], self.joeadmin['id'])
        follow_user(self.app, self.russianfan['id'], self.russianfan['apikey'],
                self.joeadmin['id'], self.joeadmin['id'])
        follow_user(self.app, self.annafan['id'], self.annafan['apikey'],
                self.joeadmin['id'], self.joeadmin['id'])
        follow_user(self.app, self.annafan['id'], self.annafan['apikey'],
                self.tester['id'], self.tester['id'])
        follow_dataset(self.app, self.testsysadmin['id'],
                self.testsysadmin['apikey'], self.warandpeace['id'],
                self.warandpeace['id'])
        follow_dataset(self.app, self.tester['id'], self.tester['apikey'],
                self.warandpeace['id'], self.warandpeace['id'])
        follow_dataset(self.app, self.russianfan['id'], self.russianfan['apikey'],
                self.warandpeace['id'], self.warandpeace['id'])
        follow_dataset(self.app, self.annafan['id'], self.annafan['apikey'],
                self.warandpeace['id'], self.warandpeace['id'])
        follow_group(self.app, self.annafan['id'], self.annafan['apikey'],
                self.davids_group['id'], self.davids_group['id'])

    @classmethod
    def teardown_class(self):
        ckan.model.repo.rebuild_db()

    def test_01_unfollow_user_not_exists(self):
        '''Test the error response when a user tries to unfollow a user that
        she is not following.

        '''
        error = ckan.tests.call_action_api(self.app, 'unfollow_user',
                apikey=self.annafan['apikey'], status=404,
                id=self.russianfan['id'])
        assert error['message'].startswith('Not found: You are not following ')

    def test_01_unfollow_dataset_not_exists(self):
        '''Test the error response when a user tries to unfollow a dataset that
        she is not following.

        '''
        error = ckan.tests.call_action_api(self.app, 'unfollow_dataset',
                apikey=self.annafan['apikey'], status=404,
                id=self.annakarenina['id'])
        assert error['message'].startswith('Not found: You are not following')

    def test_01_unfollow_group_not_exists(self):
        '''Test the error response when a user tries to unfollow a group that
        she is not following.

        '''
        error = ckan.tests.call_action_api(self.app, 'unfollow_group',
                apikey=self.annafan['apikey'], status=404,
                id=self.rogers_group['id'])
        assert error['message'].startswith('Not found: You are not following')

    def test_01_unfollow_bad_apikey(self):
        '''Test the error response when a user tries to unfollow something
        but provides a bad API key.

        '''
        for action in ('unfollow_user', 'unfollow_dataset', 'unfollow_group'):
            for apikey in ('bad api key', '', '     ', 'None', '3', '35.7',
                    'xxx'):
                error = ckan.tests.call_action_api(self.app, action,
                        apikey=apikey, status=403, id=self.joeadmin['id'])
                assert error['message'] == 'Access denied'

    def test_01_unfollow_missing_apikey(self):
        '''Test error response when calling unfollow_* without api key.'''
        for action in ('unfollow_user', 'unfollow_dataset', 'unfollow_group'):
            error = ckan.tests.call_action_api(self.app, action, status=403,
                    id=self.joeadmin['id'])
            assert error['message'] == 'Access denied'

    def test_01_unfollow_bad_object_id(self):
        '''Test error response when calling unfollow_* with bad object id.'''
        for action in ('unfollow_user', 'unfollow_dataset', 'unfollow_group'):
            for object_id in ('bad id', '     ', 3, 35.7, 'xxx'):
                error = ckan.tests.call_action_api(self.app, action,
                        apikey=self.annafan['apikey'], status=409,
                        id=object_id)
                assert error['id'][0].startswith('Not found')

    def test_01_unfollow_missing_object_id(self):
        for action in ('unfollow_user', 'unfollow_dataset', 'unfollow_group'):
            for id in ('missing', None, ''):
                if id == 'missing':
                    error = ckan.tests.call_action_api(self.app, action,
                            apikey=self.annafan['apikey'], status=409)
                else:
                    error = ckan.tests.call_action_api(self.app, action,
                            apikey=self.annafan['apikey'], status=409, id=id)
                assert error['id'] == [u'Missing value']

    def _unfollow_user(self, follower_id, apikey, object_id, object_arg):
        '''Test a user unfollowing a user via the API.

        :param follower_id: id of the follower.
        :param apikey: API key of the follower.
        :param object_id: id of the object to unfollow.
        :param object_arg: the argument to pass to unfollow_user as the id of
            the object to unfollow, could be the object's id or name.

        '''
        # Record the user's number of followers before.
        count_before = ckan.tests.call_action_api(self.app,
                'user_follower_count', id=object_id)

        # Check that the user is following the object.
        am_following = ckan.tests.call_action_api(self.app,
                'am_following_user', apikey=apikey, id=object_id)
        assert am_following is True

        # Make the user unfollow the object.
        ckan.tests.call_action_api(self.app, 'unfollow_user', apikey=apikey,
                id=object_arg)

        # Check that am_following_user now returns False.
        am_following = ckan.tests.call_action_api(self.app,
                'am_following_user', apikey=apikey, id=object_id)
        assert am_following is False

        # Check that the user doesn't appear in the object's list of followers.
        followers = ckan.tests.call_action_api(self.app, 'user_follower_list',
                id=object_id)
        assert len([follower for follower in followers if follower['id'] ==
                follower_id]) == 0

        # Check that the object's follower count has decreased by 1.
        count_after = ckan.tests.call_action_api(self.app,
                'user_follower_count', id=object_id)
        assert count_after == count_before - 1

    def _unfollow_dataset(self, user_id, apikey, dataset_id, dataset_arg):
        '''Test a user unfollowing a dataset via the API.

        :param user_id: id of the follower.
        :param apikey: API key of the follower.
        :param dataset_id: id of the object to unfollow.
        :param dataset_arg: the argument to pass to unfollow_dataset as the id
            of the object to unfollow, could be the object's id or name.

        '''
        # Record the dataset's number of followers before.
        count_before = ckan.tests.call_action_api(self.app,
                'dataset_follower_count', id=dataset_id)

        # Check that the user is following the dataset.
        am_following = ckan.tests.call_action_api(self.app,
                'am_following_dataset', apikey=apikey, id=dataset_id)
        assert am_following is True

        # Make the user unfollow the dataset.
        ckan.tests.call_action_api(self.app, 'unfollow_dataset', apikey=apikey,
                id=dataset_arg)

        # Check that am_following_dataset now returns False.
        am_following = ckan.tests.call_action_api(self.app,
                'am_following_dataset', apikey=apikey, id=dataset_id)
        assert am_following is False

        # Check that the user doesn't appear in the dataset's list of
        # followers.
        followers = ckan.tests.call_action_api(self.app,
                'dataset_follower_list', id=dataset_id)
        assert len([follower for follower in followers if follower['id'] ==
                user_id]) == 0

        # Check that the dataset's follower count has decreased by 1.
        count_after = ckan.tests.call_action_api(self.app,
                'dataset_follower_count', id=dataset_id)
        assert count_after == count_before - 1

    def _unfollow_group(self, user_id, apikey, group_id, group_arg):
        '''Test a user unfollowing a group via the API.

        :param user_id: id of the user
        :param apikey: API key of the user
        :param group_id: id of the group
        :param group_arg: the argument to pass to unfollow_group as the id
            of the group, could be the group's id or name.

        '''
        # Record the group's number of followers before.
        count_before = ckan.tests.call_action_api(self.app,
                'group_follower_count', id=group_id)

        # Check that the user is following the group.
        am_following = ckan.tests.call_action_api(self.app,
                'am_following_group', apikey=apikey, id=group_id)
        assert am_following is True

        # Make the user unfollow the group.
        ckan.tests.call_action_api(self.app, 'unfollow_group', apikey=apikey,
                id=group_arg)

        # Check that am_following_group now returns False.
        am_following = ckan.tests.call_action_api(self.app,
                'am_following_group', apikey=apikey, id=group_id)
        assert am_following is False

        # Check that the user doesn't appear in the group's list of
        # followers.
        followers = ckan.tests.call_action_api(self.app, 'group_follower_list',
                id=group_id)
        assert len([follower for follower in followers if follower['id'] ==
                user_id]) == 0

        # Check that the group's follower count has decreased by 1.
        count_after = ckan.tests.call_action_api(self.app,
                'group_follower_count', id=group_id)
        assert count_after == count_before - 1

    def test_02_follower_delete_by_id(self):
        self._unfollow_user(self.annafan['id'], self.annafan['apikey'],
                self.joeadmin['id'], self.joeadmin['id'])
        self._unfollow_dataset(self.annafan['id'], self.annafan['apikey'],
                self.warandpeace['id'], self.warandpeace['id'])
        self._unfollow_group(self.annafan['id'], self.annafan['apikey'],
                self.davids_group['id'], self.davids_group['id'])

class TestFollowerCascade(object):
    '''Tests for on delete cascade of follower table rows.'''

    @classmethod
    def setup_class(self):
        ckan.tests.CreateTestData.create()
        self.tester = {
                'id': ckan.model.User.get('tester').id,
                'apikey': ckan.model.User.get('tester').apikey,
                'name': ckan.model.User.get('tester').name,
                }
        self.testsysadmin = {
                'id': ckan.model.User.get('testsysadmin').id,
                'apikey': ckan.model.User.get('testsysadmin').apikey,
                'name': ckan.model.User.get('testsysadmin').name,
                }
        self.annafan = {
            'id': ckan.model.User.get('annafan').id,
            'apikey': ckan.model.User.get('annafan').apikey,
            'name': ckan.model.User.get('annafan').name,
            }
        self.russianfan = {
            'id': ckan.model.User.get('russianfan').id,
            'apikey': ckan.model.User.get('russianfan').apikey,
            'name': ckan.model.User.get('russianfan').name,
            }
        self.joeadmin = {
            'id': ckan.model.User.get('joeadmin').id,
            'apikey': ckan.model.User.get('joeadmin').apikey,
            'name': ckan.model.User.get('joeadmin').name,
            }
        self.warandpeace = {
            'id': ckan.model.Package.get('warandpeace').id,
            'name': ckan.model.Package.get('warandpeace').name,
            }
        self.annakarenina = {
            'id': ckan.model.Package.get('annakarenina').id,
            'name': ckan.model.Package.get('annakarenina').name,
            }
        self.rogers_group = {
            'id': ckan.model.Group.get('roger').id,
            'name': ckan.model.Group.get('roger').name,
            }
        self.davids_group = {
            'id': ckan.model.Group.get('david').id,
            'name': ckan.model.Group.get('david').name,
            }
        self.app = paste.fixture.TestApp(pylons.test.pylonsapp)

        follow_user(self.app, self.joeadmin['id'], self.joeadmin['apikey'],
                self.testsysadmin['id'], self.testsysadmin['id'])

        follow_user(self.app, self.annafan['id'], self.annafan['apikey'],
                self.testsysadmin['id'], self.testsysadmin['id'])
        follow_user(self.app, self.russianfan['id'], self.russianfan['apikey'],
                self.testsysadmin['id'], self.testsysadmin['id'])

        follow_dataset(self.app, self.joeadmin['id'], self.joeadmin['apikey'],
                self.annakarenina['id'], self.annakarenina['id'])

        follow_dataset(self.app, self.annafan['id'], self.annafan['apikey'],
                self.annakarenina['id'], self.annakarenina['id'])
        follow_dataset(self.app, self.russianfan['id'], self.russianfan['apikey'],
                self.annakarenina['id'], self.annakarenina['id'])

        follow_user(self.app, self.tester['id'], self.tester['apikey'],
                self.joeadmin['id'], self.joeadmin['id'])

        follow_dataset(self.app, self.testsysadmin['id'],
                self.testsysadmin['apikey'], self.warandpeace['id'],
                self.warandpeace['id'])

        follow_group(self.app, self.testsysadmin['id'],
                self.testsysadmin['apikey'], self.davids_group['id'],
                self.davids_group['id'])

        session = ckan.model.Session()
        session.delete(ckan.model.User.get('joeadmin'))
        session.commit()

        session.delete(ckan.model.Package.get('warandpeace'))
        session.commit()

        session.delete(ckan.model.Group.get('david'))
        session.commit()

    @classmethod
    def teardown_class(self):
        ckan.model.repo.rebuild_db()

    def test_01_on_delete_cascade_api(self):
        '''
        Test that UserFollowingUser and UserFollowingDataset rows cascade.


        '''
        # It should no longer be possible to get joeadmin's follower list.
        error = ckan.tests.call_action_api(self.app, 'user_follower_list',
                status=409, id='joeadmin')
        assert 'id' in error

        # It should no longer be possible to get warandpeace's follower list.
        error = ckan.tests.call_action_api(self.app, 'dataset_follower_list',
                status=409, id='warandpeace')
        assert 'id' in error

        # It should no longer be possible to get david's follower list.
        error = ckan.tests.call_action_api(self.app, 'group_follower_list',
                status=409, id='david')
        assert 'id' in error

        # It should no longer be possible to get joeadmin's follower count.
        error = ckan.tests.call_action_api(self.app, 'user_follower_count',
                status=409, id='joeadmin')
        assert 'id' in error

        # It should no longer be possible to get warandpeace's follower count.
        error = ckan.tests.call_action_api(self.app, 'dataset_follower_count',
                status=409, id='warandpeace')
        assert 'id' in error

        # It should no longer be possible to get david's follower count.
        error = ckan.tests.call_action_api(self.app, 'group_follower_count',
                status=409, id='david')
        assert 'id' in error

        # It should no longer be possible to get am_following for joeadmin.
        error = ckan.tests.call_action_api(self.app, 'am_following_user',
                apikey=self.testsysadmin['apikey'], status=409, id='joeadmin')
        assert 'id' in error

        # It should no longer be possible to get am_following for warandpeace.
        error = ckan.tests.call_action_api(self.app, 'am_following_dataset',
                apikey=self.testsysadmin['apikey'], status=409,
                id='warandpeace')
        assert 'id' in error

        # It should no longer be possible to get am_following for david.
        error = ckan.tests.call_action_api(self.app, 'am_following_group',
                apikey=self.testsysadmin['apikey'], status=409, id='david')
        assert 'id' in error

        # It should no longer be possible to unfollow joeadmin.
        error = ckan.tests.call_action_api(self.app, 'unfollow_user',
                apikey=self.tester['apikey'], status=409, id='joeadmin')
        assert error['id'] == ['Not found: User']

        # It should no longer be possible to unfollow warandpeace.
        error = ckan.tests.call_action_api(self.app, 'unfollow_dataset',
                apikey=self.testsysadmin['apikey'], status=409,
                id='warandpeace')
        assert error['id'] == ['Not found: Dataset']

        # It should no longer be possible to unfollow david.
        error = ckan.tests.call_action_api(self.app, 'unfollow_group',
                apikey=self.testsysadmin['apikey'], status=409, id='david')
        assert error['id'] == ['Not found: Group']

        # It should no longer be possible to follow joeadmin.
        error = ckan.tests.call_action_api(self.app, 'follow_user',
                apikey=self.annafan['apikey'], status=409, id='joeadmin')
        assert 'id' in error

        # It should no longer be possible to follow warandpeace.
        error = ckan.tests.call_action_api(self.app, 'follow_dataset',
                apikey=self.annafan['apikey'], status=409, id='warandpeace')
        assert 'id' in error

        # It should no longer be possible to follow david.
        error = ckan.tests.call_action_api(self.app, 'follow_group',
                apikey=self.annafan['apikey'], status=409, id='david')
        assert 'id' in error

        # Users who joeadmin was following should no longer have him in their
        # follower list.
        followers = ckan.tests.call_action_api(self.app, 'user_follower_list',
                id=self.testsysadmin['id'])
        assert 'joeadmin' not in [follower['name'] for follower in followers]

        # Datasets who joeadmin was following should no longer have him in
        # their follower list.
        followers = ckan.tests.call_action_api(self.app,
                'dataset_follower_list', id=self.annakarenina['id'])
        assert 'joeadmin' not in [follower['name'] for follower in followers]

    def test_02_on_delete_cascade_db(self):
        if not are_foreign_keys_supported():
            raise SkipTest("Search not supported")

        # After the previous test above there should be no rows with joeadmin's
        # id in the UserFollowingUser or UserFollowingDataset tables.
        from ckan.model import UserFollowingUser, UserFollowingDataset, UserFollowingGroup
        session = ckan.model.Session()

        query = session.query(UserFollowingUser)
        query = query.filter(UserFollowingUser.follower_id==self.joeadmin['id'])
        assert query.count() == 0

        query = session.query(UserFollowingUser)
        query = query.filter(UserFollowingUser.object_id==self.joeadmin['id'])
        assert query.count() == 0

        query = session.query(UserFollowingDataset)
        query = query.filter(UserFollowingUser.follower_id==self.joeadmin['id'])
        assert query.count() == 0

        # There should be no rows with warandpeace's id in the
        # UserFollowingDataset table.
        query = session.query(UserFollowingDataset)
        query = query.filter(
                UserFollowingDataset.object_id==self.warandpeace['id'])
        assert query.count() == 0

        # There should be no rows with david's id in the
        # UserFollowingGroup table.
        query = session.query(UserFollowingGroup)
        query = query.filter(
                UserFollowingGroup.object_id==self.davids_group['id'])
        assert query.count() == 0
