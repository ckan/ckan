# encoding: utf-8

'''Test for the dashboard API.

This module tests the various functions of the user dashboard, such as the
contents of the dashboard activity stream and reporting the number of new
activities.

'''
import ckan
from ckan.common import json
import paste
import pylons.test
from ckan.tests.legacy import CreateTestData

class TestDashboard(object):
    '''Tests for the logic action functions related to the user's dashboard.'''

    @classmethod
    def user_create(cls):
        '''Create a new user.'''
        params = json.dumps({
            'name': 'mr_new_user',
            'email': 'mr@newuser.com',
            'password': 'iammrnew',
            })
        response = cls.app.post('/api/action/user_create', params=params,
                extra_environ={'Authorization': str(cls.testsysadmin['apikey'])})
        assert response.json['success'] is True
        new_user = response.json['result']
        return new_user

    @classmethod
    def setup_class(cls):
        ckan.lib.search.clear_all()
        CreateTestData.create()
        cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)
        joeadmin = ckan.model.User.get('joeadmin')
        cls.joeadmin = {
                'id': joeadmin.id,
                'apikey': joeadmin.apikey
                }
        annafan = ckan.model.User.get('annafan')
        cls.annafan = {
                'id': annafan.id,
                'apikey': annafan.apikey
                }
        testsysadmin = ckan.model.User.get('testsysadmin')
        cls.testsysadmin = {
                'id': testsysadmin.id,
                'apikey': testsysadmin.apikey
                }
        cls.new_user = cls.user_create()

    @classmethod
    def teardown_class(cls):
        ckan.model.repo.rebuild_db()

    def post(self, action, params=None, apikey=None, status=200):
        '''Post to the CKAN API and return the result.'''
        if params is None:
            params = {}
        params = json.dumps(params)
        response = self.app.post('/api/action/{0}'.format(action),
                params=params,
                extra_environ={'Authorization': str(apikey)},
                status=status)
        if status in (200,):
            assert response.json['success'] is True
            return response.json['result']
        else:
            assert response.json['success'] is False
            return response.json['error']

    def dashboard_new_activities_count(self, user):
        '''Return the given user's new activities count from the CKAN API.'''
        return self.post('dashboard_new_activities_count',
                apikey=user['apikey'])

    def dashboard_activity_list(self, user):
        '''Return the given user's dashboard activity list from the CKAN API.

        '''
        return self.post('dashboard_activity_list', apikey=user['apikey'])

    def dashboard_new_activities(self, user):
        '''Return the activities from the user's dashboard activity stream
        that are currently marked as new.'''
        activity_list = self.dashboard_activity_list(user)
        return [activity for activity in activity_list if activity['is_new']]

    def dashboard_mark_activities_old(self, user):
        self.post('dashboard_mark_activities_old',
                apikey=user['apikey'])

    def test_00_dashboard_activity_list_not_logged_in(self):
        self.post('dashboard_activity_list', status=403)

    def test_00_dashboard_new_activities_count_not_logged_in(self):
        self.post('dashboard_new_activities_count', status=403)

    def test_00_dashboard_mark_new_activities_not_logged_in(self):
        self.post('dashboard_mark_activities_old', status=403)

    def test_01_dashboard_activity_list_for_new_user(self):
        '''Test the contents of a new user's dashboard activity stream.'''
        activities = self.dashboard_activity_list(self.new_user)
        # We expect to find a single 'new user' activity.
        assert len(activities) == 1
        activity = activities[0]
        assert activity['activity_type'] == 'new user'
        assert activity['user_id'] == activity['object_id']
        assert activity['user_id'] == self.new_user['id']

    def test_01_new_activities_count_for_new_user(self):
        '''Test that a newly registered user's new activities count is 0.'''
        assert self.dashboard_new_activities_count(self.new_user) == 0

    def test_01_new_activities_for_new_user(self):
        '''Test that a newly registered user has no activities marked as new
        in their dashboard activity stream.'''
        assert len(self.dashboard_new_activities(self.new_user)) == 0

    def test_02_own_activities_do_not_count_as_new(self):
        '''Make a user do some activities and check that her own activities
        don't increase her new activities count.'''

        # The user has to view her dashboard activity stream first to mark any
        # existing activities as read. For example when she follows a dataset
        # below, past activities from the dataset (e.g. when someone created
        # the dataset, etc.) will appear in her dashboard, and if she has never
        # viewed her dashboard then those activities will be considered
        # "unseen".
        # We would have to do this if, when you follow something, you only get
        # the activities from that object since you started following it, and
        # not all its past activities as well.
        self.dashboard_mark_activities_old(self.new_user)

        # Create a new dataset.
        params = json.dumps({
            'name': 'my_new_package',
            })
        response = self.app.post('/api/action/package_create', params=params,
                extra_environ={'Authorization': str(self.new_user['apikey'])})
        assert response.json['success'] is True

        # Follow a dataset.
        params = json.dumps({'id': 'warandpeace'})
        response = self.app.post('/api/action/follow_dataset', params=params,
                extra_environ={'Authorization': str(self.new_user['apikey'])})
        assert response.json['success'] is True

        # Follow a user.
        params = json.dumps({'id': 'annafan'})
        response = self.app.post('/api/action/follow_user', params=params,
                extra_environ={'Authorization': str(self.new_user['apikey'])})
        assert response.json['success'] is True

        # Follow a group.
        params = json.dumps({'id': 'roger'})
        response = self.app.post('/api/action/follow_group', params=params,
                extra_environ={'Authorization': str(self.new_user['apikey'])})
        assert response.json['success'] is True

        # Update the dataset that we're following.
        params = json.dumps({'name': 'warandpeace', 'notes': 'updated'})
        response = self.app.post('/api/action/package_update', params=params,
                extra_environ={'Authorization': str(self.new_user['apikey'])})
        assert response.json['success'] is True

        # User's own actions should not increase her activity count.
        assert self.dashboard_new_activities_count(self.new_user) == 0

    def test_03_dashboard_activity_list_own_activities(self):
        '''Test that a user's own activities appear in her dashboard.'''
        activities = self.dashboard_activity_list(self.new_user)

        # FIXME: There should actually be 3 activities here, but when you
        # follow something it's old activities (from before you followed it)
        # appear in your activity stream. So here we get more activities than
        # expected.
        assert len(activities) == 5, len(activities)

        assert activities[0]['activity_type'] == 'changed package'
        #assert activities[1]['activity_type'] == 'follow group'
        #assert activities[2]['activity_type'] == 'follow user'
        #assert activities[3]['activity_type'] == 'follow dataset'
        assert activities[1]['activity_type'] == 'new package'
        assert activities[2]['activity_type'] == 'new user'

        # FIXME: Shouldn't need the [:3] here, it's because when you follow
        # something its old activities (from before you started following it)
        # appear in your dashboard.
        for activity in activities[:3]:
            assert activity['user_id'] == self.new_user['id']

    def test_03_own_activities_not_marked_as_new(self):
        '''Make a user do some activities and check that her own activities
        aren't marked as new in her dashboard activity stream.'''
        assert len(self.dashboard_new_activities(self.new_user)) == 0

    def test_04_activities_from_followed_datasets(self):
        '''Activities from followed datasets should show in dashboard.'''

        activities_before = self.dashboard_activity_list(self.new_user)

        # Make someone else who new_user is not following update a dataset that
        # new_user is following.
        params = json.dumps({'name': 'warandpeace', 'notes': 'updated again'})
        response = self.app.post('/api/action/package_update', params=params,
                extra_environ={'Authorization': str(self.joeadmin['apikey'])})
        assert response.json['success'] is True

        # Check the new activity in new_user's dashboard.
        activities = self.dashboard_activity_list(self.new_user)
        new_activities = [activity for activity in activities
                if activity not in activities_before]
        assert len(new_activities) == 1
        activity = new_activities[0]
        assert activity['activity_type'] == 'changed package'
        assert activity['user_id'] == self.joeadmin['id']
        assert activity['data']['package']['name'] == 'warandpeace'

    def test_04_activities_from_followed_users(self):
        '''Activities from followed users should show in the dashboard.'''

        activities_before = self.dashboard_activity_list(self.new_user)

        # Make someone that the user is following create a new dataset.
        params = json.dumps({'name': 'annas_new_dataset'})
        response = self.app.post('/api/action/package_create', params=params,
                extra_environ={'Authorization': str(self.annafan['apikey'])})
        assert response.json['success'] is True

        # Check the new activity in new_user's dashboard.
        activities = self.dashboard_activity_list(self.new_user)
        new_activities = [activity for activity in activities
                if activity not in activities_before]
        assert len(new_activities) == 1
        activity = new_activities[0]
        assert activity['activity_type'] == 'new package'
        assert activity['user_id'] == self.annafan['id']
        assert activity['data']['package']['name'] == 'annas_new_dataset'

    def test_04_activities_from_followed_groups(self):
        '''Activities from followed groups should show in the dashboard.'''

        activities_before = self.dashboard_activity_list(self.new_user)

        # Make someone that the user is not following update a group that the
        # user is following.
        group = self.post('group_show',
                          {'id': 'roger', 'include_datasets':True},
                          apikey=self.testsysadmin['apikey'])
        group['description'] = 'updated'
        self.post('group_update', group, apikey=self.testsysadmin['apikey'])

        # Check the new activity in new_user's dashboard.
        activities = self.dashboard_activity_list(self.new_user)
        new_activities = [activity for activity in activities
                if activity not in activities_before]
        assert len(new_activities) == 1
        activity = new_activities[0]
        assert activity['activity_type'] == 'changed group'
        assert activity['user_id'] == self.testsysadmin['id']
        assert activity['data']['group']['name'] == 'roger'

    def test_04_activities_from_datasets_of_followed_groups(self):
        '''Activities from datasets of followed groups should show in the
        dashboard.

        '''
        activities_before = self.dashboard_activity_list(self.new_user)

        # Make someone that the user is not following update a dataset that the
        # user is not following either, but that belongs to a group that the
        # user is following.
        params = json.dumps({'name': 'annakarenina', 'notes': 'updated'})
        response = self.app.post('/api/action/package_update', params=params,
            extra_environ={'Authorization': str(self.joeadmin['apikey'])})
        assert response.json['success'] is True

        # Check the new activity in new_user's dashboard.
        activities = self.dashboard_activity_list(self.new_user)
        new_activities = [activity for activity in activities
                if activity not in activities_before]
        assert len(new_activities) == 1
        activity = new_activities[0]
        assert activity['activity_type'] == 'changed package'
        assert activity['user_id'] == self.joeadmin['id']
        assert activity['data']['package']['name'] == 'annakarenina'

    def test_05_new_activities_count(self):
        '''Test that new activities from objects that a user follows increase
        her new activities count.'''
        assert self.dashboard_new_activities_count(self.new_user) == 4

    def test_06_activities_marked_as_new(self):
        '''Test that new activities from objects that a user follows are
        marked as new in her dashboard activity stream.'''
        assert len(self.dashboard_new_activities(self.new_user)) == 4

    def test_07_mark_new_activities_as_read(self):
        '''Test that a user's new activities are marked as old when she views
        her dashboard activity stream.'''
        assert self.dashboard_new_activities_count(self.new_user) > 0
        assert len(self.dashboard_new_activities(self.new_user)) > 0
        self.dashboard_mark_activities_old(self.new_user)
        assert self.dashboard_new_activities_count(self.new_user) == 0
        assert len(self.dashboard_new_activities(self.new_user)) == 0

    def test_08_maximum_number_of_new_activities(self):
        '''Test that the new activities count does not go higher than 15, even
        if there are more than 15 new activities from the user's followers.'''
        for n in range(0, 20):
            notes = "Updated {n} times".format(n=n)
            params = json.dumps({'name': 'warandpeace', 'notes': notes})
            response = self.app.post('/api/action/package_update',
                params=params,
                extra_environ={'Authorization': str(self.joeadmin['apikey'])})
            assert response.json['success'] is True
        assert self.dashboard_new_activities_count(self.new_user) == 15

    def test_09_activities_that_should_not_show(self):
        '''Test that other activities do not appear on the user's dashboard.'''

        before = self.dashboard_activity_list(self.new_user)

        # Make someone else who new_user is not following create a new dataset.
        params = json.dumps({'name': 'irrelevant_dataset'})
        response = self.app.post('/api/action/package_create', params=params,
            extra_environ={'Authorization': str(self.testsysadmin['apikey'])})
        assert response.json['success'] is True

        after = self.dashboard_activity_list(self.new_user)

        assert before == after

    def test_10_dashboard_activity_list_html_does_not_crash(self):

        params = json.dumps({'name': 'irrelevant_dataset1'})
        response = self.app.post('/api/action/package_create', params=params,
            extra_environ={'Authorization': str(self.annafan['apikey'])})
        assert response.json['success'] is True

        params = json.dumps({'name': 'another_irrelevant_dataset'})
        response = self.app.post('/api/action/package_create', params=params,
            extra_environ={'Authorization': str(self.annafan['apikey'])})
        assert response.json['success'] is True

        res = self.app.get('/api/3/action/dashboard_activity_list_html',
                extra_environ={'Authorization':
                    str(self.annafan['apikey'])})
        assert res.json['success'] is True
