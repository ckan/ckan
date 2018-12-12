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
from ckan.tests.helpers import call_action


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
        self.app = paste.fixture.TestApp(pylons.test.pylonsapp)

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

    def _create_package(self, user, name=None):
        if user:
            user_id = user['id']
            apikey = user['apikey']
        else:
            user_id = 'not logged in'
            apikey = None

        before = self.record_details(user_id, apikey=apikey)

        # Create a new package.
        request_data = make_package(name)

        before = self.record_details(user_id=user_id,
                group_ids=[group['name'] for group in request_data['groups']],
                apikey=apikey)
        extra_environ = {'Authorization': str(user['apikey'])}

        call_action('member_create',
                    capacity='admin',
                    object=user['id'],
                    object_type='user',
                    id='roger')
        response = self.app.post('/api/action/package_create',
                json.dumps(request_data), extra_environ=extra_environ)
        response_dict = json.loads(response.body)
        assert response_dict['success'] is True
        package_created = response_dict['result']

        after = self.record_details(user_id=user_id,
            package_id=package_created['id'],
            group_ids=[group['name'] for group in package_created['groups']],
            apikey=apikey)

        # Find the new activity in the user's activity stream.
        user_new_activities = (find_new_activities(
            before['user activity stream'], after['user activity stream']))
        assert len(user_new_activities) == 1, ("There should be 1 new "
            " activity in the user's activity stream, but found %i" %
            len(user_new_activities))
        activity = user_new_activities[0]

        # The same new activity should appear in the package's activity stream.
        pkg_new_activities = after['package activity stream']
        assert pkg_new_activities == [activity]

        # The same new activity should appear in the recently changed datasets
        # stream.
        new_rcd_activities = find_new_activities(
                before['recently changed datasets stream'],
                after['recently changed datasets stream'])
        assert new_rcd_activities == [activity]

        # The same new activity should appear in the activity streams of the
        # package's groups.
        for group_dict in package_created['groups']:
            grp_new_activities = find_new_activities(
                before['group activity streams'][group_dict['name']],
                after['group activity streams'][group_dict['name']])
            assert [activity['id'] for activity in grp_new_activities] == [
                    activity['id']]

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == package_created['id'], \
            str(activity['object_id'])
        assert activity['user_id'] == user_id, str(activity['user_id'])
        assert activity['activity_type'] == 'new package', \
            str(activity['activity_type'])
        if 'id' not in activity:
            assert False, "activity object should have an id value"
        # TODO: Test for the _correct_ revision_id value.
        if 'revision_id' not in activity:
            assert False, "activity object should have a revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert timestamp >= before['time'] and timestamp <= \
            after['time'], str(activity['timestamp'])

        details = self.activity_details(activity)
        # There should be five activity details: one for the package itself,
        # one for each of its two resources, and one for each of its two tags.

        assert len(details) == 5, "There should be five activity details."

        detail_ids = [detail['object_id'] for detail in details]
        assert detail_ids.count(package_created['id']) == 1, (
            "There should be one activity detail for the package itself.")
        for resource in package_created['resources']:
            assert detail_ids.count(resource['id']) == 1, (
                "There should be one activity detail for each of the "
                "package's resources")

        for detail in details:
            assert detail['activity_id'] == activity['id'], \
                str(detail['activity_id'])

            if detail['object_id'] == package_created['id']:
                assert detail['activity_type'] == "new", (
                    str(detail['activity_type']))
                assert detail['object_type'] == "Package", \
                    str(detail['object_type'])

            elif (detail['object_id'] in
                [resource['id'] for resource in package_created['resources']]):
                assert detail['activity_type'] == "new", (
                    str(detail['activity_type']))
                assert detail['object_type'] == "Resource", (
                    str(detail['object_type']))

            else:
                assert detail['activity_type'] == "added", (
                    str(detail['activity_type']))
                assert detail['object_type'] == "tag", (
                    str(detail['object_type']))

    def _add_resource(self, package, user):
        if user:
            user_id = user['id']
            apikey = user['apikey']
        else:
            user_id = 'not logged in'
            apikey = None

        before = self.record_details(user_id, package['id'],
                [group['name'] for group in package['groups']], apikey=apikey)

        resource_ids_before = [resource['id'] for resource in
                package['resources']]

        # Create a new resource.
        resources = package['resources']
        resources.append(make_resource())
        updated_package = package_update(self.app, package, user)

        after = self.record_details(user_id, package['id'],
                [group['name'] for group in package['groups']], apikey=apikey)
        resource_ids_after = [resource['id'] for resource in
                updated_package['resources']]
        assert len(resource_ids_after) == len(resource_ids_before) + 1

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

        # The same new activity should appear in the recently changed datasets
        # stream.
        assert find_new_activities(
                before['recently changed datasets stream'],
                after['recently changed datasets stream']) \
                        == user_new_activities

        # If the package has any groups, the same new activity should appear
        # in the activity stream of each group.
        for group_dict in package['groups']:
            grp_new_activities = find_new_activities(
                before['group activity streams'][group_dict['name']],
                after['group activity streams'][group_dict['name']])
            assert grp_new_activities == [activity]

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == updated_package['id'], \
            str(activity['object_id'])
        assert activity['user_id'] == user_id, str(activity['user_id'])
        assert activity['activity_type'] == 'changed package', \
            str(activity['activity_type'])
        if 'id' not in activity:
            assert False, "activity object should have an id value"
        # TODO: Test for the _correct_ revision_id value.
        if 'revision_id' not in activity:
            assert False, "activity object should have a revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert (timestamp >= before['time'] and
                timestamp <= after['time']), str(activity['timestamp'])

        # Test for the presence of a correct activity detail item.
        details = self.activity_details(activity)
        assert len(details) == 1, [(detail['activity_type'],
            detail['object_type']) for detail in details]
        detail = details[0]
        assert detail['activity_id'] == activity['id'], \
            str(detail['activity_id'])
        new_resource_ids = [id for id in resource_ids_after if id not in
            resource_ids_before]
        assert len(new_resource_ids) == 1
        new_resource_id = new_resource_ids[0]
        assert detail['object_id'] == new_resource_id, (
            str(detail['object_id']))
        assert detail['object_type'] == "Resource", (
            str(detail['object_type']))
        assert detail['activity_type'] == "new", (
            str(detail['activity_type']))

    def _delete_extra(self, package_dict, user):
        if user:
            user_id = user['id']
            apikey = user['apikey']
        else:
            user_id = 'not logged in'
            apikey = None

        before = self.record_details(user_id, package_dict['id'],
                [group['name'] for group in package_dict['groups']],
                apikey=apikey)

        extras_before = list(package_dict['extras'])
        assert len(extras_before) > 0, (
                "Can't update an extra if the package doesn't have any")

        # Update the package's first extra.
        del package_dict['extras'][0]
        updated_package = package_update(self.app, package_dict, user)

        after = self.record_details(user_id, package_dict['id'],
                [group['name'] for group in package_dict['groups']],
                apikey=apikey)
        extras_after = updated_package['extras']
        assert len(extras_after) == len(extras_before) - 1, (
                "%s != %s" % (len(extras_after), len(extras_before) - 1))

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

        # The same new activity should appear in the recently changed datasets
        # stream.
        assert find_new_activities(
                before['recently changed datasets stream'],
                after['recently changed datasets stream']) \
                        == user_new_activities

        # If the package has any groups, the same new activity should appear
        # in the activity stream of each group.
        for group_dict in package_dict['groups']:
            grp_new_activities = find_new_activities(
                before['group activity streams'][group_dict['name']],
                after['group activity streams'][group_dict['name']])
            assert grp_new_activities == [activity]

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == updated_package['id'], \
            str(activity['object_id'])
        assert activity['user_id'] == user_id, str(activity['user_id'])
        assert activity['activity_type'] == 'changed package', \
            str(activity['activity_type'])
        if 'id' not in activity:
            assert False, "activity object should have an id value"
        # TODO: Test for the _correct_ revision_id value.
        if 'revision_id' not in activity:
            assert False, "activity object should have a revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert (timestamp >= before['time'] and
                timestamp <= after['time']), str(activity['timestamp'])

        # Test for the presence of a correct activity detail item.
        details = self.activity_details(activity)
        assert len(details) == 1, (
                "There should be 1 activity detail but found %s"
                % len(details))
        detail = details[0]
        assert detail['activity_id'] == activity['id'], \
            str(detail['activity_id'])
        deleted_extras = [extra for extra in extras_before if extra not in
                extras_after]
        assert len(deleted_extras) == 1, "%s != 1" % len(deleted_extras)
        deleted_extra = deleted_extras[0]
        assert detail['object_type'] == "PackageExtra", (
            str(detail['object_type']))
        assert detail['activity_type'] == "deleted", (
            str(detail['activity_type']))

    def _update_extra(self, package_dict, user):
        if user:
            user_id = user['id']
            apikey = user['apikey']
        else:
            user_id = 'not logged in'
            apikey=None

        before = self.record_details(user_id, package_dict['id'],
                [group['name'] for group in package_dict['groups']],
                apikey=apikey)

        import copy
        extras_before = copy.deepcopy(package_dict['extras'])
        assert len(extras_before) > 0, (
                "Can't update an extra if the package doesn't have any")

        # Update the package's first extra.
        if package_dict['extras'][0]['value'] != '"edited"':
            package_dict['extras'][0]['value'] = '"edited"'
        else:
            assert package_dict['extras'][0]['value'] != '"edited again"'
            package_dict['extras'][0]['value'] = '"edited again"'
        updated_package = package_update(self.app, package_dict, user)

        after = self.record_details(user_id, package_dict['id'],
                [group['name'] for group in package_dict['groups']],
                apikey=apikey)
        extras_after = updated_package['extras']
        assert len(extras_after) == len(extras_before), (
                "%s != %s" % (len(extras_after), len(extras_before)))

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

        # The same new activity should appear in the recently changed datasets
        # stream.
        assert find_new_activities(
                before['recently changed datasets stream'],
                after['recently changed datasets stream']) \
                        == user_new_activities

        # If the package has any groups, the same new activity should appear
        # in the activity stream of each group.
        for group_dict in package_dict['groups']:
            grp_new_activities = find_new_activities(
                before['group activity streams'][group_dict['name']],
                after['group activity streams'][group_dict['name']])
            assert grp_new_activities == [activity]

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == updated_package['id'], \
            str(activity['object_id'])
        assert activity['user_id'] == user_id, str(activity['user_id'])
        assert activity['activity_type'] == 'changed package', \
            str(activity['activity_type'])
        if 'id' not in activity:
            assert False, "activity object should have an id value"
        # TODO: Test for the _correct_ revision_id value.
        if 'revision_id' not in activity:
            assert False, "activity object should have a revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert (timestamp >= before['time'] and
                timestamp <= after['time']), str(activity['timestamp'])

        # Test for the presence of a correct activity detail item.
        details = self.activity_details(activity)
        assert len(details) == 1, (
                "There should be 1 activity detail but found %s"
                % len(details))
        detail = details[0]
        assert detail['activity_id'] == activity['id'], \
            str(detail['activity_id'])
        new_extras = [extra for extra in extras_after if extra not in
                extras_before]
        assert len(new_extras) == 1, "%s != 1" % len(new_extras)
        new_extra = new_extras[0]
        assert detail['object_type'] == "PackageExtra", (
            str(detail['object_type']))
        assert detail['activity_type'] == "changed", (
            str(detail['activity_type']))

    def _add_extra(self, package_dict, user, key=None):
        if key is None:
            key = 'quality'
        if user:
            user_id = user['id']
            apikey = user['apikey']
        else:
            user_id = 'not logged in'
            apikey = None

        before = self.record_details(user_id, package_dict['id'],
                [group['name'] for group in package_dict['groups']],
                apikey=apikey)

        # Make a copy of the package's extras before we add a new extra,
        # so we can compare the extras before and after updating the package.
        extras_before = list(package_dict['extras'])

        # Create a new extra.
        extras = package_dict['extras']
        extras.append({'key': key, 'value': '10000'})
        updated_package = package_update(self.app, package_dict, user)

        after = self.record_details(user_id, package_dict['id'],
                [group['name'] for group in package_dict['groups']],
                apikey=apikey)
        extras_after = updated_package['extras']
        assert len(extras_after) == len(extras_before) + 1, (
                "%s != %s" % (len(extras_after), len(extras_before) + 1))

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

        # The same new activity should appear in the recently changed datasets
        # stream.
        assert find_new_activities(
                before['recently changed datasets stream'],
                after['recently changed datasets stream']) \
                        == user_new_activities

        # If the package has any groups, the same new activity should appear
        # in the activity stream of each group.
        for group_dict in package_dict['groups']:
            grp_new_activities = find_new_activities(
                before['group activity streams'][group_dict['name']],
                after['group activity streams'][group_dict['name']])
            assert grp_new_activities == [activity]

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == updated_package['id'], \
            str(activity['object_id'])
        assert activity['user_id'] == user_id, str(activity['user_id'])
        assert activity['activity_type'] == 'changed package', \
            str(activity['activity_type'])
        if 'id' not in activity:
            assert False, "activity object should have an id value"
        # TODO: Test for the _correct_ revision_id value.
        if 'revision_id' not in activity:
            assert False, "activity object should have a revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert (timestamp >= before['time'] and
                timestamp <= after['time']), str(activity['timestamp'])

        # Test for the presence of a correct activity detail item.
        details = self.activity_details(activity)
        assert len(details) == 1, (
                "There should be 1 activity detail but found %s"
                % len(details))
        detail = details[0]
        assert detail['activity_id'] == activity['id'], \
            str(detail['activity_id'])
        new_extras = [extra for extra in extras_after if extra not in
                extras_before]
        assert len(new_extras) == 1, "%s != 1" % len(new_extras)
        new_extra = new_extras[0]
        assert detail['object_type'] == "PackageExtra", (
            str(detail['object_type']))
        assert detail['activity_type'] == "new", (
            str(detail['activity_type']))

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

    def _delete_group(self, group, user):
        """
        Delete the given group and test that the correct activity stream
        item and detail are emitted.

        """
        before = self.record_details(user['id'], group_ids=[group['id']],
                apikey=user['apikey'])

        # Deleted the group.
        group_dict = {'id': group['id'], 'state': 'deleted'}
        group_update(self.app, group_dict, user['apikey'])

        after = self.record_details(user['id'], group_ids=[group['id']],
                apikey=user['apikey'])

        # Find the new activity.
        new_activities = find_new_activities(before['user activity stream'],
            after['user activity stream'])
        assert len(new_activities) == 1, ("There should be 1 new activity in "
            "the user's activity stream, but found %i" % len(new_activities))
        activity = new_activities[0]

        assert find_new_activities(
                before["group activity streams"][group['id']],
                after['group activity streams'][group['id']]) == \
                        new_activities, ("The same activity should also "
                        "appear in the group's activity stream.")

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == group['id'], str(activity['object_id'])
        assert activity['user_id'] == user['id'], str(activity['user_id'])
        assert activity['activity_type'] == 'deleted group', \
            str(activity['activity_type'])
        if 'id' not in activity:
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if 'revision_id' not in activity:
            assert False, "activity has no revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert timestamp >= before['time'] and timestamp <= after['time'], \
            str(activity['timestamp'])

        # Tidy up - undelete the group for following tests
        group_dict = {'id': group['id'], 'state': 'active'}
        group_update(self.app, group_dict, user['apikey'])

    def _update_group(self, group, user):
        """
        Update the given group and test that the correct activity stream
        item and detail are emitted.

        """
        before = self.record_details(user['id'], group_ids=[group['id']],
                apikey=user['apikey'])

        # Update the group.
        group_dict = {'id': group['id'], 'title': 'edited'}
        group_update(self.app, group_dict, user['apikey'])

        after = self.record_details(user['id'], group_ids=[group['id']],
                apikey=user['apikey'])

        # Find the new activity.
        new_activities = find_new_activities(before['user activity stream'],
            after['user activity stream'])
        assert len(new_activities) == 1, ("There should be 1 new activity in "
            "the user's activity stream, but found %i" % len(new_activities))
        activity = new_activities[0]

        assert find_new_activities(
                before["group activity streams"][group['id']],
                after['group activity streams'][group['id']]) == \
                        new_activities, ("The same activity should also "
                        "appear in the group's activity stream.")

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == group['id'], str(activity['object_id'])
        assert activity['user_id'] == user['id'], str(activity['user_id'])
        assert activity['activity_type'] == 'changed group', \
            str(activity['activity_type'])
        if 'id' not in activity:
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if 'revision_id' not in activity:
            assert False, "activity has no revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert timestamp >= before['time'] and timestamp <= after['time'], \
            str(activity['timestamp'])

    def _delete_resources(self, package):
        """
        Remove all resources (if any) from the given package, and test that
        correct activity item and detail items are emitted.

        """
        before = self.record_details(self.normal_user['id'], package['id'],
                [group['name'] for group in package['groups']],
                apikey=self.normal_user['apikey'])

        num_resources = len(package['resources'])
        assert num_resources > 0, \
                "Cannot delete resources if there aren't any."
        resource_ids = [resource['id'] for resource in package['resources']]

        package['resources'] = []
        package_update(self.app, package, self.normal_user)

        after = self.record_details(self.normal_user['id'], package['id'],
                [group['name'] for group in package['groups']],
                apikey=self.normal_user['apikey'])

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

        # The same new activity should appear in the recently changed datasets
        # stream.
        assert find_new_activities(
                before['recently changed datasets stream'],
                after['recently changed datasets stream']) \
                        == user_new_activities

        # If the package has any groups, the same new activity should appear
        # in the activity stream of each group.
        for group_dict in package['groups']:
            grp_new_activities = find_new_activities(
                before['group activity streams'][group_dict['name']],
                after['group activity streams'][group_dict['name']])
            assert grp_new_activities == [activity]

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == package['id'], (
            str(activity['object_id']))
        assert activity['user_id'] == self.normal_user['id'], (
            str(activity['user_id']))
        assert activity['activity_type'] == 'changed package', (
            str(activity['activity_type']))
        if 'id' not in activity:
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if 'revision_id' not in activity:
            assert False, "activity has no revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert timestamp >= before['time'], str(activity['timestamp'])
        assert timestamp <= after['time'], str(activity['timestamp'])

        # Test for the presence of correct activity detail items.
        details = self.activity_details(activity)
        assert len(details) == num_resources
        for detail in details:
            assert detail['activity_id'] == activity['id'], (
                "activity_id should be %s but is %s"
                % (activity['id'], detail['activity_id']))
            assert detail['object_id'] in resource_ids, (
                str(detail['object_id']))
            assert detail['object_type'] == "Resource", (
                str(detail['object_type']))
            assert detail['activity_type'] == "deleted", (
                str(detail['activity_type']))

    def _update_package(self, package, user):
        """
        Update the given package and test that the correct activity stream
        item and detail are emitted.

        """
        if user:
            user_id = user['id']
            apikey = user['apikey']
        else:
            user_id = 'not logged in'
            apikey = None

        group_ids = [group['name'] for group in package['groups']]
        before = self.record_details(
            user_id, package['id'], apikey=apikey, group_ids=group_ids
        )

        # Update the package.
        if package['title'] != 'edited':
            package['title'] = 'edited'
        else:
            assert package['title'] != 'edited again'
            package['title'] = 'edited again'
        package_update(self.app, package, user)

        after = self.record_details(
            user_id, package['id'], apikey=apikey, group_ids=group_ids
        )

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

        # The same new activity should appear in the recently changed datasets
        # stream.
        assert find_new_activities(
                before['recently changed datasets stream'],
                after['recently changed datasets stream']) \
                        == user_new_activities

        # If the package has any groups, the same new activity should appear
        # in the activity stream of each group.
        for group_dict in package['groups']:
            grp_new_activities = find_new_activities(
                before['group activity streams'][group_dict['name']],
                after['group activity streams'][group_dict['name']])
            assert grp_new_activities == [activity]

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == package['id'], (
            str(activity['object_id']))
        assert activity['user_id'] == user_id, str(activity['user_id'])
        assert activity['activity_type'] == 'changed package', (
            str(activity['activity_type']))
        if 'id' not in activity:
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if 'revision_id' not in activity:
            assert False, "activity has no revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert (timestamp >= before['time'] and
                timestamp <= after['time']), str(activity['timestamp'])

        # Test for the presence of a correct activity detail item.
        details = self.activity_details(activity)
        assert len(details) == 1
        detail = details[0]
        assert detail['activity_id'] == activity['id'], \
            str(detail['activity_id'])
        assert detail['object_id'] == package['id'], str(detail['object_id'])
        assert detail['object_type'] == "Package", (
            str(detail['object_type']))
        assert detail['activity_type'] == "changed", (
            str(detail['activity_type']))

    def _update_resource(self, package, resource, user):
        """
        Update the given resource and test that the correct activity stream
        item and detail are emitted.

        """
        if user:
            user_id = user['id']
            apikey = user['apikey']
        else:
            user_id = 'not logged in'
            apikey = None

        before = self.record_details(user_id, package['id'], apikey=apikey)

        # Update the resource.
        resource['name'] = 'edited'
        package_update(self.app, package, user)

        after = self.record_details(user_id, package['id'], apikey=apikey)

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

        # The same new activity should appear in the recently changed datasets
        # stream.
        assert find_new_activities(
                before['recently changed datasets stream'],
                after['recently changed datasets stream']) \
                        == user_new_activities

        # If the package has any groups, the same new activity should appear
        # in the activity stream of each group.
        for group_dict in package['groups']:
            grp_new_activities = find_new_activities(
                before['group activity streams'][group_dict['name']],
                after['group activity streams'][group_dict['name']])
            assert grp_new_activities == [activity]

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == package['id'], (
            str(activity['object_id']))
        assert activity['user_id'] == user_id, str(activity['user_id'])
        assert activity['activity_type'] == 'changed package', (
            str(activity['activity_type']))
        if not activity['id']:
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity['revision_id']:
            assert False, "activity has no revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert (timestamp >= before['time'] and
                timestamp <= after['time']), str(activity['timestamp'])

        # Test for the presence of a correct activity detail item.
        details = self.activity_details(activity)
        assert len(details) == 1
        detail = details[0]
        assert detail['activity_id'] == activity['id'], (
            str(detail['activity_id']))
        assert detail['object_id'] == resource.id, str(detail['object_id'])
        assert detail['object_type'] == "Resource", (
            str(detail['object_type']))
        assert detail['activity_type'] == "changed", (
            str(detail['activity_type']))

    def _delete_package(self, package):
        """
        Delete the given package and test that the correct activity stream
        item and detail are emitted.

        """
        group_ids = [group['name'] for group in package['groups']]
        before = self.record_details(
            self.sysadmin_user['id'], package['id'],
            apikey=self.sysadmin_user['apikey'], group_ids=group_ids
        )
        # Delete the package.
        package_dict = {'id': package['id']}
        response = self.app.post('/api/action/package_delete',
            json.dumps(package_dict),
            extra_environ={'Authorization': str(self.sysadmin_user['apikey'])})
        response_dict = json.loads(response.body)
        assert response_dict['success'] is True

        after = self.record_details(
            self.sysadmin_user['id'], package['id'],
            apikey=self.sysadmin_user['apikey'], group_ids=group_ids
        )

        # Find the new activity in the user's activity stream.
        user_new_activities = (find_new_activities(
            before['user activity stream'], after['user activity stream']))
        assert len(user_new_activities) == 1, ("There should be 1 new "
            " activity in the user's activity stream, but found %i" %
            len(user_new_activities))
        activity = user_new_activities[0]

        # The same new activity should appear in the package's stream.
        pkg_new_activities = (find_new_activities(
            before['package activity stream'],
            after['package activity stream']))
        assert pkg_new_activities == user_new_activities

        # The same new activity should appear in the recently changed datasets
        # stream.
        assert find_new_activities(
                before['recently changed datasets stream'],
                after['recently changed datasets stream']) \
                        == user_new_activities

        # If the package has any groups, there should be no new activities
        # because package has been deleted == removed from group lifecycle

        for group_dict in package['groups']:
            grp_new_activities = find_new_activities(
                before['group activity streams'][group_dict['name']],
                after['group activity streams'][group_dict['name']])
            assert grp_new_activities == []

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == package['id'], (
                str(activity['object_id']))
        assert activity['user_id'] == self.sysadmin_user['id'], (
            str(activity['user_id']))
        assert activity['activity_type'] == 'deleted package', (
            str(activity['activity_type']))
        if 'id' not in activity:
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if 'revision_id' not in activity:
            assert False, "activity has no revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert (timestamp >= before['time'] and
                timestamp <= after['time']), str(activity['timestamp'])

        # Test for the presence of a correct activity detail item.
        details = self.activity_details(activity)
        assert len(details) == 1
        detail = details[0]
        assert detail['activity_id'] == activity['id'], \
            str(detail['activity_id'])
        assert detail['object_id'] == package['id'], str(detail['object_id'])
        assert detail['object_type'] == "Package", (
            str(detail['object_type']))
        assert detail['activity_type'] == "deleted", (
            str(detail['activity_type']))

    def test_01_delete_resources(self):
        """
        Test deleted resource activity stream.

        Test that correct activity stream item and detail items are created
        when resources are deleted from packages.

        """
        packages_with_resources = []
        for package_name in package_list(self.app):
            package_dict = package_show(self.app, {'id': package_name})
            if len(package_dict['resources']) > 0:
                packages_with_resources.append(package_dict)
        assert len(packages_with_resources) > 0, \
                "Need some packages with resources to test deleting resources."
        for package in packages_with_resources:
            self._delete_resources(package)

    def test_01_update_group(self):
        """
        Test updated group activity stream.

        Test that correct activity stream item and detail items are created
        when groups are updated.

        """
        for group in group_list(self.app):
            self._update_group(group, user=self.sysadmin_user)

    def test_01_remove_tag(self):
        """
        Test remove tag activity.

        If a package is updated by removing one tag from it, a
        'changed package' activity with a single 'removed tag' activity detail
        should be emitted.

        """
        # Get a package.
        user = self.normal_user
        pkg_name = u"warandpeace"
        pkg_dict = package_show(self.app, {'id': pkg_name}, user['apikey'])

        # Remove one tag from the package.
        assert len(pkg_dict['tags']) >= 1, ("The package has to have at least"
                " one tag to test removing a tag.")
        before = self.record_details(user['id'], pkg_dict['id'],
                [group['name'] for group in pkg_dict['groups']],
                apikey=user['apikey'])
        data_dict = {
            'id': pkg_dict['id'],
            'tags': pkg_dict['tags'][0:-1],
            }
        package_update(self.app, data_dict, user)
        after = self.record_details(user['id'], pkg_dict['id'],
                [group['name'] for group in pkg_dict['groups']],
                apikey=user['apikey'])

        # Find the new activity in the user's activity stream.
        user_new_activities = (find_new_activities(
            before['user activity stream'], after['user activity stream']))
        assert len(user_new_activities) == 1, ("There should be 1 new "
            " activity in the user's activity stream, but found %i" %
            len(user_new_activities))
        activity = user_new_activities[0]

        # The same new activity should appear in the package's stream.
        pkg_new_activities = (find_new_activities(
            before['package activity stream'],
            after['package activity stream']))
        assert pkg_new_activities == user_new_activities

        # The same new activity should appear in the recently changed datasets
        # stream.
        assert find_new_activities(
                before['recently changed datasets stream'],
                after['recently changed datasets stream']) \
                        == user_new_activities

        # If the package has any groups, the same new activity should appear
        # in the activity stream of each group.
        for group_dict in pkg_dict['groups']:
            grp_new_activities = find_new_activities(
                before['group activity streams'][group_dict['name']],
                after['group activity streams'][group_dict['name']])
            assert grp_new_activities == [activity]

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == pkg_dict['id'], (
            str(activity['object_id']))
        assert activity['user_id'] == user['id'], str(activity['user_id'])
        assert activity['activity_type'] == 'changed package', (
            str(activity['activity_type']))
        if 'id' not in activity:
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if 'revision_id' not in activity:
            assert False, "activity has no revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert (timestamp >= before['time'] and
                timestamp <= after['time']), str(activity['timestamp'])

        # Test for the presence of a correct activity detail item.
        details = self.activity_details(activity)
        assert len(details) == 1
        detail = details[0]
        assert detail['activity_id'] == activity['id'], \
            str(detail['activity_id'])
        assert detail['object_type'] == "tag", (
            str(detail['object_type']))
        assert detail['activity_type'] == "removed", (
            str(detail['activity_type']))

    def test_01_update_extras(self):
        """
        Test changed package extra activity stream.

        Test that correct activity stream item and detail items are emitted
        when a package extra is changed.

        """
        packages_with_extras = []
        for package_name in package_list(self.app):
            package_dict = package_show(self.app, {'id': package_name})
            if len(package_dict['extras']) > 0:
                    packages_with_extras.append(package_dict)
        assert len(packages_with_extras) > 0, (
                "Need some packages with extras to test")
        for package_dict in packages_with_extras:
            self._update_extra(package_dict, user=self.normal_user)

    def test_01_update_package(self):
        """
        Test updated package activity stream.

        Test that correct activity stream item and detail items are created
        when packages are updated.

        """
        for package_name in package_list(self.app):
            package_dict = package_show(self.app, {'id': package_name})
            self._update_package(package_dict, user=self.normal_user)

    def test_01_update_resource(self):
        """
        Test that a correct activity stream item and detail item are emitted
        when a resource is updated.

        """
        for package_name in package_list(self.app):
            package_dict = package_show(self.app, {'id': package_name})
            for resource in package_dict['resources']:
                self._update_resource(package_dict, resource,
                        user=self.normal_user)

    def test_01_update_resource_not_logged_in(self):
        """
        Test that a correct activity stream item and detail item are emitted
        when a resource is updated by a user who is not logged in.

        """
        for package_name in package_list(self.app):
            package_dict = package_show(self.app, {'id': package_name})
            for resource in package_dict['resources']:
                self._update_resource(package_dict, resource, user=None)

    def test_create_package(self):
        """
        Test new package activity stream.

        Test that correct activity stream item and detail items are emitted
        when a new package is created.

        """
        self._create_package(user=self.normal_user)

    def test_add_resources(self):
        """
        Test new resource activity stream.

        Test that correct activity stream item and detail items are emitted
        when a resource is added to a package.

        """
        for package_name in package_list(self.app):
            package_dict = package_show(self.app, {'id': package_name})
            self._add_resource(package_dict, user=self.normal_user)

    def test_delete_package(self):
        """
        Test deleted package activity stream.

        Test that correct activity stream item and detail items are created
        when packages are deleted.

        """
        for package_name in package_list(self.app):
            package_dict = package_show(self.app, {'id': package_name})
            self._delete_package(package_dict)

    def test_create_user(self):
        """
        Test new user activity stream.

        Test that correct activity stream item and detail item are created when
        a new user is created.

        """
        before = datetime.datetime.utcnow()

        # Create a new user.
        user_dict = {'name': 'testuser',
                'about': 'Just a test user', 'email': 'me@test.org',
                'password': 'TestPassword1'}
        response = self.app.post('/api/action/user_create',
            json.dumps(user_dict),
            extra_environ={'Authorization': str(self.sysadmin_user['apikey'])})
        response_dict = json.loads(response.body)
        assert response_dict['success'] is True
        user_created = response_dict['result']

        after = self.record_details(user_created['id'],
                apikey=user_created['apikey'])

        user_activities = after['user activity stream']
        assert len(user_activities) == 1, ("There should be 1 activity in "
            "the user's activity stream, but found %i" % len(user_activities))
        activity = user_activities[0]

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == user_created['id'], \
            str(activity['object_id'])
        assert activity['user_id'] == user_created['id'], \
            str(activity['user_id'])
        assert activity['activity_type'] == 'new user', \
            str(activity['activity_type'])
        if 'id' not in activity:
            assert False, "activity object should have an id value"
        # TODO: Test for the _correct_ revision_id value.
        if 'revision_id' not in activity:
            assert False, "activity object should have a revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert timestamp >= before and timestamp <= after['time'], \
            str(activity['timestamp'])

        details = self.activity_details(activity)
        assert len(details) == 0, ("There shouldn't be any activity details"
                " for a 'new user' activity")

    def test_create_group(self):

        user = self.normal_user

        before = self.record_details(user['id'], apikey=user['apikey'])

        # Create a new group.
        request_data = {'name': 'a-new-group', 'title': 'A New Group'}
        response = self.app.post('/api/action/group_create',
            json.dumps(request_data),
            extra_environ={'Authorization': str(user['apikey'])})
        response_dict = json.loads(response.body)
        assert response_dict['success'] is True
        group_created = response_dict['result']

        after = self.record_details(user['id'],
                group_ids=[group_created['id']], apikey=user['apikey'])

        # Find the new activity.
        new_activities = find_new_activities(before['user activity stream'],
            after['user activity stream'])
        assert len(new_activities) == 1, ("There should be 1 new activity in "
            "the user's activity stream, but found %i" % len(new_activities))
        activity = new_activities[0]

        assert after['group activity streams'][group_created['id']] == \
                new_activities, ("The same activity should also appear in "
                "the group's activity stream.")

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == group_created['id'], \
            str(activity['object_id'])
        assert activity['user_id'] == user['id'], str(activity['user_id'])
        assert activity['activity_type'] == 'new group', \
            str(activity['activity_type'])
        if 'id' not in activity:
            assert False, "activity object should have an id value"
        # TODO: Test for the _correct_ revision_id value.
        if 'revision_id' not in activity:
            assert False, "activity object should have a revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert timestamp >= before['time'] and timestamp <= after['time'], \
            str(activity['timestamp'])

    def test_delete_group(self):
        """
        Test deleted group activity stream.

        Test that correct activity stream item and detail items are created
        when groups are deleted.

        """
        for group in group_list(self.app):
            self._delete_group(group, self.sysadmin_user)

    def test_add_tag(self):
        """
        Test add tag activities.

        If a package is updated by adding one new tag to it, a
        'changed package' activity with a single 'added tag' activity detail
        should be emitted.

        """
        # Get a package.
        user = self.normal_user
        pkg_name = u"warandpeace"
        pkg_dict = package_show(self.app, {'id': pkg_name})

        # Add one new tag to the package.
        group_ids = [group['name'] for group in pkg_dict['groups']]

        before = self.record_details(
            user['id'], pkg_dict['id'],
            apikey=user['apikey'], group_ids=group_ids
        )
        new_tag_name = 'test tag'
        assert new_tag_name not in [tag['name'] for tag in pkg_dict['tags']]

        pkg_dict['tags'].append({'name': new_tag_name})
        package_update(self.app, pkg_dict, user)
        after = self.record_details(
            user['id'], pkg_dict['id'],
            apikey=user['apikey'], group_ids=group_ids
        )

        # Find the new activity in the user's activity stream.
        user_new_activities = (find_new_activities(
            before['user activity stream'], after['user activity stream']))
        assert len(user_new_activities) == 1, ("There should be 1 new "
            " activity in the user's activity stream, but found %i" %
            len(user_new_activities))
        activity = user_new_activities[0]

        # The same new activity should appear in the package's stream.
        pkg_new_activities = (find_new_activities(
            before['package activity stream'],
            after['package activity stream']))
        assert pkg_new_activities == user_new_activities

        # The same new activity should appear in the recently changed datasets
        # stream.
        assert find_new_activities(
                before['recently changed datasets stream'],
                after['recently changed datasets stream']) \
                        == user_new_activities

        # If the package has any groups, the same new activity should appear
        # in the activity stream of each group.
        for group_dict in pkg_dict['groups']:
            grp_new_activities = find_new_activities(
                before['group activity streams'][group_dict['name']],
                after['group activity streams'][group_dict['name']])
            assert grp_new_activities == [activity]

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == pkg_dict['id'], (
            str(activity['object_id']))
        assert activity['user_id'] == user['id'], str(activity['user_id'])
        assert activity['activity_type'] == 'changed package', (
            str(activity['activity_type']))
        if 'id' not in activity:
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if 'revision_id' not in activity:
            assert False, "activity has no revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert (timestamp >= before['time'] and
                timestamp <= after['time']), str(activity['timestamp'])

        # Test for the presence of a correct activity detail item.
        details = self.activity_details(activity)
        assert len(details) == 1
        detail = details[0]
        assert detail['activity_id'] == activity['id'], \
            str(detail['activity_id'])
        assert detail['object_type'] == "tag", (
            str(detail['object_type']))
        assert detail['activity_type'] == "added", (
            str(detail['activity_type']))

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

    def test_add_extras(self):
        """
        Test new package extra activity stream.

        Test that correct activity stream item and detail items are emitted
        when an extra is added to a package.

        """
        for package_name in package_list(self.app):
            package_dict = package_show(self.app, {'id': package_name})
            self._add_extra(package_dict, user=self.normal_user)

    def test_delete_extras(self):
        """
        Test deleted package extra activity stream.

        Test that correct activity stream item and detail items are emitted
        when a package extra is deleted.

        """
        packages_with_extras = []
        for package_name in package_list(self.app):
            package_dict = package_show(self.app, {'id': package_name})
            if len(package_dict['extras']) > 0:
                    packages_with_extras.append(package_dict)
        assert len(packages_with_extras) > 0, (
                "Need some packages with extras to test")
        for package_dict in packages_with_extras:
            self._delete_extra(package_dict, user=self.normal_user)

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
