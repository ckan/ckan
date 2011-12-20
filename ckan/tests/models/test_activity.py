import datetime
import random
import logging
logger = logging.getLogger(__name__)

import ckan
import ckan.model as model
from ckan.logic.action.create import package_create
from ckan.logic.action.update import package_update, resource_update
from ckan.logic.action.delete import package_delete
from ckan.lib.dictization.model_dictize import resource_list_dictize
from ckan.logic.action.get import activity_show

def _make_resource():
    return {
            'url': 'http://www.example.com',
            'description': 'example resource description',
            'format': 'txt',
            'name': 'example resource',
            }

class TestActivity:

    def setUp(self):
        ckan.tests.CreateTestData.create()
        self.sysadmin_user = model.User.get('testsysadmin')
        self.normal_user = model.User.get('annafan')

    def tearDown(self):
        ckan.tests.CreateTestData.delete()
        model.repo.rebuild_db()

    def _make_test_package(self):
        """Return a test package in dictionary form."""
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

    def _create_package(self, user):
        # Record some details before creating a new package.
        length_before = len(model.Session.query(model.activity.Activity).all())
        details_length_before = len(model.Session.query(
            model.activity.ActivityDetail).all())
        before = datetime.datetime.now()

        # Create a new package.
        if user is None:
            context = {'model': model, 'session': model.Session,
                    'user':'127.0.0.1'}
        else:
            context = {'model': model, 'session': model.Session,
                    'user':user.name}
        request_data = self._make_test_package()
        package_created = package_create(context, request_data)

        # Record some details after creating the new package.
        after = datetime.datetime.now()

        # Test that there is one new activity item and it contains the right
        # data.
        activities = model.Session.query(model.activity.Activity).all()
        assert len(activities) == length_before + 1, \
            "Length of activities table should be %i but is %i" \
            % (length_before + 1, len(activities))
        activity = activities[-1]
        assert activity.object_id == package_created['id'], \
            str(activity.object_id)
        if user:
            user_id = user.id
        else:
            user_id = 'not logged in'
        assert activity.user_id == user_id, str(activity.user_id)
        assert activity.activity_type == 'new package', \
            str(activity.activity_type)
        if not activity.id:
            assert False, "activity object should have an id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity.revision_id:
            assert False, "activity object should have a revision_id value"
        assert activity.timestamp >= before and activity.timestamp <= after, \
            str(activity.timestamp)

        # Test that there are three activity details: one for the package
        # itself and one for each of its two resources, and test that each
        # contains the right data.
        details = model.Session.query(model.activity.ActivityDetail).all()
        assert len(details) == details_length_before + 3, \
            "Length of details table should be %i but is %i" \
            % (details_length_before + 3, len(details))
        new_details = details[-3:]
        for detail in new_details:
            assert detail.activity_id == activity.id, str(detail.activity_id)
            assert detail.activity_type == "new", str(detail.activity_type)
            if detail.object_id == package_created['id']:
                assert detail.object_type == "Package", str(detail.object_type)
            elif detail.object_id == package_created['resources'][0]['id']:
                assert detail.object_type == "Resource", \
                    str(detail.object_type)
            elif detail.object_id == package_created['resources'][1]['id']:
                assert detail.object_type == "Resource", \
                    str(detail.object_type)
            else:
                assert False, ("Activity detail's object_id did not match"
                    "package or any of its resources: %s" \
                    % str(detail.object_id))

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
        # Record some details before creating a new resource.
        length_before = len(model.Session.query(model.activity.Activity).all())
        details_length_before = len(model.Session.query(
            model.activity.ActivityDetail).all())
        before = datetime.datetime.now()

        # Query for the package object again, as the session that it belongs to
        # may have been closed.
        package = model.Session.query(model.Package).get(package.id)

        resource_ids_before = [resource.id for resource in package.resources]

        # Create a new resource.
        if user is None:
            context = {'model': model, 'session': model.Session,
                    'user':'127.0.0.1'}
        else:
            context = {'model': model, 'session': model.Session,
                    'user':user.name}
        resources = resource_list_dictize(package.resources, context)
        resources.append(_make_resource())
        request_data = {
                'id':package.id,
                'resources':resources
                }
        updated_package = package_update(context, request_data)

        # Record some details after creating the new resource.
        after = datetime.datetime.now()
        resource_ids_after = [resource['id'] for resource in
                updated_package['resources']]

        assert len(resource_ids_after) == len(resource_ids_before) + 1

        # Test for the presence of a correct activity stream item.
        activities = model.Session.query(model.activity.Activity).all()
        assert len(activities) == length_before + 1, ("Length of activities "
            "table should be %i but is %i" % (length_before + 1,
                len(activities)))
        activity = activities[-1]
        assert activity.object_id == updated_package['id'], \
            str(activity.object_id)
        if user:
            user_id = user.id
        else:
            user_id = 'not logged in'
        assert activity.user_id == user_id, str(activity.user_id)
        assert activity.activity_type == 'changed package', \
            str(activity.activity_type)
        if not activity.id:
            assert False, "activity object should have an id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity.revision_id:
            assert False, "activity object should have a revision_id value"
        assert activity.timestamp >= before and activity.timestamp <= after, \
            str(activity.timestamp)

        # Test for the presence of a correct activity detail item.
        details = model.Session.query(model.activity.ActivityDetail).all()
        assert len(details) == details_length_before + 1, ("Length of details "
            "table should be %i but is %i" % (details_length_before + 1,
                len(details)))
        detail = details[-1]
        assert detail.activity_id == activity.id, str(detail.activity_id)
        new_resource_ids = [id for id in resource_ids_after if id not in
                resource_ids_before]
        assert len(new_resource_ids) == 1
        new_resource_id = new_resource_ids[0]
        assert detail.object_id == new_resource_id, str(detail.object_id)
        assert detail.object_type == "Resource", str(detail.object_type)
        assert detail.activity_type == "new", str(detail.activity_type)

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
        # Record some details before updating the package.
        length_before = len(model.Session.query(model.activity.Activity).all())
        details_length_before = len(model.Session.query(
            model.activity.ActivityDetail).all())
        before = datetime.datetime.now()

        # Query for the package object again, as the session that it belongs to
        # may have been closed.
        package = model.Session.query(model.Package).get(package.id)

        # Update the package.
        context = {'model': model, 'session': model.Session,
                'user':self.normal_user.name,
                'allow_partial_update':True}
        package_dict = {'id':package.id, 'title':'edited'}
        result = package_update(context, package_dict)

        # Record some details after updating the package.
        after = datetime.datetime.now()

        # Test for the presence of a correct activity stream item.
        activities = model.Session.query(model.activity.Activity).all()
        assert len(activities) == length_before + 1, ("Length of activities "
            "table should be %i but is %i" % (length_before + 1,
                len(activities)))
        activity = activities[-1]
        assert activity.object_id == package.id, str(activity.object_id)
        assert activity.user_id == self.normal_user.id, \
            str(activity.user_id)
        assert activity.activity_type == 'changed package', \
            str(activity.activity_type)
        if not activity.id:
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity.revision_id:
            assert False, "activity has no revision_id value"
        assert activity.timestamp >= before and activity.timestamp <= after, \
            str(activity.timestamp)

        # Test for the presence of a correct activity detail item.
        details = model.Session.query(model.activity.ActivityDetail).all()
        assert len(details) == details_length_before + 1, ("Length of details "
            "table should be %i but is %i" % (details_length_before + 1,
                len(details)))
        detail = details[-1]
        assert detail.activity_id == activity.id, str(detail.activity_id)
        assert detail.object_id == package.id, str(detail.object_id)
        assert detail.object_type == "Package", str(detail.object_type)
        assert detail.activity_type == "changed", str(detail.activity_type)

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
        # Record some details before updating the resource.
        length_before = len(model.Session.query(model.activity.Activity).all())
        details_length_before = len(model.Session.query(
            model.activity.ActivityDetail).all())
        before = datetime.datetime.now()

        # Query for the Package and Resource objects again, as the session that
        # they belong to may have been closed.
        package = model.Session.query(model.Package).get(package.id)
        resource = model.Session.query(model.Resource).get(resource.id)

        # Update the resource.
        if user is None:
            context = {'model': model, 'session': model.Session,
                    'user':'127.0.0.1', 'allow_partial_update':True}
        else:
            context = {'model': model, 'session': model.Session,
                    'user':user.name, 'allow_partial_update':True}
        resource_dict = {'id':resource.id, 'name':'edited'}
        result = resource_update(context, resource_dict)

        # Record some details after updating the resource.
        after = datetime.datetime.now()

        # Test for the presence of a correct activity stream item.
        activities = model.Session.query(model.activity.Activity).all()
        assert len(activities) == length_before + 1, str(activities)
        activity = activities[-1]
        assert activity.object_id == package.id, str(activity.object_id)
        if user:
            user_id = user.id
        else:
            user_id = 'not logged in'
        assert activity.user_id == user_id, str(activity.user_id)
        assert activity.activity_type == 'changed package', \
            str(activity.activity_type)
        if not activity.id:
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity.revision_id:
            assert False, "activity has no revision_id value"
        assert activity.timestamp >= before and activity.timestamp <= after, \
            activity.timestamp

        # Test for the presence of a correct activity detail item.
        details = model.Session.query(model.activity.ActivityDetail).all()
        assert len(details) == details_length_before + 1, str(details)
        detail = details[-1]
        assert detail.activity_id == activity.id, str(detail.activity_id)
        assert detail.object_id == resource.id, str(detail.object_id)
        assert detail.object_type == "Resource", str(detail.object_type)
        assert detail.activity_type == "changed", str(detail.activity_type)

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
        # Record some details before deleting the package.
        length_before = len(model.Session.query(model.activity.Activity).all())
        details_length_before = len(model.Session.query(
            model.activity.ActivityDetail).all())
        before = datetime.datetime.now()

        # Query for the package object again, as the session that it belongs to
        # may have been closed.
        package = model.Session.query(model.Package).get(package.id)

        # Delete the package.
        context = {'model': model, 'session': model.Session,
                'user':self.normal_user.name}
        package_dict = {'id':package.id}
        result = package_delete(context, package_dict)

        # Record some details after deleting the package.
        after = datetime.datetime.now()

        # Test for the presence of a correct activity stream item.
        activities = model.Session.query(model.activity.Activity).all()
        assert len(activities) == length_before + 1, ("Length of activities "
            "table should be %i but is %i" % (length_before + 1,
                len(activities)))
        activity = activities[-1]
        assert activity.object_id == package.id, str(activity.object_id)
        assert activity.user_id == self.normal_user.id, \
            str(activity.user_id)
        # "Deleted" packages actually show up as changed (the package's status
        # changes to "deleted" but the package is not expunged).
        assert activity.activity_type == 'changed package', \
            str(activity.activity_type)
        if not activity.id:
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity.revision_id:
            assert False, "activity has no revision_id value"
        assert activity.timestamp >= before and activity.timestamp <= after, \
            str(activity.timestamp)

        # Test for the presence of a correct activity detail item.
        details = model.Session.query(model.activity.ActivityDetail).all()
        assert len(details) == details_length_before + 1, ("Length of details "
            "table should be %i but is %i" % (details_length_before + 1,
                len(details)))
        detail = details[-1]
        assert detail.activity_id == activity.id, str(detail.activity_id)
        assert detail.object_id == package.id, str(detail.object_id)
        assert detail.object_type == "Package", str(detail.object_type)
        # "Deleted" packages actually show up as changed (the package's status
        # changes to "deleted" but the package is not expunged).
        assert detail.activity_type == "changed", str(detail.activity_type)

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
        # Record some details before deleting the resources.
        length_before = len(model.Session.query(model.activity.Activity).all())
        details_length_before = len(model.Session.query(
            model.activity.ActivityDetail).all())
        before = datetime.datetime.now()
        # Query the model for the Package object again, as the session that it
        # belongs to may have been closed.
        package = model.Session.query(model.Package).get(package.id)
        num_resources = len(package.resources)
        resource_ids = [resource.id for resource in package.resources]

        # Delete the resources.
        context = {'model': model, 'session': model.Session,
                'user':self.normal_user.name}
        data_dict = { 'id':package.id, 'resources':[] }
        result = package_update(context, data_dict)

        # Record some details after deleting the resources.
        after = datetime.datetime.now()

        # Test for the presence of a correct activity stream item.
        activities = model.Session.query(model.activity.Activity).all()
        assert len(activities) == length_before + 1, ("Length of activities "
            "table should be %i but is %i" % (length_before + 1,
                len(activities)))
        activity = activities[-1]
        assert activity.object_id == package.id, str(activity.object_id)
        assert activity.user_id == self.normal_user.id, \
            str(activity.user_id)
        assert activity.activity_type == 'changed package', \
            str(activity.activity_type)
        if not activity.id:
            assert False, "activity object has no id value"
        # TODO: Test for the _correct_ revision_id value.
        if not activity.revision_id:
            assert False, "activity has no revision_id value"
        assert activity.timestamp >= before and activity.timestamp <= after, \
            str(activity.timestamp)

        # Test for the presence of correct activity detail items.
        details = model.Session.query(model.activity.ActivityDetail).all()
        if num_resources == 0:
            assert len(details) == details_length_before, \
                    "Length of details table should be %i but is %i" \
                    % (details_length_before, len(details))
        else:
            assert len(details) == details_length_before + num_resources, \
                    "Length of details table should be %i but is %i" \
                    % (details_length_before + num_resources, len(details))
            new_details = details[-num_resources:]
            for detail in new_details:
                assert detail.activity_id == activity.id, \
                    "activity_id should be %s but is %s" \
                    % (activity.id, detail.activity_id)
                assert detail.object_id in resource_ids, str(detail.object_id)
                assert detail.object_type == "Resource", str(detail.object_type)
                assert detail.activity_type == "changed", str(detail.activity_type)

    def test_delete_resources(self):
        """
        Test deleted resource activity stream.

        Test that correct activity stream item and detail items are created
        when resources are deleted from packages.

        """
        for package in model.Session.query(model.Package).all():
            self._delete_resources(package)

    def test_user_activity_stream(self):
        tester = model.Session.query(model.user.User).filter_by(name="tester").first()
        context = {'model':model}
        data_dict = {'id':tester.id}
        activities = activity_show(context, data_dict)
        assert len(activities) == 2
        for activity in activities:
            assert activity['user_id'] == tester.id
