import datetime
import random
import logging
logger = logging.getLogger(__name__)

import ckan
import ckan.model as model
from ckan.logic.action.create import package_create, resource_create
from ckan.logic.action.update import package_update
from ckan.logic.action.delete import package_delete
from ckan.lib.dictization.model_dictize import package_dictize

class TestActivity:

    @classmethod
    def setup_class(cls):
        ckan.tests.CreateTestData.create()
        cls.sysadmin_user = model.User.get('testsysadmin')
        cls.normal_user = model.User.get('annafan')

    @classmethod
    def tearDownClass(cls):
        model.repo.rebuild_db()
        model.Session.remove()

    # TODO: Add tests for creating a package with some resources, groups, tags,
    # etc.
    def test_create_package(self):
        """
        Test new package activity stream.

        Test that correct activity stream item and detail items are emitted
        when a new package is created.

        """
        # Record some details before creating a new package.
        length_before = len(model.Session.query(model.activity.Activity).all())
        details_length_before = len(model.Session.query(
            model.activity.ActivityDetail).all())
        before = datetime.datetime.now()

        # Create a new package.
        context = {'model': model, 'session': model.Session,
                'user':TestActivity.normal_user.name}
        request_data = {'title':'My Test Package', 'name':'test_package'}
        package_created = package_create(context, request_data)

        # Record some details after creating the new package.
        after = datetime.datetime.now()

        # Test for the presence of a correct activity stream item.
        activities = model.Session.query(model.activity.Activity).all()
        assert len(activities) == length_before + 1, ("Length of activities "
            "table should be %i but is %i" % (length_before + 1,
                len(activities)))
        activity = activities[-1]
        assert activity.object_id == package_created['id'], \
            str(activity.object_id)
        assert activity.user_id == "Unknown IP Address", str(activity.user_id)
        assert activity.activity_type == 'new package', \
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
        assert detail.object_id == package_created['id'], str(detail.object_id)
        assert detail.object_type == "Package", str(detail.object_type)
        assert detail.activity_type == "new", str(detail.activity_type)

    # TODO: Add tests for creating a resource with some related packages,
    # groups, tags, etc.
    def test_create_resource(self):
        """
        Test new resource activity stream.

        Test that correct activity stream item and detail items are emitted
        when a new resource is created.

        """
        # Record some details before creating a new resource.
        length_before = len(model.Session.query(model.activity.Activity).all())
        details_length_before = len(model.Session.query(
            model.activity.ActivityDetail).all())
        before = datetime.datetime.now()

        # Create a new resource.
        context = {'model': model, 'session': model.Session,
                'user':TestActivity.normal_user.name}
        request_data = {'name':'test_resource'}
        resource_created = resource_create(context, request_data)

        # Record some details after creating the new resource.
        after = datetime.datetime.now()

        # Test for the presence of a correct activity stream item.
        activities = model.Session.query(model.activity.Activity).all()
        assert len(activities) == length_before + 1, ("Length of activities "
            "table should be %i but is %i" % (length_before + 1,
                len(activities)))
        activity = activities[-1]
        assert activity.object_id == package_created['id'], \
            str(activity.object_id)
        assert activity.user_id == "Unknown IP Address", str(activity.user_id)
        assert activity.activity_type == 'new resource', \
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
        assert detail.object_id == package_created['id'], str(detail.object_id)
        assert detail.object_type == "Resource", str(detail.object_type)
        assert detail.activity_type == "new", str(detail.activity_type)

    def _update_package(self, package):
        """
        Update the given package and test that the correct activity stream
        item and detail are emitted.

        """
        # Record some details before updating the package.
        length_before = len(model.Session.query(model.activity.Activity).all())
        details_length_before = len(model.Session.query(
            model.activity.ActivityDetail).all())
        before = datetime.datetime.now()

        # Query for the package object again, as the session that is belongs to
        # may have been closed.
        package = model.Session.query(model.Package).get(package.id)

        # Update the package.
        context = {'model': model, 'session': model.Session,
                'user':TestActivity.normal_user.name,
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
        assert activity.user_id == "Unknown IP Address", str(activity.user_id)
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
            self._update_package(package)

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

        # Query for the package object again, as the session that is belongs to
        # may have been closed.
        package = model.Session.query(model.Package).get(package.id)

        # Delete the package.
        context = {'model': model, 'session': model.Session,
                'user':TestActivity.normal_user.name}
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
        assert activity.user_id == "Unknown IP Address", str(activity.user_id)
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


    #def test_edit_resource_not_logged_in(self):
        #"""
        #Test that a correct activity stream item and detail item are emitted
        #when a new resource is created by a user who is not logged in.

        #"""
        ## Edit a resource, recording some details before and after.
        #length_before = len(model.Session.query(model.activity.Activity).all())
        #details_length_before = len(model.Session.query(
            #model.activity.ActivityDetail).all())
        #before = datetime.datetime.now()
        #packages = model.Session.query(model.Package).all()
        #packages = [package for package in packages if
            #len(package.resources) > 0]
        #package = random.choice(packages)
        #resource = random.choice(package.resources)
        #resource.description = "edited"
        #model.Session.commit()
        #after = datetime.datetime.now()

        ## Test for the presence of a correct activity stream item.
        #activities = model.Session.query(model.activity.Activity).all()
        #assert len(activities) == length_before + 1, str(activities)        
        #activity = activities[-1]
        #assert activity.object_id == package.id, str(activity.object_id)
        #assert activity.user_id == "Unknown IP Address", str(activity.user_id)
        #assert activity.activity_type == 'changed package', \
            #str(activity.activity_type)
        #if not activity.id:
            #assert False, "activity object has no id value"
        ## TODO: Test for the _correct_ revision_id value.
        #if not activity.revision_id:
            #assert False, "activity has no revision_id value"
        #assert activity.timestamp >= before and activity.timestamp <= after, \
            #activity.timestamp

        ## Test for the presence of a correct activity detail item.
        #details = model.Session.query(model.activity.ActivityDetail).all()
        #assert len(details) == details_length_before + 1, str(details)
        #detail = details[-1]
        #assert detail.activity_id == activity.id, str(detail.activity_id)
        #assert detail.object_id == resource.id, str(detail.object_id)
        #assert detail.object_type == "Resource", str(detail.object_type)
        #assert detail.activity_type == "changed", str(detail.activity_type)

    #def test_edit_resource_logged_in(self):
        #pass
    
    #def test_delete_resource_not_logged_in(self):
        #pass
    
    #def test_delete_resource_logged_in(self):
        #pass
