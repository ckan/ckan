# encoding: utf-8

'''Functional tests for the public activity streams API.

This module tests the contents of the various public activity streams:
use activity streams, dataset activity streams, group activity streams, etc.

This module _does not_ test the private user dashboard activity stream (which
is different because the contents depend on what the user is following), that
is tested in test_dashboard.py.

'''
import datetime
import logging
logger = logging.getLogger(__name__)

import pylons.test
from ckan.common import config
from paste.deploy.converters import asbool
import paste.fixture
from nose import SkipTest
from ckan.common import json
import ckan.tests.legacy as tests
from ckan.tests.helpers import call_action, _get_test_app


##def package_update(context, data_dict):
##    # These tests call package_update directly which is really bad
##    # setting api_version in context make things seem like the api key
##    # is ok etc
##    context['api_version'] = 3
##    context['ignore_auth'] = True
##    return _package_update(context, data_dict)
##
##def package_create(context, data_dict):
##    # These tests call package_update directly which is really bad
##    # setting api_version in context make things seem like the api key
##    # is ok etc
##    context['api_version'] = 3
##    context['ignore_auth'] = True
##    return _package_create(context, data_dict)
def package_show(app, data_dict, apikey=None):
    if apikey:
        extra_environ = {'Authorization': str(apikey)}
    else:
        extra_environ = None
    response = app.post('/api/action/package_show', json.dumps(data_dict),
            extra_environ=extra_environ)
    response_dict = json.loads(response.body)
    assert response_dict['success'] is True
    package = response_dict['result']
    return package


def package_list(app, data_dict=None, apikey=None):
    if data_dict is None:
        data_dict = {}
    if apikey:
        extra_environ = {'Authorization': str(apikey)}
    else:
        extra_environ = None
    response = app.post('/api/action/package_list',
            json.dumps(data_dict), extra_environ=extra_environ)
    response_dict = json.loads(response.body)
    assert response_dict['success'] is True
    packages = response_dict['result']
    return packages


def group_list(app, data_dict=None, apikey=None):
    if data_dict is None:
        data_dict = {}
    if 'all_fields' not in data_dict:
        data_dict['all_fields'] = True
    if apikey:
        extra_environ = {'Authorization': str(apikey)}
    else:
        extra_environ = None
    response = app.post('/api/action/group_list',
            json.dumps(data_dict), extra_environ=extra_environ)
    response_dict = json.loads(response.body)
    assert response_dict['success'] is True
    groups = response_dict['result']
    return groups


def package_update(app, data_dict, user):
    response = call_action('package_update', context={'user': user['name']},
                           **data_dict)
    return response


def group_update(app, data_dict, apikey=None):
    if apikey:
        extra_environ = {'Authorization': str(apikey)}
    else:
        extra_environ = None
    response = app.post('/api/action/group_update',
            json.dumps(data_dict), extra_environ=extra_environ)
    response_dict = json.loads(response.body)
    assert response_dict['success'] is True
    updated_group = response_dict['result']
    return updated_group


def datetime_from_string(s):
    '''Return a standard datetime.datetime object initialised from a string in
    the same format used for timestamps in dictized activities (the format
    produced by datetime.datetime.isoformat())

    '''
    return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f')


def make_resource():
    '''Return a test resource in dictionary form.'''
    return {
            'url': 'http://www.example.com',
            'description': 'example resource description',
            'format': 'txt',
            'name': 'example resource',
            }


