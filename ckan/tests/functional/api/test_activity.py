import datetime
import logging
logger = logging.getLogger(__name__)

import ckan
import ckan.model as model
from ckan.logic.action.create import package_create, user_create, group_create
from ckan.logic.action.update import package_update, resource_update
from ckan.logic.action.update import user_update, group_update
from ckan.logic.action.delete import package_delete
from ckan.logic.action.get import package_list, package_show
from ckan.lib.dictization.model_dictize import resource_list_dictize
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

def find_new_activities(before, after):
    new_activities = []
    for activity in after:
        if activity not in before:
            new_activities.append(activity)
    return new_activities

class TestActivity:

    def setup(self):
        ckan.tests.CreateTestData.create()
        self.sysadmin_user = model.User.get('testsysadmin')
        self.normal_user = model.User.get('annafan')
        self.warandpeace = model.Package.get('warandpeace')
        self.annakarenina = model.Package.get('annakarenina')
        self.app = paste.fixture.TestApp(pylonsapp)

    def teardown(self):
        model.repo.rebuild_db()

    def user_activity_stream(self, user_id):
        response = self.app.get("/api/2/rest/user/%s/activity" % user_id)
        return json.loads(response.body)

    def package_activity_stream(self, package_id):
        response = self.app.get("/api/2/rest/dataset/%s/activity" % package_id)
        return json.loads(response.body)

    def group_activity_stream(self, group_id):
        response = self.app.get("/api/2/rest/group/%s/activity" % group_id)
        return json.loads(response.body)

    def activity_details(self, activity):
        response = self.app.get(
                "/api/2/rest/activity/%s/details" % activity['id'])
        return json.loads(response.body)

    def record_details(self, user_id, package_id=None, group_id=None):
        details = {}
        details['user activity stream'] = self.user_activity_stream(user_id)

        if package_id is not None:
            details['package activity stream'] = (
                    self.package_activity_stream(package_id))

        if group_id is not None:
            details['group activity stream'] = (
                self.group_activity_stream(group_id))

        details['time'] = datetime.datetime.now()
        return details

    def _create_package(self, user):
        if user:
            user_name = user.name
            user_id = user.id
        else:
            user_name = '127.0.0.1'
            user_id = 'not logged in'

        before = self.record_details(user_id)

        # Create a new package.
        context = {
            'model': model,
            'session': model.Session,
            'user': user_name,
            'allow_partial_update': True,
            }
        request_data = make_package()
        package_created = package_create(context, request_data)

        after = self.record_details(user_id, package_created['id'])

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

        before = self.record_details(user_id, package.id)

        # Query for the package object again, as the session that it belongs to
        # may have been closed.
        package = model.Session.query(model.Package).get(package.id)

        resource_ids_before = [resource.id for resource in package.resources]

        # Create a new resource.
        context = {
            'model': model,
            'session': model.Session,
            'user': user_name,
            'allow_partial_update': True,
            }
        resources = resource_list_dictize(package.resources, context)
        resources.append(make_resource())
        request_data = {
                'id': package.id,
                'resources': resources,
                }
        updated_package = package_update(context, request_data)

        after = self.record_details(user_id, package.id)
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
        details = self.activity_details(activity)
        assert len(details) == 1, [(detail['activity_type'], detail['object_type']) for detail in details]
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

        before = self.record_details(user_id, package.id)

        # Query for the package object again, as the session that it belongs to
        # may have been closed.
        package = model.Session.query(model.Package).get(package.id)

        # Update the package.
        context = {'model': model, 'session': model.Session, 'user': user_name,
                'allow_partial_update': True}
        package_dict = {'id': package.id, 'title': 'edited'}
        package_update(context, package_dict)

        after = self.record_details(user_id, package.id)

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
        details = self.activity_details(activity)
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

        before = self.record_details(user_id, package.id)

        # Query for the Package and Resource objects again, as the session that
        # they belong to may have been closed.
        package = model.Session.query(model.Package).get(package.id)
        resource = model.Session.query(model.Resource).get(resource.id)

        # Update the resource.
        context = {'model': model, 'session': model.Session, 'user': user_name,
                'allow_partial_update': True}
        resource_dict = {'id':resource.id, 'name':'edited'}
        resource_update(context, resource_dict)

        after = self.record_details(user_id, package.id)

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
        before = self.record_details(self.normal_user.id, package.id)

        # Query for the package object again, as the session that it belongs to
        # may have been closed.
        package = model.Session.query(model.Package).get(package.id)

        # Delete the package.
        context = {'model': model, 'session': model.Session,
            'user': self.normal_user.name}
        package_dict = {'id':package.id}
        package_delete(context, package_dict)

        after = self.record_details(self.normal_user.id, package.id)

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

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == package.id, (
                str(activity['object_id']))
        assert activity['user_id'] == self.normal_user.id, (
            str(activity['user_id']))
        assert activity['activity_type'] == 'deleted package', (
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
        details = self.activity_details(activity)
        assert len(details) == 1
        detail = details[0]        
        assert detail['activity_id'] == activity['id'], \
            str(detail['activity_id'])
        assert detail['object_id'] == package.id, str(detail['object_id'])
        assert detail['object_type'] == "Package", (
            str(detail['object_type']))
        assert detail['activity_type'] == "deleted", (
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
        before = self.record_details(self.normal_user.id, package.id)

        # Query the model for the Package object again, as the session that it
        # belongs to may have been closed.
        package = model.Session.query(model.Package).get(package.id)
        num_resources = len(package.resources)
        assert num_resources > 0, \
                "Cannot delete resources if there aren't any."
        resource_ids = [resource.id for resource in package.resources]

        # Delete the resources.
        context = {
            'model': model,
            'session': model.Session,
            'user':self.normal_user.name,
            }
        from ckan.lib.dictization.model_dictize import package_dictize
        data_dict = package_dictize(package, context)
        data_dict['resources'] = []
        package_update(context, data_dict)

        after = self.record_details(self.normal_user.id, package.id)

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

        after = self.record_details(user_created['id'])

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

        details = self.activity_details(activity)
        assert len(details) == 0, ("There shouldn't be any activity details"
                " for a 'new user' activity")

    def _update_user(self, user):
        """
        Update the given user and test that the correct activity stream item
        and detail are emitted.

        """
        before = self.record_details(user.id)

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

        after = self.record_details(user.id)

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

        before = self.record_details(user.id)

        # Create a new group.
        context = {'model': model, 'session': model.Session, 'user': user.name}
        request_data = {'name': 'a-new-group', 'title': 'A New Group'}
        group_created = group_create(context, request_data)

        after = self.record_details(user.id, group_id=group_created['id'])

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
        before = self.record_details(user.id, group_id=group.id)

        # Update the group.
        context = {'model': model, 'session': model.Session, 'user': user.name,
                'allow_partial_update': True}
        group_dict = {'id': group.id, 'title': 'edited'}
        group_updated = group_update(context, group_dict)

        after = self.record_details(user.id, group_id=group.id)

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

    def _delete_group(self, group, user):
        """
        Delete the given group and test that the correct activity stream
        item and detail are emitted.

        """
        before = self.record_details(user.id, group_id=group.id)

        # Deleted the group.
        context = {'model': model, 'session': model.Session,
                'user': user.name, 'allow_partial_update': True}
        group_dict = {'id': group.id, 'state': 'deleted'}
        group_update(context, group_dict)

        after = self.record_details(user.id, group_id=group.id)

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
        assert activity['activity_type'] == 'deleted group', \
            str(activity['activity_type'])
        if not activity.has_key('id'):
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity.has_key('revision_id'):
            assert False, "activity has no revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert timestamp >= before['time'] and timestamp <= after['time'], \
            str(activity['timestamp'])

    def test_delete_group(self):
        """
        Test deleted group activity stream.

        Test that correct activity stream item and detail items are created
        when groups are deleted.

        """
        for group in model.Session.query(model.Group).all():
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
        context = {
            'model': model,
            'session': model.Session,
            'user': user.name,
        }
        pkg_dict = ckan.logic.action.get.package_show(context,
                {'id': pkg_name})

        # Add one new tag to the package.
        before = self.record_details(user.id, pkg_dict['id'])
        new_tag_name = 'test tag'
        assert new_tag_name not in [tag['name'] for tag in pkg_dict['tags']]
        new_tag_list = pkg_dict['tags'] + [{'name': new_tag_name}]
        data_dict = {
            'id': pkg_dict['id'],
            'tags': new_tag_list
            }
        ckan.logic.action.update.package_update(context, data_dict)
        after = self.record_details(user.id, pkg_dict['id'])

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

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == pkg_dict['id'], (
            str(activity['object_id']))
        assert activity['user_id'] == user.id, str(activity['user_id'])
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
        details = self.activity_details(activity)
        assert len(details) == 1
        detail = details[0]
        assert detail['activity_id'] == activity['id'], \
            str(detail['activity_id'])
        assert detail['object_type'] == "tag", (
            str(detail['object_type']))
        assert detail['activity_type'] == "added", (
            str(detail['activity_type']))

    def test_remove_tag(self):
        """
        Test remove tag activity.

        If a package is updated by removing one tag from it, a
        'changed package' activity with a single 'removed tag' activity detail
        should be emitted.

        """
        # Get a package.
        user = self.normal_user
        pkg_name = u"warandpeace"
        context = {
            'model': model,
            'session': model.Session,
            'user': user.name,
        }
        pkg_dict = ckan.logic.action.get.package_show(context,
                {'id': pkg_name})

        # Remove one tag from the package.
        assert len(pkg_dict['tags']) >= 1, ("The package has to have at least"
                " one tag to test removing a tag.")
        before = self.record_details(user.id, pkg_dict['id'])
        data_dict = {
            'id': pkg_dict['id'],
            'tags': pkg_dict['tags'][0:-1],
            }
        ckan.logic.action.update.package_update(context, data_dict)
        after = self.record_details(user.id, pkg_dict['id'])

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

        # Check that the new activity has the right attributes.
        assert activity['object_id'] == pkg_dict['id'], (
            str(activity['object_id']))
        assert activity['user_id'] == user.id, str(activity['user_id'])
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
        details = self.activity_details(activity)
        assert len(details) == 1
        detail = details[0]
        assert detail['activity_id'] == activity['id'], \
            str(detail['activity_id'])
        assert detail['object_type'] == "tag", (
            str(detail['object_type']))
        assert detail['activity_type'] == "removed", (
            str(detail['activity_type']))

    def _create_activity(self, user, package, params):
        before = self.record_details(user.id, package.id)

        response = self.app.post('/api/action/activity_create', 
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)})
        assert response.json['success'] == True

        after = self.record_details(user.id, package.id)

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
        if not activity.has_key('id'):
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity.has_key('revision_id'):
            assert False, "activity has no revision_id value"
        timestamp = datetime_from_string(activity['timestamp'])
        assert (timestamp >= before['time'] and
                timestamp <= after['time']), str(activity['timestamp'])

    def test_activity_create_successful_no_data(self):
        """Test creating an activity via the API, without passing the optional
        data dict.

        """
        params = {
            'user_id': self.sysadmin_user.id,
            'object_id': self.warandpeace.id,
            'activity_type': 'changed package',
        }
        self._create_activity(self.sysadmin_user, self.warandpeace, params)

    def test_activity_create_successful_with_data(self):
        """Test creating an activity via the API, with the optional data dict.

        """
        params = {
            'user_id': self.sysadmin_user.id,
            'object_id': self.annakarenina.id,
            'activity_type': 'deleted package',
            'data': {'a': 1, 'b': 2, 'c': 3}
        }
        self._create_activity(self.sysadmin_user, self.annakarenina, params)

    def test_activity_create_no_authorization(self):
        """Test the error response when the activity_create API is called
        without an authorization header.

        """
        params = {
            'user_id': self.sysadmin_user.id,
            'object_id': self.warandpeace.id,
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create', 
            params=json.dumps(params), status=403)
        assert response.json['success'] == False

    def test_activity_create_not_authorized(self):
        """Test the error response when the activity_create API is called
        with an authorization header for a user who is not authorized to
        create activities.

        """
        params = {
            'user_id': self.normal_user.id,
            'object_id': self.warandpeace.id,
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create', 
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.normal_user.apikey)},
            status=403)
        assert response.json['success'] == False

    def test_activity_create_authorization_not_exists(self):
        """Test the error response when the activity_create API is called
        with an authorization header with an API key that doesn't exist in the
        model.

        """
        params = {
            'user_id': self.normal_user.id,
            'object_id': self.warandpeace.id,
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create', 
            params=json.dumps(params),
            extra_environ={'Authorization': 'xxxxxxxxxx'},
            status=403)
        assert response.json['success'] == False

    def test_activity_create_with_id(self):
        """Test that an ID passed to the activity_create API is ignored and not
        used.

        """
        activity_id = '1234567890'
        user = self.sysadmin_user
        package = self.warandpeace
        params = {
            'id': activity_id,
            'user_id': user.id,
            'object_id': package.id,
            'activity_type': 'changed package',
        }
        self._create_activity(self.sysadmin_user, self.warandpeace, params)
        assert activity_id not in [activity['id'] for activity in 
                self.user_activity_stream(user.id)]
        assert activity_id not in [activity['id'] for activity in 
                self.package_activity_stream(package.id)]

    def test_activity_create_with_timestamp(self):
        """Test that a timestamp passed to the activity_create API is ignored
        and not used

        """
        params = {
            'user_id': self.sysadmin_user.id,
            'object_id': self.warandpeace.id,
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
            'user_id': user.id,
            'object_id': package.id,
            'activity_type': 'changed package',
        }
        self._create_activity(self.sysadmin_user, self.warandpeace, params)
        assert revision_id not in [activity['revision_id'] for activity in 
                self.user_activity_stream(user.id)]
        assert revision_id not in [activity['revision_id'] for activity in 
                self.package_activity_stream(package.id)]

    def test_activity_create_user_id_missing(self):
        """Test the error response when the activity_create API is called with
        no user ID.

        """
        params = {
            'object_id': self.warandpeace.id,
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create', 
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
            status=409)
        assert response.json['success'] == False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'user_id'] == [u'Missing value'], (
                response.json['error'][u'user_id'])

    def test_activity_create_user_id_empty(self):
        """Test the error response when the activity_create API is called with
        an empty user ID.

        """
        params = {
            'user_id': '',
            'object_id': self.warandpeace.id,
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create', 
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
            status=409)
        assert response.json['success'] == False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'user_id'] == [u'Missing value'], (
                response.json['error'][u'user_id'])

        params['user_id'] = None
        response = self.app.post('/api/action/activity_create', 
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
            status=409)
        assert response.json['success'] == False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'user_id'] == [u'Missing value'], (
                response.json['error'][u'user_id'])

    def test_activity_create_user_id_does_not_exist(self):
        """Test the error response when the activity_create API is called with
        a user ID that doesn't exist in the model.

        """
        params = {
            'user_id': '1234567890abcdefghijk',
            'object_id': self.warandpeace.id,
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create', 
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
            status=409)
        assert response.json['success'] == False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'user_id'] == [
                u'Not found: User'], (
                response.json['error'][u'user_id'])

    def test_activity_create_object_id_missing(self):
        """Test the error response when the activity_create API is called with
        no object ID.

        """
        params = {
            'user_id': self.sysadmin_user.id,
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
            status=409)
        assert response.json['success'] == False
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
            'user_id': self.sysadmin_user.id,
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
            status=409)
        assert response.json['success'] == False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'object_id'] == [
                u'Missing value'], (
                response.json['error'][u'user_id'])

        params['object_id'] = None
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
            status=409)
        assert response.json['success'] == False
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
            'user_id': self.sysadmin_user.id,
            'activity_type': 'changed package',
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
            status=409)
        assert response.json['success'] == False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'object_id'] == [
                u'Not found: Dataset'], (
                response.json['error'][u'object_id'])

    def test_activity_create_activity_type_missing(self):
        """Test the error response when the activity_create API is called
        without an activity_type.

        """
        params = {
            'user_id': self.normal_user.id,
            'object_id': self.warandpeace.id,
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
            status=409)
        assert response.json['success'] == False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'object_id'] == [
                u'Missing value'], (
                response.json['error'][u'object_id'])

    def test_activity_create_activity_type_empty(self):
        """Test the error response when the activity_create API is called
        with an empty activity_type.

        """
        params = {
            'user_id': self.normal_user.id,
            'object_id': self.warandpeace.id,
            'activity_type': ''
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
            status=409)
        assert response.json['success'] == False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'activity_type'] == [
                u'Missing value'], (
                response.json['error'][u'activity_type'])

        params['activity_type'] = None
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
            status=409)
        assert response.json['success'] == False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'activity_type'] == [
                u'Missing value'], (
                response.json['error'][u'activity_type'])

    def test_activity_create_activity_type_not_exists(self):
        """Test the error response when the activity_create API is called
        with an activity_type that does not exist.

        """
        params = {
            'user_id': self.normal_user.id,
            'object_id': self.warandpeace.id,
            'activity_type': 'foobar'
        }
        response = self.app.post('/api/action/activity_create',
            params=json.dumps(params),
            extra_environ={'Authorization': str(self.sysadmin_user.apikey)},
            status=409)
        assert response.json['success'] == False
        assert response.json['error'][u'__type'] == u'Validation Error'
        assert response.json['error'][u'activity_type'] == [
            u"Not found: Activity type"], (
                response.json['error'][u'activity_type'])

    def _add_extra(self, package_dict, user):
        if user:
            user_name = user.name
            user_id = user.id
        else:
            user_name = '127.0.0.1'
            user_id = 'not logged in'

        before = self.record_details(user_id, package_dict['id'])

        extras_before = package_dict['extras']

        # Create a new extra.
        context = {
            'model': model,
            'session': model.Session,
            'user': user_name,
            'allow_partial_update': True,
            'extras_as_string': True
            }
        extras = list(extras_before)
        extras.append({'key': 'quality', 'value': '10000'})
        request_data = {
                'id': package_dict['id'],
                'extras': extras
                }
        updated_package = package_update(context, request_data)

        after = self.record_details(user_id, package_dict['id'])
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
        assert detail['object_id'] == new_extra['id'], (
            str(detail['object_id']))
        assert detail['object_type'] == "PackageExtra", (
            str(detail['object_type']))
        assert detail['activity_type'] == "new", (
            str(detail['activity_type']))

    def test_add_extras(self):
        """
        Test new package extra activity stream.

        Test that correct activity stream item and detail items are emitted
        when an extra is added to a package.

        """
        context = {
            'model': model,
            'session': model.Session,
            'user': self.normal_user.name,
            'extras_as_string': True,
            }
        for package_name in package_list(context, {}):
            package_dict = package_show(context, {'id': package_name})
            self._add_extra(package_dict, user=self.normal_user)

    def test_add_extras_not_logged_in(self):
        """
        Test new package extra activity stream when no user logged in.

        Test that correct activity stream item and detail items are emitted
        when an extra is added to a package by a user who is not logged in.

        """
        context = {
            'model': model,
            'session': model.Session,
            'user': self.normal_user.name,
            'extras_as_string': True,
            }
        for package_name in package_list(context, {}):
            package_dict = package_show(context, {'id': package_name})
            self._add_extra(package_dict, None)

    def _update_extra(self, package_dict, user):
        if user:
            user_name = user.name
            user_id = user.id
        else:
            user_name = '127.0.0.1'
            user_id = 'not logged in'

        before = self.record_details(user_id, package_dict['id'])

        extras_before = package_dict['extras']
        assert len(extras_before) > 0, (
                "Can't update an extra if the package doesn't have any")

        # Update the package's first extra.
        context = {
            'model': model,
            'session': model.Session,
            'user': user_name,
            'allow_partial_update': True,
            'extras_as_string': True
            }
        extras = list(extras_before)
        extras[0]['value'] = 'edited'
        request_data = {
                'id': package_dict['id'],
                'extras': extras
                }
        updated_package = package_update(context, request_data)

        after = self.record_details(user_id, package_dict['id'])
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
        assert detail['object_id'] == new_extra['id'], (
            str(detail['object_id']))
        assert detail['object_type'] == "PackageExtra", (
            str(detail['object_type']))
        assert detail['activity_type'] == "changed", (
            str(detail['activity_type']))

    def test_update_extras(self):
        """
        Test changed package extra activity stream.

        Test that correct activity stream item and detail items are emitted
        when a package extra is changed.

        """
        context = {
            'model': model,
            'session': model.Session,
            'user': self.normal_user.name,
            'extras_as_string': True,
            }
        packages_with_extras = []
        for package_name in package_list(context, {}):
            package_dict = package_show(context, {'id': package_name})
            if len(package_dict['extras']) > 0:
                    packages_with_extras.append(package_dict)
        assert len(packages_with_extras) > 0, (
                "Need some packages with extras to test")
        for package_dict in packages_with_extras:
            self._update_extra(package_dict, user=self.normal_user)

    def test_update_extras_not_logged_in(self):
        """
        Test changed package extra activity stream when no user logged in.

        Test that correct activity stream item and detail items are emitted
        when a package extra is changed by a user who is not logged in.

        """
        context = {
            'model': model,
            'session': model.Session,
            'user': self.normal_user.name,
            'extras_as_string': True,
            }
        packages_with_extras = []
        for package_name in package_list(context, {}):
            package_dict = package_show(context, {'id': package_name})
            if len(package_dict['extras']) > 0:
                    packages_with_extras.append(package_dict)
        assert len(packages_with_extras) > 0, (
                "Need some packages with extras to test")
        for package_dict in packages_with_extras:
            self._update_extra(package_dict, None)

    def _delete_extra(self, package_dict, user):
        if user:
            user_name = user.name
            user_id = user.id
        else:
            user_name = '127.0.0.1'
            user_id = 'not logged in'

        before = self.record_details(user_id, package_dict['id'])

        extras_before = package_dict['extras']
        assert len(extras_before) > 0, (
                "Can't update an extra if the package doesn't have any")

        # Update the package's first extra.
        context = {
            'model': model,
            'session': model.Session,
            'user': user_name,
            'allow_partial_update': True,
            'extras_as_string': True
            }
        extras = list(extras_before)
        del extras[0]
        request_data = {
                'id': package_dict['id'],
                'extras': extras
                }
        updated_package = package_update(context, request_data)

        after = self.record_details(user_id, package_dict['id'])
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
        assert detail['object_id'] == deleted_extra['id'], (
            str(detail['object_id']))
        assert detail['object_type'] == "PackageExtra", (
            str(detail['object_type']))
        assert detail['activity_type'] == "deleted", (
            str(detail['activity_type']))

    def test_delete_extras(self):
        """
        Test deleted package extra activity stream.

        Test that correct activity stream item and detail items are emitted
        when a package extra is deleted.

        """
        context = {
            'model': model,
            'session': model.Session,
            'user': self.normal_user.name,
            'extras_as_string': True,
            }
        packages_with_extras = []
        for package_name in package_list(context, {}):
            package_dict = package_show(context, {'id': package_name})
            if len(package_dict['extras']) > 0:
                    packages_with_extras.append(package_dict)
        assert len(packages_with_extras) > 0, (
                "Need some packages with extras to test")
        for package_dict in packages_with_extras:
            self._delete_extra(package_dict, user=self.normal_user)

    def test_delete_extras_not_logged_in(self):
        """
        Test deleted package extra activity stream when no user logged in.

        Test that correct activity stream item and detail items are emitted
        when a package extra is deleted by a user who is not logged in.

        """
        context = {
            'model': model,
            'session': model.Session,
            'user': self.normal_user.name,
            'extras_as_string': True,
            }
        packages_with_extras = []
        for package_name in package_list(context, {}):
            package_dict = package_show(context, {'id': package_name})
            if len(package_dict['extras']) > 0:
                    packages_with_extras.append(package_dict)
        assert len(packages_with_extras) > 0, (
                "Need some packages with extras to test")
        for package_dict in packages_with_extras:
            self._delete_extra(package_dict, None)
