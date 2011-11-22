import datetime
import random
import logging
logger = logging.getLogger(__name__)

import paste.fixture
from paste.deploy import appconfig

from ckan.tests.pylons_controller import PylonsTestCase
from ckan.tests import conf_dir, CreateTestData
import ckan.model as model
from ckan.config.middleware import make_app 

class TestActivity(PylonsTestCase):

    @classmethod
    def setUp(cls):
        config = appconfig('config:test.ini', relative_to=conf_dir)
        wsgiapp = make_app(config.global_conf, **config.local_conf)
        cls.app = paste.fixture.TestApp(wsgiapp)
        CreateTestData.create()
        cls.rev = model.repo.new_revision()

    @classmethod
    def tearDown(cls):
        CreateTestData.delete()

    def test_create_package_not_logged_in(self):
        """
        Test that a correct activity stream item is emitted when a new package
        is created by a user who is not logged in.

        """
        # Create a new package, recording some details before and after.
        length_before = len(model.Session.query(model.activity.Activity).all())
        details_length_before = len(model.Session.query(
            model.activity.ActivityDetail).all())
        before = datetime.datetime.now()
        package_created = model.Package(name="A Test Package")
        model.Session.add(package_created)
        model.Session.commit()
        after = datetime.datetime.now()
        
        # Test for the presence of a correct activity stream item.
        activities = model.Session.query(model.activity.Activity).all()
        assert len(activities) == length_before + 1, str(activities)
        activity = activities[-1]
        assert activity.object_id == package_created.id, \
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

        # No activity stream detail should be emitted by adding a new package.
        details = model.Session.query(model.activity.ActivityDetail).all()
        assert len(details) == details_length_before, str(details)

    def test_create_package_logged_in(self):
        """
        Test that a correct activity stream item is emitted when a new package
        is created by a user who is not logged in.

        """
        pass

    def test_edit_package_not_logged_in(self):
        """
        Test that correct activity stream item and detail items are created
        when a package is edited by a user who is not logged in.
        
        """
        # Edit a package, recording some details before and after the edit.
        length_before = len(model.Session.query(model.activity.Activity).all())
        details_length_before = len(model.Session.query(
            model.activity.ActivityDetail).all())
        before = datetime.datetime.now()
        package = random.choice(model.Session.query(model.Package).all())
        package.title = 'Edited'
        model.Session.commit()
        after = datetime.datetime.now()

        # Test for the presence of a correct activity stream item.
        activities = model.Session.query(model.activity.Activity).all()
        assert len(activities) == length_before + 1, str(activities)
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
        assert len(details) == details_length_before + 1, str(details)
        detail = details[-1]
        assert detail.activity_id == activity.id, str(detail.activity_id)
        assert detail.object_id == package.id, str(detail.object_id)
        assert detail.object_type == "Package", str(detail.object_type)
        assert detail.activity_type == "changed", str(detail.activity_type)

    def test_edit_package_logged_in(self):
        pass

    def test_delete_package_not_logged_in(self):
        pass

    def test_delete_package_logged_in(self):
        pass
    
    def test_create_resource_not_logged_in(self):
        """
        Test that a correct activity stream item and detail item are emitted
        when a new resource is created by a user who is not logged in.

        """
        # Create a new resource, recording some details before and after.
        length_before = len(model.Session.query(model.activity.Activity).all())
        details_length_before = len(model.Session.query(
            model.activity.ActivityDetail).all())
        before = datetime.datetime.now()
        package = random.choice(model.Session.query(model.Package).all())        
        resource = model.Resource(
            url=u'http://www.annakarenina.com/download/x=1&y=2',
            format=u'plain text',
            description=u'Full text. Needs escaping: " Umlaut: \xfc',
            hash=u'abc123',
            extras={'size_extra': u'123'},
            )
        model.Session.add(resource)
        package.resources.append(resource)
        model.Session.commit()
        after = datetime.datetime.now()

        # Test for the presence of a correct activity stream item.
        activities = model.Session.query(model.activity.Activity).all()
        assert len(activities) == length_before + 1, str(activities)        
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
            activity.timestamp

        # Test for the presence of a correct activity detail item.
        details = model.Session.query(model.activity.ActivityDetail).all()
        assert len(details) == details_length_before + 1, str(details)
        detail = details[-1]
        assert detail.activity_id == activity.id, str(detail.activity_id)
        assert detail.object_id == resource.id, str(detail.object_id)
        assert detail.object_type == "Resource", str(detail.object_type)
        assert detail.activity_type == "new", str(detail.activity_type)

    def test_create_resource_logged_in(self):
        pass
    
    def test_edit_resource_not_logged_in(self):
        """
        Test that a correct activity stream item and detail item are emitted
        when a new resource is created by a user who is not logged in.

        """
        # Edit a resource, recording some details before and after.
        length_before = len(model.Session.query(model.activity.Activity).all())
        details_length_before = len(model.Session.query(
            model.activity.ActivityDetail).all())
        before = datetime.datetime.now()
        packages = model.Session.query(model.Package).all()
        packages = [package for package in packages if
            len(package.resources) > 0]
        package = random.choice(packages)
        resource = random.choice(package.resources)
        resource.description = "edited"
        model.Session.commit()
        after = datetime.datetime.now()

        # Test for the presence of a correct activity stream item.
        activities = model.Session.query(model.activity.Activity).all()
        assert len(activities) == length_before + 1, str(activities)        
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
            activity.timestamp

        # Test for the presence of a correct activity detail item.
        details = model.Session.query(model.activity.ActivityDetail).all()
        assert len(details) == details_length_before + 1, str(details)
        detail = details[-1]
        assert detail.activity_id == activity.id, str(detail.activity_id)
        assert detail.object_id == resource.id, str(detail.object_id)
        assert detail.object_type == "Resource", str(detail.object_type)
        assert detail.activity_type == "changed", str(detail.activity_type)

    def test_edit_resource_logged_in(self):
        pass
    
    def test_delete_resource_not_logged_in(self):
        pass
    
    def test_delete_resource_logged_in(self):
        pass