def make_package(name=None):
    '''Return a test package in dictionary form.'''
    if name is None:
        name = "test_package"

    # A package with no resources, tags, extras or groups.
    pkg = {
        'name': name,
        'title': 'My Test Package',
        'author': 'test author',
        'author_email': 'test_author@testauthor.com',
        'maintainer': 'test maintainer',
        'maintainer_email': 'test_maintainer@testmaintainer.com',
        'notes': 'some test notes',
        'url': 'www.example.com',
        }

    # Add some resources to the package.
    res1 = {
            'url': 'http://www.example-resource.info',
            'description': 'an example resource description',
            'format': 'HTML',
            'name': 'an example resource',
        }
    res2 = {
            'url': 'http://www.example-resource2.info',
            'description': 'another example resource description',
            'format': 'PDF',
            'name': 'another example resource',
        }
    pkg['resources'] = [res1, res2]

    # Add some tags to the package.
    tag1 = {'name': 'a_test_tag'}
    tag2 = {'name': 'another_test_tag'}
    pkg['tags'] = [tag1, tag2]

    # Add the package to a group.
    pkg['groups'] = [{'name': 'roger'}]

    return pkg


def find_new_activities(before, after):
    return [activity for activity in after if activity not in before]


class TestActivity:
    @classmethod
    def setup_class(self):
        if not asbool(config.get('ckan.activity_streams_enabled', 'true')):
            raise SkipTest('Activity streams not enabled')
        import ckan
        import ckan.model as model
        tests.CreateTestData.create()
        sysadmin_user = model.User.get('testsysadmin')
        self.sysadmin_user = {
                'id': sysadmin_user.id,
                'apikey': sysadmin_user.apikey,
                'name': sysadmin_user.name,
                }
        normal_user = model.User.get('annafan')

        self.normal_user = {
                'id': normal_user.id,
                'apikey': normal_user.apikey,
                'name': normal_user.name,
                }
        warandpeace = model.Package.get('warandpeace')
        self.warandpeace = {
                'id': warandpeace.id,
                }
        annakarenina = model.Package.get('annakarenina')
        self.annakarenina = {
                'id': annakarenina.id,
                }
        self.users = [self.sysadmin_user, self.normal_user]
        self.app = _get_test_app()

    @classmethod
    def teardown_class(self):
        import ckan.model as model
        model.repo.rebuild_db()

    def user_activity_stream(self, user_id, apikey=None):
        if apikey:
            extra_environ = {'Authorization': str(apikey)}
        else:
            extra_environ = None
        params = {'id': user_id}
        response = self.app.get("/api/action/user_activity_list",
                                params=params, extra_environ=extra_environ)
        assert response.json['success'] is True
        activities = response.json['result']
        return activities

    def package_activity_stream(self, package_id, apikey=None):
        if apikey:
            extra_environ = {'Authorization': str(apikey)}
        else:
            extra_environ = None
        params = {'id': package_id}
        response = self.app.get("/api/action/package_activity_list",
                                params=params, extra_environ=extra_environ)
        assert response.json['success'] is True
        activities = response.json['result']
        return activities

    def group_activity_stream(self, group_id, apikey=None):
        if apikey:
            extra_environ = {'Authorization': str(apikey)}
        else:
            extra_environ = None
        params = {'id': group_id, 'limit': 100}
        response = self.app.get("/api/action/group_activity_list",
                                params=params, extra_environ=extra_environ)
        assert response.json['success'] is True
        activities = response.json['result']
        return activities

    def recently_changed_datasets_stream(self, apikey=None):
        if apikey:
            extra_environ = {'Authorization': str(apikey)}
        else:
            extra_environ = None
        response = self.app.post(
                '/api/action/recently_changed_packages_activity_list',
                params=json.dumps({}),
                extra_environ=extra_environ,
                status=200)
        assert response.json['success'] is True
        activities = response.json['result']
        return activities

    def activity_details(self, activity):
        response = call_action('activity_detail_list', id=activity['id'])
        return response

    def record_details(self, user_id, package_id=None, group_ids=None,
            apikey=None):
        details = {}
        details['user activity stream'] = self.user_activity_stream(user_id,
                apikey)

        if package_id is not None:
            details['package activity stream'] = (
                    self.package_activity_stream(package_id, apikey))

        if group_ids is not None:
            details['group activity streams'] = {}
            for group_id in group_ids:
                details['group activity streams'][group_id] = (
                    self.group_activity_stream(group_id, apikey))

        details['recently changed datasets stream'] = \
                self.recently_changed_datasets_stream(apikey)

        details['time'] = datetime.datetime.utcnow()
        return details

    def _create_activity(self, user, package, params):
        before = self.record_details(user['id'], package['id'],
                apikey=user['apikey'])

        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user['apikey'])})
        assert response.json['success'] is True

        after = self.record_details(user['id'], package['id'],
                apikey=user['apikey'])

        # Find the new activity in the user's activity stream.
        user_new_activities = (find_new_activities(
            before['user activity stream'], after['user activity stream']))
        assert len(user_new_activities) == 1, ("There should be 1 new "
            " activity in the user's activity stream, but found %i" %
            len(user_new_activities))
        activity = user_new_activities[0]

        # The same new activity should appear in the package's activity stream.
        pkg_new_activities = (find_new_activities(
            before['package activity stream'],
            after['package activity stream']))
        assert pkg_new_activities == user_new_activities

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == params['object_id'], (
            str(activity['object_id']))
        assert activity['user_id'] == params['user_id'], (
            str(activity['user_id']))
        assert activity['activity_type'] == params['activity_type'], (
            str(activity['activity_type']))
        if 'id' not in activity:
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if 'revision_id' not in activity:
            assert False, "activity has no revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert (timestamp >= before['time'] and
                timestamp <= after['time']), str(activity['timestamp'])

    def test_activity_create_successful_no_data(self):
        """Test creating an activity via the API, without passing the optional
        data dict.

        """
        params = {
            'user_id': self.sysadmin_user['id'],
            'object_id': self.warandpeace['id'],
            'activity_type': 'changed package',
        }
        self._create_activity(self.sysadmin_user, self.warandpeace, params)

    def test_activity_create_successful_with_data(self):
        """Test creating an activity via the API, with the optional data dict.

        """
        params = {
            'user_id': self.sysadmin_user['id'],
            'object_id': self.annakarenina['id'],
            'activity_type': 'deleted package',
            'data': {'a': 1, 'b': 2, 'c': 3}
        }
        self._create_activity(self.sysadmin_user, self.annakarenina, params)

    def test_activity_create_no_authorization(self):
        """Test the error response when the activity_create API is called
        without an authorization header.

        """
        params = {
            'user_id': self.sysadmin_user['id'],
            'object_id': self.warandpeace['id'],
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params), status=403)
        assert response.json['success'] is False

    def test_activity_create_not_authorized(self):
        """Test the error response when the activity_create API is called
        with an authorization header for a user who is not authorized to
        create activities.

        """
        params = {
            'user_id': self.normal_user['id'],
            'object_id': self.warandpeace['id'],
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.normal_user['apikey'])},
            status=403)
        assert response.json['success'] is False

    def test_activity_create_authorization_not_exists(self):
        """Test the error response when the activity_create API is called
        with an authorization header with an API key that doesn't exist in the
        model.

        """
        params = {
            'user_id': self.normal_user['id'],
            'object_id': self.warandpeace['id'],
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': 'xxxxxxxxxx'},
            status=403)
        assert response.json['success'] is False

    def test_activity_create_with_id(self):
        """Test that an ID passed to the activity_create API is ignored and not
        used.

        """
        activity_id = '1234567890'
        user = self.sysadmin_user
        package = self.warandpeace
        params = {
            'id': activity_id,
            'user_id': user['id'],
            'object_id': package['id'],
            'activity_type': 'changed package',
        }
        self._create_activity(self.sysadmin_user, self.warandpeace, params)
        assert activity_id not in [activity['id'] for activity in
                self.user_activity_stream(user['id'])]
        assert activity_id not in [activity['id'] for activity in
                self.package_activity_stream(package['id'])]

    def test_activity_create_with_timestamp(self):
        """Test that a timestamp passed to the activity_create API is ignored
        and not used

        """
        params = {
            'user_id': self.sysadmin_user['id'],
            'object_id': self.warandpeace['id'],
            'activity_type': 'changed package',
            'timestamp': str(datetime.datetime.max),
        }
        self._create_activity(self.sysadmin_user, self.warandpeace, params)
        params['timestamp'] = 'foobar'
        self._create_activity(self.sysadmin_user, self.warandpeace, params)

    def test_activity_create_with_revision(self):
        """Test that a revision_id passed to the activity_create API is ignored
        and not used

        """
        revision_id = '1234567890'
        user = self.sysadmin_user
        package = self.warandpeace
        params = {
            'revision_id': revision_id,
            'user_id': user['id'],
            'object_id': package['id'],
            'activity_type': 'changed package',
        }
        self._create_activity(self.sysadmin_user, self.warandpeace, params)
        assert revision_id not in [activity['revision_id'] for activity in
                self.user_activity_stream(user['id'])]
        assert revision_id not in [activity['revision_id'] for activity in
                self.package_activity_stream(package['id'])]

    def test_activity_create_user_id_missing(self):
        """Test the error response when the activity_create API is called with
        no user ID.

        """
        params = {
            'object_id': self.warandpeace['id'],
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user['apikey'])},
            status=409)
        assert response.json['success'] is False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'user_id'] == [u'Missing value'], (
                response.json['error'][u'user_id'])

    def test_activity_create_user_id_empty(self):
        """Test the error response when the activity_create API is called with
        an empty user ID.

        """
        params = {
            'user_id': '',
            'object_id': self.warandpeace['id'],
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user['apikey'])},
            status=409)
        assert response.json['success'] is False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'user_id'] == [u'Missing value'], (
                response.json['error'][u'user_id'])

        params['user_id'] = None
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user['apikey'])},
            status=409)
        assert response.json['success'] is False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'user_id'] == [u'Missing value'], (
                response.json['error'][u'user_id'])

    def test_activity_create_user_id_does_not_exist(self):
        """Test the error response when the activity_create API is called with
        a user ID that doesn't exist in the model.

        """
        params = {
            'user_id': '1234567890abcdefghijk',
            'object_id': self.warandpeace['id'],
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user['apikey'])},
            status=409)
        assert response.json['success'] is False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'user_id'] == [
                u'Not found: User'], (
                response.json['error'][u'user_id'])

    def test_activity_create_object_id_missing(self):
        """Test the error response when the activity_create API is called with
        no object ID.

        """
        params = {
            'user_id': self.sysadmin_user['id'],
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user['apikey'])},
            status=409)
        assert response.json['success'] is False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'object_id'] == [
                u'Missing value'], (
                response.json['error'][u'user_id'])

    def test_activity_create_object_id_empty(self):
        """Test the error response when the activity_create API is called with
        an empty object ID.

        """
        params = {
            'object_id': '',
            'user_id': self.sysadmin_user['id'],
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user['apikey'])},
            status=409)
        assert response.json['success'] is False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'object_id'] == [
                u'Missing value'], (
                response.json['error'][u'user_id'])

        params['object_id'] = None
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user['apikey'])},
            status=409)
        assert response.json['success'] is False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'object_id'] == [
                u'Missing value'], (
                response.json['error'][u'user_id'])

    def test_activity_create_object_id_does_not_exist(self):
        """Test the error response when the activity_create API is called with
        a user ID that doesn't exist in the model.

        """
        params = {
            'object_id': '1234567890qwertyuiop',
            'user_id': self.sysadmin_user['id'],
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user['apikey'])},
            status=409)
        assert response.json['success'] is False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'object_id'] == [
                u'Not found: Dataset'], (
                response.json['error'][u'object_id'])

    def test_activity_create_activity_type_missing(self):
        """Test the error response when the activity_create API is called
        without an activity_type.

        """
        params = {
            'user_id': self.normal_user['id'],
            'object_id': self.warandpeace['id'],
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user['apikey'])},
            status=409)
        assert response.json['success'] is False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'object_id'] == [
                u'Missing value'], (
                response.json['error'][u'object_id'])

    def test_activity_create_activity_type_empty(self):
        """Test the error response when the activity_create API is called
        with an empty activity_type.

        """
        params = {
            'user_id': self.normal_user['id'],
            'object_id': self.warandpeace['id'],
            'activity_type': ''
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user['apikey'])},
            status=409)
        assert response.json['success'] is False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'activity_type'] == [
                u'Missing value'], (
                response.json['error'][u'activity_type'])

        params['activity_type'] = None
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user['apikey'])},
            status=409)
        assert response.json['success'] is False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'activity_type'] == [
                u'Missing value'], (
                response.json['error'][u'activity_type'])

    def test_activity_create_activity_type_not_exists(self):
        """Test the error response when the activity_create API is called
        with an activity_type that does not exist.

        """
        params = {
            'user_id': self.normal_user['id'],
            'object_id': self.warandpeace['id'],
            'activity_type': 'foobar'
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user['apikey'])},
            status=409)
        assert response.json['success'] is False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'activity_type'] == [
            u"Not found: Activity type"], (
                response.json['error'][u'activity_type'])

    def test_follow_dataset(self):
        user = self.sysadmin_user
        before = self.record_details(user['id'], self.warandpeace['id'],
                apikey=user['apikey'])
        data = {'id': self.warandpeace['id']}
        extra_environ = {'Authorization': str(user['apikey'])}
        response = self.app.post('/api/action/follow_dataset',
            json.dumps(data), extra_environ=extra_environ)
        response_dict = json.loads(response.body)
        assert response_dict['success'] is True

        after = self.record_details(user['id'], self.warandpeace['id'],
                apikey=user['apikey'])

        # Find the new activity in the user's activity stream.
        user_new_activities = (find_new_activities(
            before['user activity stream'], after['user activity stream']))
        assert len(user_new_activities) == 0, ("There should be 0 new "
            " activity in the user's activity stream, but found %i" %
            len(user_new_activities))

        # The rest of this test is commented out because 'follow dataset'
        # activities are disabled, even they are reenabled then uncomment it.

        #activity = user_new_activities[0]

        # The same new activity should appear in the package's activity stream.
        #pkg_new_activities = after['package activity stream']
        #for activity in user_new_activities:
        #    assert activity in pkg_new_activities

        # Check that the new activity has the right attributes.
        #assert activity['object_id'] == self.warandpeace['id'], \
        #    str(activity['object_id'])
        #assert activity['user_id'] == user['id'], str(activity['user_id'])
        #assert activity['activity_type'] == 'follow dataset', \
        #    str(activity['activity_type'])
        #if 'id' not in activity:
        #    assert False, "activity object should have an id value"
        # TODO: Test for the _correct_ revision_id value.
        #if 'revision_id' not in activity:
        #    assert False, "activity object should have a revision_id value"
        #timestamp = datetime_from_string(activity['timestamp'])
        #assert timestamp >= before['time'] and timestamp <= \
        #    after['time'], str(activity['timestamp'])

        #assert len(self.activity_details(activity)) == 0

    def test_follow_user(self):
        user = self.normal_user
        before = self.record_details(user['id'], apikey=user['apikey'])
        followee_before = self.record_details(self.sysadmin_user['id'],
                apikey=self.sysadmin_user['apikey'])
        data = {'id': self.sysadmin_user['id']}
        extra_environ = {'Authorization': str(user['apikey'])}
        response = self.app.post('/api/action/follow_user',
            json.dumps(data), extra_environ=extra_environ)
        response_dict = json.loads(response.body)
        assert response_dict['success'] is True

        after = self.record_details(user['id'], apikey=user['apikey'])
        followee_after = self.record_details(self.sysadmin_user['id'],
                apikey=self.sysadmin_user['apikey'])

        # Find the new activity in the user's activity stream.
        user_new_activities = (find_new_activities(
            before['user activity stream'], after['user activity stream']))
        assert len(user_new_activities) == 0, ("There should be 0 new "
            " activities in the user's activity stream, but found %i" %
            len(user_new_activities))

        # The rest of this test is commented out because follow_user activities
        # are disabled, uncomment it if they're enabled again.

        #activity = user_new_activities[0]

        # Check that the new activity has the right attributes.
        #assert activity['object_id'] == self.sysadmin_user['id'], \
        #    str(activity['object_id'])
        #assert activity['user_id'] == user['id'], str(activity['user_id'])
        #assert activity['activity_type'] == 'follow user', \
        #    str(activity['activity_type'])
        #if 'id' not in activity:
        #    assert False, "activity object should have an id value"
        # TODO: Test for the _correct_ revision_id value.

        #if 'revision_id' not in activity:
        #    assert False, "activity object should have a revision_id value"
        #timestamp = datetime_from_string(activity['timestamp'])
        #assert timestamp >= before['time'] and timestamp <= \
        #    after['time'], str(activity['timestamp'])

        #assert len(self.activity_details(activity)) == 0

    def test_user_activity_list_by_name(self):
        '''user_activity_list should accept a user name as param.'''
        activities = tests.call_action_api(self.app, 'user_activity_list',
                id='annafan')
        assert len(activities) > 0

    def test_package_activity_list_by_name(self):
        '''package_activity_list should accept a package name as param.'''
        activities = tests.call_action_api(self.app,
                'package_activity_list', id='warandpeace',
                apikey=self.sysadmin_user['apikey'])
        assert len(activities) > 0

    def test_group_activity_list_by_name(self):
        '''group_activity_list should accept a group name as param.'''
        activities = tests.call_action_api(self.app,
                'group_activity_list', id='roger')
        assert len(activities) > 0

    def test_organization_activity_list_by_name(self):
        '''organization_activity_list should accept a org name as param.'''
        organization = tests.call_action_api(self.app,
                'organization_create', name='test_org',
                apikey=self.sysadmin_user['apikey'])
        activities = tests.call_action_api(self.app,
                'organization_activity_list', id=organization['name'])
        assert len(activities) > 0

    def test_no_activity_when_creating_private_dataset(self):
        '''There should be no activity when a private dataset is created.'''

        user = self.normal_user
        organization = tests.call_action_api(self.app, 'organization_create',
                name='another_test_org', apikey=user['apikey'])
        dataset = tests.call_action_api(self.app, 'package_create',
                apikey=user['apikey'],
                name='test_private_dataset',
                owner_org=organization['id'], private=True)
        activity_stream = tests.call_action_api(self.app,
                'package_activity_list', id=dataset['id'],
                apikey=user['apikey'])
        assert activity_stream == []

    def test_no_activity_when_updating_private_dataset(self):
        '''There should be no activity when a private dataset is created.'''

        user = self.normal_user
        organization = tests.call_action_api(self.app, 'organization_create',
                name='test_org_3', apikey=user['apikey'])
        dataset = tests.call_action_api(self.app, 'package_create',
                apikey=user['apikey'],
                name='test_private_dataset_2',
                owner_org=organization['id'], private=True)
        dataset['notes'] = 'updated'
        updated_dataset = tests.call_action_api(self.app, 'package_update',
                apikey=user['apikey'], **dataset)
        activity_stream = tests.call_action_api(self.app,
                'package_activity_list', id=dataset['id'],
                apikey=user['apikey'])
        assert activity_stream == []

    def test_no_activity_when_deleting_private_dataset(self):
        '''There should be no activity when a private dataset is created.'''

        user = self.normal_user
        organization = tests.call_action_api(self.app, 'organization_create',
                name='test_org_4', apikey=user['apikey'])
        dataset = tests.call_action_api(self.app, 'package_create',
                apikey=user['apikey'],
                name='test_private_dataset_3',
                owner_org=organization['id'], private=True)
        deleted_dataset = tests.call_action_api(self.app, 'package_delete',
                apikey=user['apikey'], id=dataset['id'])
        activity_stream = tests.call_action_api(self.app,
                'package_activity_list', id=dataset['id'],
                apikey=user['apikey'])
        assert activity_stream == []
