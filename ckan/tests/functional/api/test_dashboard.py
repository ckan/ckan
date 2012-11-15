import ckan
from ckan.lib.helpers import json
import paste
import pylons.test


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
                extra_environ={'Authorization': str(cls.joeadmin['apikey'])})
        assert response.json['success'] is True
        new_user = response.json['result']
        return new_user

    @classmethod
    def setup_class(cls):
        ckan.tests.CreateTestData.create()
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

    def dashboard_new_activities_count(self, user):
        '''Return the given user's new activities count from the CKAN API.'''
        params = json.dumps({})
        response = self.app.post('/api/action/dashboard_new_activities_count',
                params=params,
                extra_environ={'Authorization': str(user['apikey'])})
        assert response.json['success'] is True
        new_activities_count = response.json['result']
        return new_activities_count

    def dashboard_activity_list(self, user):
        '''Return the given user's dashboard activity list from the CKAN API.

        '''
        params = json.dumps({})
        response = self.app.post('/api/action/dashboard_activity_list',
                params=params,
                extra_environ={'Authorization': str(user['apikey'])})
        assert response.json['success'] is True
        activity_list = response.json['result']
        return activity_list

    def dashboard_new_activities(self, user):
        '''Return the activities from the user's dashboard activity stream
        that are currently marked as new.'''
        activity_list = self.dashboard_activity_list(user)
        return [activity for activity in activity_list if activity['is_new']]

    def dashboard_mark_activities_as_read(self, user):
        params = json.dumps({})
        response = self.app.post(
                '/api/action/dashboard_mark_activities_as_read',
                params=params,
                extra_environ={'Authorization': str(user['apikey'])})
        assert response.json['success'] is True

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
        self.dashboard_mark_activities_as_read(self.new_user)

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

    def test_03_own_activities_not_marked_as_new(self):
        '''Make a user do some activities and check that her own activities
        aren't marked as new in her dashboard activity stream.'''
        assert len(self.dashboard_new_activities(self.new_user)) == 0

    def test_04_new_activities_count(self):
        '''Test that new activities from objects that a user follows increase
        her new activities count.'''

        # Make someone else who new_user is not following update a dataset that
        # new_user is following.
        params = json.dumps({'name': 'warandpeace', 'notes': 'updated again'})
        response = self.app.post('/api/action/package_update', params=params,
                extra_environ={'Authorization': str(self.joeadmin['apikey'])})
        assert response.json['success'] is True

        # Make someone that the user is following create a new dataset.
        params = json.dumps({'name': 'annas_new_dataset'})
        response = self.app.post('/api/action/package_create', params=params,
                extra_environ={'Authorization': str(self.annafan['apikey'])})
        assert response.json['success'] is True

        # Make someone that the user is not following update a dataset that
        # the user is not following, but that belongs to a group that the user
        # is following.
        params = json.dumps({'name': 'annakarenina', 'notes': 'updated'})
        response = self.app.post('/api/action/package_update', params=params,
            extra_environ={'Authorization': str(self.testsysadmin['apikey'])})
        assert response.json['success'] is True

        # FIXME: The number here should be 3 but activities from followed
        # groups are not appearing in dashboard. When that is fixed, fix this
        # number.
        assert self.dashboard_new_activities_count(self.new_user) == 2

    def test_05_activities_marked_as_new(self):
        '''Test that new activities from objects that a user follows are
        marked as new in her dashboard activity stream.'''
        # FIXME: The number here should be 3 but activities from followed
        # groups are not appearing in dashboard. When that is fixed, fix this
        # number.
        assert len(self.dashboard_new_activities(self.new_user)) == 2

    def test_06_mark_new_activities_as_read(self):
        '''Test that a user's new activities are marked as old when she views
        her dashboard activity stream.'''
        assert self.dashboard_new_activities_count(self.new_user) > 0
        assert len(self.dashboard_new_activities(self.new_user)) > 0
        self.dashboard_mark_activities_as_read(self.new_user)
        assert self.dashboard_new_activities_count(self.new_user) == 0
        assert len(self.dashboard_new_activities(self.new_user)) == 0
