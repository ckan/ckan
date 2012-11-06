import ckan
from ckan.lib.helpers import json
import paste
import pylons.test


class TestDashboard(object):
    '''Tests for the logic action functions related to the user's dashboard.'''

    @classmethod
    def setup_class(cls):
        ckan.tests.CreateTestData.create()
        cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)
        joeadmin = ckan.model.User.get('joeadmin')
        cls.joeadmin = {
                'id': joeadmin.id,
                'apikey': joeadmin.apikey
                }

    @classmethod
    def teardown_class(cls):
        ckan.model.repo.rebuild_db()

    def new_activities_count(self, user):
        '''Return the given user's new activities count from the CKAN API.'''

        params = json.dumps({})
        response = self.app.post('/api/action/dashboard_new_activities_count',
                params=params,
                extra_environ={'Authorization': str(user['apikey'])})
        assert response.json['success'] is True
        new_activities_count = response.json['result']
        return new_activities_count

    def mark_as_read(self, user):
        params = json.dumps({})
        response = self.app.post(
                '/api/action/dashboard_mark_activities_as_read',
                params=params,
                extra_environ={'Authorization': str(user['apikey'])})
        assert response.json['success'] is True

    def test_01_num_new_activities_new_user(self):
        '''Test retreiving the number of new activities for a new user.'''

        # Create a new user.
        params = json.dumps({
            'name': 'mr_new_user',
            'email': 'mr@newuser.com',
            'password': 'iammrnew',
            })
        response = self.app.post('/api/action/user_create', params=params,
                extra_environ={'Authorization': str(self.joeadmin['apikey'])})
        assert response.json['success'] is True
        new_user = response.json['result']

        # We expect to find only one new activity for a newly registered user
        # (A "{USER} signed up" activity).
        assert self.new_activities_count(new_user) == 1

        self.mark_as_read(new_user)
        assert self.new_activities_count(new_user) == 0

        # Create a dataset.
        params = json.dumps({
            'name': 'my_new_package',
            })
        response = self.app.post('/api/action/package_create', params=params,
                extra_environ={'Authorization': str(new_user['apikey'])})
        assert response.json['success'] is True

        # Now there should be a new 'user created dataset' activity.
        assert self.new_activities_count(new_user) == 1

        # Update the dataset.
        params = json.dumps({
            'name': 'my_new_package',
            'title': 'updated description',
            })
        response = self.app.post('/api/action/package_update', params=params,
                extra_environ={'Authorization': str(new_user['apikey'])})
        assert response.json['success'] is True

        assert self.new_activities_count(new_user) == 2

        self.mark_as_read(new_user)
        assert self.new_activities_count(new_user) == 0
