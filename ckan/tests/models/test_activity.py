import datetime
import logging
logger = logging.getLogger(__name__)

import ckan
import ckan.model as model
from ckan.logic.action.create import package_create, user_create, group_create
from ckan.logic.action.update import package_update, resource_update
from ckan.logic.action.update import user_update, group_update
from ckan.logic.action.delete import package_delete
from ckan.lib.dictization.model_dictize import resource_list_dictize
from ckan.logic.action.get import user_activity_list, activity_detail_list
from ckan.logic.action.get import package_activity_list, group_activity_list
from pylons.test import pylonsapp
import paste.fixture
from ckan.lib.helpers import json

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

def make_package():
    '''Return a test package in dictionary form.'''
    # A package with no resources, tags, extras or groups.
    pkg = {
        'name' : 'test_package',
        'title' : 'My Test Package',
        'author' : 'test author',
        'author_email' : 'test_author@test_author.com',
        'maintainer' : 'test maintainer',
        'maintainer_email' : 'test_maintainer@test_maintainer.com',
        'notes' : 'some test notes',
        'url' : 'www.example.com',
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
    tag1 = { 'name': 'a_test_tag' }
    tag2 = { 'name': 'another_test_tag' }
    pkg['tags'] = [tag1, tag2]
    return pkg

def get_user_activity_stream(user_id):
    context = {'model':model}
    data_dict = {'id':user_id}
    return user_activity_list(context, data_dict)

def get_package_activity_stream(package_id):
    context = {'model':model}
    data_dict = {'id':package_id}
    return package_activity_list(context, data_dict)

def get_group_activity_stream(group_id):
    context = {'model':model}
    data_dict = {'id':group_id}
    return group_activity_list(context, data_dict)

def get_user_activity_stream_from_api(user_id):
    app = paste.fixture.TestApp(pylonsapp)
    response = app.get("/api/2/rest/user/%s/activity" % user_id)
    return json.loads(response.body)

def get_package_activity_stream_from_api(package_id):
    app = paste.fixture.TestApp(pylonsapp)
    response = app.get("/api/2/rest/dataset/%s/activity" % package_id)
    return json.loads(response.body)

def get_group_activity_stream_from_api(group_id):
    app = paste.fixture.TestApp(pylonsapp)
    response = app.get("/api/2/rest/group/%s/activity" % group_id)
    return json.loads(response.body)

def get_activity_details(activity):
    '''Return the list of activity details for the given activity.'''
    context = {'model': model}
    data_dict = {'id': activity['id']}
    details = activity_detail_list(context, data_dict)
    assert details == get_activity_details_from_api(activity), ("Results from"
        " API should match results from logic function.")
    return details

def get_activity_details_from_api(activity):
    app = paste.fixture.TestApp(pylonsapp)
    response = app.get("/api/2/rest/activity/%s/details" % activity['id'])
    return json.loads(response.body)

def record_details(user_id, package_id=None, group_id=None):
    details = {}
    details['user activity stream'] = get_user_activity_stream(user_id)
    assert get_user_activity_stream_from_api(user_id) == (
        details['user activity stream'])

    if package_id is not None:
        details['package activity stream'] = (
                get_package_activity_stream(package_id))
        assert get_package_activity_stream_from_api(package_id) == (
            details['package activity stream']), ("Results from API should "
            "match results from controller function.")

    if group_id is not None:
        details['group activity stream'] = (
                get_group_activity_stream(group_id))
        assert get_group_activity_stream_from_api(group_id) == (
            details['group activity stream']), ("Results from API should "
            "match results from controller function.")

    details['time'] = datetime.datetime.now()
    return details

def find_new_activities(before, after):
    new_activities = []
    for activity in after:
        if activity not in before:
            new_activities.append(activity)
    return new_activities

class TestActivity:

    def setUp(self):
        ckan.tests.CreateTestData.create()
        self.sysadmin_user = model.User.get('testsysadmin')
        self.normal_user = model.User.get('annafan')

    def tearDown(self):
        model.repo.rebuild_db()

    def _create_package(self, user):
        if user:
            user_name = user.name
            user_id = user.id
        else:
            user_name = '127.0.0.1'
            user_id = 'not logged in'

        before = record_details(user_id)

        # Create a new package.
        context = {'model': model, 'session': model.Session, 'user': user_name}
        request_data = make_package()
        package_created = package_create(context, request_data)

        after = record_details(user_id, package_created['id'])

        # Find the new activity in the user's activity stream.
        user_new_activities = (find_new_activities(
            before['user activity stream'], after['user activity stream']))
        assert len(user_new_activities) == 1, ("There should be 1 new "
            " activity in the user's activity stream, but found %i" % 
            len(user_new_activities))
        activity = user_new_activities[0]

        # The same new activity should appear in the package's activity stream.
        pkg_new_activities = after['package activity stream']
        assert pkg_new_activities == user_new_activities

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == package_created['id'], \
            str(activity['object_id'])
        assert activity['user_id'] == user_id, str(activity['user_id'])
        assert activity['activity_type'] == 'new package', \
            str(activity['activity_type'])
        if not activity.has_key('id'):
            assert False, "activity object should have an id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity.has_key('revision_id'):
            assert False, "activity object should have a revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert timestamp >= before['time'] and timestamp <= \
            after['time'], str(activity['timestamp'])

        # Test that there are three activity details: one for the package
        # itself and one for each of its two resources, and test that each
        # contains the right data.
        details = get_activity_details(activity)
        assert len(details) == 3
        for detail in details:
            assert detail['activity_id'] == activity['id'], \
                str(detail['activity_id'])
            assert detail['activity_type'] == "new", ( 
                str(detail['activity_type']))
            if detail['object_id'] == package_created['id']:
                assert detail['object_type'] == "Package", \
                    str(detail['object_type'])
            elif (detail['object_id'] ==
                package_created['resources'][0]['id']):
                assert detail['object_type'] == "Resource", (
                    str(detail['object_type']))
            elif (detail['object_id'] ==
                package_created['resources'][1]['id']):
                assert detail['object_type'] == "Resource", \
                    str(detail['object_type'])
            else:
                assert False, ("Activity detail's object_id did not match"
                    "package or any of its resources: %s" \
                    % str(detail['object_id']))

    def test_create_package(self):
        """
        Test new package activity stream.

        Test that correct activity stream item and detail items are emitted
        when a new package is created.

        """
        self._create_package(user=self.normal_user)

    def test_create_package_not_logged_in(self):
        """
        Test new package activity stream when not logged in.

        Test that correct activity stream item and detail items are emitted
        when a new package is created by a user who is not logged in.

        """
        self._create_package(user=None)

    def _add_resource(self, package, user):
        if user:
            user_name = user.name
            user_id = user.id
        else:
            user_name = '127.0.0.1'
            user_id = 'not logged in'

        before = record_details(user_id, package.id)

        # Query for the package object again, as the session that it belongs to
        # may have been closed.
        package = model.Session.query(model.Package).get(package.id)

        resource_ids_before = [resource.id for resource in package.resources]

        # Create a new resource.
        context = {'model': model, 'session': model.Session, 'user': user_name}
        resources = resource_list_dictize(package.resources, context)
        resources.append(make_resource())
        request_data = {
                'id':package.id,
                'resources':resources
                }
        updated_package = package_update(context, request_data)

        after = record_details(user_id, package.id)
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

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == updated_package['id'], \
            str(activity['object_id'])
        assert activity['user_id'] == user_id, str(activity['user_id'])
        assert activity['activity_type'] == 'changed package', \
            str(activity['activity_type'])
        if not activity.has_key('id'):
            assert False, "activity object should have an id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity.has_key('revision_id'):
            assert False, "activity object should have a revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert (timestamp >= before['time'] and
                timestamp <= after['time']), str(activity['timestamp'])

        # Test for the presence of a correct activity detail item.
        details = get_activity_details(activity)        
        assert len(details) == 1
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

    def test_add_resources(self):
        """
        Test new resource activity stream.

        Test that correct activity stream item and detail items are emitted
        when a resource is added to a package.

        """
        for package in model.Session.query(model.Package).all():
            self._add_resource(package, user=self.normal_user)

    def test_add_resources_not_logged_in(self):
        """
        Test new resource activity stream when no user logged in.

        Test that correct activity stream item and detail items are emitted
        when a resource is added to a package by a user who is not logged in.

        """
        for package in model.Session.query(model.Package).all():
            self._add_resource(package, user=None)

    def _update_package(self, package, user):
        """
        Update the given package and test that the correct activity stream
        item and detail are emitted.

        """
        if user:
            user_name = user.name
            user_id = user.id
        else:
            user_name = '127.0.0.1'
            user_id = 'not logged in'

        before = record_details(user_id, package.id)

        # Query for the package object again, as the session that it belongs to
        # may have been closed.
        package = model.Session.query(model.Package).get(package.id)

        # Update the package.
        context = {'model': model, 'session': model.Session, 'user': user_name,
                'allow_partial_update': True}
        package_dict = {'id': package.id, 'title': 'edited'}
        package_update(context, package_dict)

        after = record_details(user_id, package.id)

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
        assert activity['object_id'] == package.id, (
            str(activity['object_id']))
        assert activity['user_id'] == user_id, str(activity['user_id'])
        assert activity['activity_type'] == 'changed package', (
            str(activity['activity_type']))
        if not activity.has_key('id'):
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity.has_key('revision_id'):
            assert False, "activity has no revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert (timestamp >= before['time'] and
                timestamp <= after['time']), str(activity['timestamp'])

        # Test for the presence of a correct activity detail item.
        details = get_activity_details(activity)
        assert len(details) == 1
        detail = details[0]
        assert detail['activity_id'] == activity['id'], \
            str(detail['activity_id'])
        assert detail['object_id'] == package.id, str(detail['object_id'])
        assert detail['object_type'] == "Package", ( 
            str(detail['object_type']))
        assert detail['activity_type'] == "changed", (
            str(detail['activity_type']))

    def test_update_package(self):
        """
        Test updated package activity stream.

        Test that correct activity stream item and detail items are created
        when packages are updated.

        """
        for package in model.Session.query(model.Package).all():
            self._update_package(package, user=self.normal_user)

    def test_update_package_not_logged_in(self):
        """
        Test updated package activity stream when not logged in.

        Test that correct activity stream item and detail items are created
        when packages are updated by a user who is not logged in.

        """
        for package in model.Session.query(model.Package).all():
            self._update_package(package, user=None)

    def _update_resource(self, package, resource, user):
        """
        Update the given resource and test that the correct activity stream
        item and detail are emitted.

        """
        if user:
            user_name = user.name
            user_id = user.id
        else:
            user_name = '127.0.0.1'
            user_id = 'not logged in'

        before = record_details(user_id, package.id)

        # Query for the Package and Resource objects again, as the session that
        # they belong to may have been closed.
        package = model.Session.query(model.Package).get(package.id)
        resource = model.Session.query(model.Resource).get(resource.id)

        # Update the resource.
        context = {'model': model, 'session': model.Session, 'user': user_name,
                'allow_partial_update': True}
        resource_dict = {'id':resource.id, 'name':'edited'}
        resource_update(context, resource_dict)

        after = record_details(user_id, package.id)

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
        assert activity['object_id'] == package.id, (
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
        details = get_activity_details(activity)
        assert len(details) == 1
        detail = details[0]
        assert detail['activity_id'] == activity['id'], (
            str(detail['activity_id']))
        assert detail['object_id'] == resource.id, str(detail['object_id'])
        assert detail['object_type'] == "Resource", (
            str(detail['object_type']))
        assert detail['activity_type'] == "changed", (
            str(detail['activity_type']))

    def test_update_resource(self):
        """
        Test that a correct activity stream item and detail item are emitted
        when a resource is updated.

        """
        packages = model.Session.query(model.Package).all()
        for package in packages:
            # Query the model for the Package object again, as the session that
            # it belongs to may have been closed.
            pkg = model.Session.query(model.Package).get(package.id)
            for resource in pkg.resources:
                self._update_resource(pkg, resource, user=self.normal_user)

    def test_update_resource_not_logged_in(self):
        """
        Test that a correct activity stream item and detail item are emitted
        when a resource is updated by a user who is not logged in.

        """
        packages = model.Session.query(model.Package).all()
        for package in packages:
            # Query the model for the Package object again, as the session that
            # it belongs to may have been closed.
            pkg = model.Session.query(model.Package).get(package.id)
            for resource in pkg.resources:
                self._update_resource(pkg, resource, user=None)

    def _delete_package(self, package):
        """
        Delete the given package and test that the correct activity stream
        item and detail are emitted.

        """
        before = record_details(self.normal_user.id, package.id)

        # Query for the package object again, as the session that it belongs to
        # may have been closed.
        package = model.Session.query(model.Package).get(package.id)

        # Delete the package.
        context = {'model': model, 'session': model.Session,
            'user': self.normal_user.name}
        package_dict = {'id':package.id}
        package_delete(context, package_dict)

        after = record_details(self.normal_user.id, package.id)

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
        assert activity['object_id'] == package.id, (
                str(activity['object_id']))
        assert activity['user_id'] == self.normal_user.id, (
            str(activity['user_id']))
        # "Deleted" packages actually show up as changed (the package's
        # status changes to "deleted" but the package is not expunged).
        assert activity['activity_type'] == 'changed package', (
            str(activity['activity_type']))
        if not activity.has_key('id'):
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity.has_key('revision_id'):
            assert False, "activity has no revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert (timestamp >= before['time'] and
                timestamp <= after['time']), str(activity['timestamp'])

        # Test for the presence of a correct activity detail item.
        details = get_activity_details(activity)
        assert len(details) == 1
        detail = details[0]        
        assert detail['activity_id'] == activity['id'], \
            str(detail['activity_id'])
        assert detail['object_id'] == package.id, str(detail['object_id'])
        assert detail['object_type'] == "Package", (
            str(detail['object_type']))
        # "Deleted" packages actually show up as changed (the package's
        # status changes to "deleted" but the package is not expunged).
        assert detail['activity_type'] == "changed", (
            str(detail['activity_type']))

    def test_delete_package(self):
        """
        Test deleted package activity stream.

        Test that correct activity stream item and detail items are created
        when packages are deleted.

        """
        for package in model.Session.query(model.Package).all():
            self._delete_package(package)

    def _delete_resources(self, package):
        """
        Remove all resources (if any) from the given package, and test that
        correct activity item and detail items are emitted.

        """
        before = record_details(self.normal_user.id, package.id)

        # Query the model for the Package object again, as the session that it
        # belongs to may have been closed.
        package = model.Session.query(model.Package).get(package.id)
        num_resources = len(package.resources)
        assert num_resources > 0, \
                "Cannot delete resources if there aren't any."
        resource_ids = [resource.id for resource in package.resources]

        # Delete the resources.
        context = {'model': model, 'session': model.Session,
                'user':self.normal_user.name}
        data_dict = { 'id':package.id, 'resources':[] }
        package_update(context, data_dict)

        after = record_details(self.normal_user.id, package.id)

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
        assert activity['object_id'] == package.id, (
            str(activity['object_id']))
        assert activity['user_id'] == self.normal_user.id, (
            str(activity['user_id']))
        assert activity['activity_type'] == 'changed package', (
            str(activity['activity_type']))
        if not activity.has_key('id'):
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity.has_key('revision_id'):
            assert False, "activity has no revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert (timestamp >= before['time'] and
            timestamp <= after['time'], str(activity['timestamp']))

        # Test for the presence of correct activity detail items.
        details = get_activity_details(activity)
        assert len(details) == num_resources        
        for detail in details:
            assert detail['activity_id'] == activity['id'], (
                "activity_id should be %s but is %s"
                % (activity['id'], detail['activity_id']))
            assert detail['object_id'] in resource_ids, (
                str(detail['object_id']))
            assert detail['object_type'] == "Resource", (
                str(detail['object_type']))
            assert detail['activity_type'] == "changed", (
                str(detail['activity_type']))

    def test_delete_resources(self):
        """
        Test deleted resource activity stream.

        Test that correct activity stream item and detail items are created
        when resources are deleted from packages.

        """
        packages_with_resources = []
        for package in model.Session.query(model.Package).all():
            # Query for the package object again, as the session that it
            # belongs to may have been closed.
            package = model.Session.query(model.Package).get(package.id)
            if len(package.resources) > 0:
                packages_with_resources.append(package)
        assert len(packages_with_resources) > 0, \
                "Need some packages with resources to test deleting resources."
        for package in packages_with_resources:
            self._delete_resources(package)

    def test_create_user(self):
        """
        Test new user activity stream.

        Test that correct activity stream item and detail item are created when
        a new user is created.

        """
        before = datetime.datetime.now()

        # Create a new user.
        user_dict = {'name': 'testuser',
                'about': 'Just a test user', 'email': 'me@test.org',
                'password': 'testpass'}
        context = {'model': model, 'session': model.Session,
                'user': self.sysadmin_user.name}
        user_created = user_create(context, user_dict)

        after = record_details(user_created['id'])

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
        if not activity.has_key('id'):
            assert False, "activity object should have an id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity.has_key('revision_id'):
            assert False, "activity object should have a revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert timestamp >= before and timestamp <= after['time'], \
            str(activity['timestamp'])

        details = get_activity_details(activity)
        assert len(details) == 0, ("There shouldn't be any activity details"
                " for a 'new user' activity")

    def _update_user(self, user):
        """
        Update the given user and test that the correct activity stream item
        and detail are emitted.

        """
        before = record_details(user.id)

        # Query for the user object again, as the session that it belongs to
        # may have been closed.
        user = model.Session.query(model.User).get(user.id)

        # Update the user.
        context = {'model': model, 'session': model.Session, 'user': user.name,
                'allow_partial_update': True}
        user_dict = {'id': user.id}
        user_dict['about'] = 'edited'
        if not user.email:
            user_dict['email'] = 'there has to be a value in email or validate fails'
        user_update(context, user_dict)

        after = record_details(user.id)

        # Find the new activity.
        new_activities = find_new_activities(before['user activity stream'],
            after['user activity stream'])
        assert len(new_activities) == 1, ("There should be 1 new activity in "
            "the user's activity stream, but found %i" % len(new_activities))
        activity = new_activities[0]

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == user.id, str(activity['object_id'])
        assert activity['user_id'] == user.id, str(activity['user_id'])
        assert activity['activity_type'] == 'changed user', \
            str(activity['activity_type'])
        if not activity.has_key('id'):
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity.has_key('revision_id'):
            assert False, "activity has no revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert timestamp >= before['time'] and timestamp <= after['time'], \
            str(activity['timestamp'])

    def test_update_user(self):
        """
        Test updated user activity stream.

        Test that correct activity stream item is created when users are
        updated.

        """
        for user in model.Session.query(model.User).all():
            self._update_user(user)

    def test_create_group(self):

        user = self.normal_user

        before = record_details(user.id)

        # Create a new group.
        context = {'model': model, 'session': model.Session, 'user': user.name}
        request_data = {'name': 'a-new-group', 'title': 'A New Group'}
        group_created = group_create(context, request_data)

        after = record_details(user.id, group_id=group_created['id'])

        # Find the new activity.
        new_activities = find_new_activities(before['user activity stream'],
            after['user activity stream'])
        assert len(new_activities) == 1, ("There should be 1 new activity in "
            "the user's activity stream, but found %i" % len(new_activities))
        activity = new_activities[0]

        assert after['group activity stream'] == new_activities, ("The same "
            "activity should also appear in the group's activity stream.")

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == group_created['id'], \
            str(activity['object_id'])
        assert activity['user_id'] == user.id, str(activity['user_id'])
        assert activity['activity_type'] == 'new group', \
            str(activity['activity_type'])
        if not activity.has_key('id'):
            assert False, "activity object should have an id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity.has_key('revision_id'):
            assert False, "activity object should have a revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert timestamp >= before['time'] and timestamp <= after['time'], \
            str(activity['timestamp'])

    def _update_group(self, group, user):
        """
        Update the given group and test that the correct activity stream
        item and detail are emitted.

        """
        before = record_details(user.id, group_id=group.id)

        # Update the group.
        context = {'model': model, 'session': model.Session, 'user': user.name,
                'allow_partial_update': True}
        group_dict = {'id': group.id, 'title': 'edited'}
        group_updated = group_update(context, group_dict)

        after = record_details(user.id, group_id=group.id)

        # Find the new activity.
        new_activities = find_new_activities(before['user activity stream'],
            after['user activity stream'])
        assert len(new_activities) == 1, ("There should be 1 new activity in "
            "the user's activity stream, but found %i" % len(new_activities))
        activity = new_activities[0]

        assert find_new_activities(before["group activity stream"],
            after['group activity stream']) == new_activities, ("The same "
            "activity should also appear in the group's activity stream.")

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == group.id, str(activity['object_id'])
        assert activity['user_id'] == user.id, str(activity['user_id'])
        assert activity['activity_type'] == 'changed group', \
            str(activity['activity_type'])
        if not activity.has_key('id'):
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity.has_key('revision_id'):
            assert False, "activity has no revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert timestamp >= before['time'] and timestamp <= after['time'], \
            str(activity['timestamp'])

    def test_update_group(self):
        """
        Test updated group activity stream.

        Test that correct activity stream item and detail items are created
        when groups are updated.

        """
        for group in model.Session.query(model.Group).all():
            self._update_group(group, user=self.sysadmin_user)
