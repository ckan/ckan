# encoding: utf-8

import copy
from collections import defaultdict

import mock
import pytest

import ckan.logic
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan import model
from ckan.migration.migrate_package_activity import (
    migrate_dataset,
    wipe_activity_detail,
    PackageDictizeMonkeyPatch,
)
from ckan.model.activity import package_activity_list


@pytest.mark.usefixtures(u"clean_db")
def test_migration():
    # Test that the migration correctly takes the package_revision (etc)
    # tables and populates the Activity.data, i.e. it does it the same as
    # if you made a change to the dataset with the current version of CKAN
    # and the Activity was created by activity_stream_item().
    dataset = factories.Dataset(
        resources=[{u"url": u"http://example.com/a.csv", u"format": u"csv"}]
    )
    activity = package_activity_list(dataset["id"], 0, 0)[0]
    activity_data_as_it_should_be = copy.deepcopy(activity.data)

    # Remove 'activity.data.package' to provoke the migration to regenerate
    # it from package_revision (etc)
    activity = model.Activity.get(activity.id)
    del activity.data["package"]
    model.repo.commit_and_remove()
    with PackageDictizeMonkeyPatch():
        migrate_dataset(dataset["name"], {})

    activity_data_migrated = package_activity_list(dataset["id"], 0, 0)[0].data
    assert activity_data_as_it_should_be == activity_data_migrated


@pytest.mark.usefixtures(u"clean_db")
def test_migration_with_multiple_revisions():
    dataset = factories.Dataset(
        resources=[{u"url": u"http://example.com/a.csv", u"format": u"csv"}]
    )
    dataset["title"] = u"Title 2"
    helpers.call_action(u"package_update", **dataset)
    dataset["title"] = u"Title 3"
    helpers.call_action(u"package_update", **dataset)

    activity = package_activity_list(dataset["id"], 0, 0)[1]
    activity_data_as_it_should_be = copy.deepcopy(activity.data["package"])

    # Remove 'activity.data.package.resources' to provoke the migration to
    # regenerate it from package_revision (etc)
    activity = model.Activity.get(activity.id)
    activity.data = {u"actor": None, u"package": {u"title": u"Title 2"}}
    model.Session.commit()
    model.Session.remove()
    # double check that worked...
    assert (
        not model.Activity.get(activity.id).data["package"].get(u"resources")
    )

    with PackageDictizeMonkeyPatch():
        migrate_dataset(dataset["name"], {})

    activity_data_migrated = package_activity_list(dataset["id"], 0, 0)[
        1
    ].data[u"package"]
    assert activity_data_as_it_should_be == activity_data_migrated
    assert activity_data_migrated["title"] == u"Title 2"


@pytest.mark.usefixtures(u"clean_db")
def test_a_contemporary_activity_needs_no_migration():
    # An Activity created by a change under the current CKAN should not
    # need a migration - check it does a nop
    dataset = factories.Dataset(
        resources=[{u"url": u"http://example.com/a.csv", u"format": u"csv"}]
    )
    activity = package_activity_list(dataset["id"], 0, 0)[0]
    activity_data_before = copy.deepcopy(activity.data)

    with PackageDictizeMonkeyPatch():
        migrate_dataset(dataset["name"], {})

    activity_data_after = package_activity_list(dataset["id"], 0, 0)[0].data
    assert activity_data_before == activity_data_after


@pytest.mark.usefixtures(u"clean_db")
def test_revision_missing():
    dataset = factories.Dataset(
        resources=[{u"url": u"http://example.com/a.csv", u"format": u"csv"}]
    )
    # delete a part of the revision, so package_show for the revision will
    # return NotFound
    model.Session.query(model.PackageRevision).delete()
    model.Session.commit()
    # delete 'activity.data.package.resources' so it needs migrating
    activity = package_activity_list(dataset["id"], 0, 0)[0]
    activity = model.Activity.get(activity.id)
    activity.data = {u"actor": None, u"package": {u"title": u"Test Dataset"}}
    model.Session.commit()
    model.Session.remove()
    # double check that worked...
    assert (
        not model.Activity.get(activity.id).data["package"].get(u"resources")
    )

    errors = defaultdict(int)
    with PackageDictizeMonkeyPatch():
        migrate_dataset(dataset["name"], errors)

    assert dict(errors) == {u"Revision missing": 1}
    activity_data_migrated = package_activity_list(dataset["id"], 0, 0)[0].data
    # the title is there so the activity stream can display it
    assert activity_data_migrated["package"]["title"] == u"Test Dataset"
    # the rest of the dataset is missing - better that than just the
    # dictized package without resources, extras etc
    assert u"resources" not in activity_data_migrated["package"]


@pytest.mark.usefixtures(u"clean_db")
def test_revision_and_data_missing():
    dataset = factories.Dataset(
        resources=[{u"url": u"http://example.com/a.csv", u"format": u"csv"}]
    )
    # delete a part of the revision, so package_show for the revision will
    # return NotFound
    model.Session.query(model.PackageRevision).delete()
    model.Session.commit()
    # delete 'activity.data.package' so it needs migrating AND the package
    # title won't be available, so we test how the migration deals with
    # that
    activity = package_activity_list(dataset["id"], 0, 0)[0]
    activity = model.Activity.get(activity.id)
    del activity.data["package"]
    model.Session.commit()

    errors = defaultdict(int)
    with PackageDictizeMonkeyPatch():
        migrate_dataset(dataset["name"], errors)

    assert dict(errors) == {u"Revision missing": 1}
    activity_data_migrated = package_activity_list(dataset["id"], 0, 0)[0].data
    # the title is there so the activity stream can display it
    assert activity_data_migrated["package"]["title"] == u"unknown"
    assert u"resources" not in activity_data_migrated["package"]


@pytest.mark.usefixtures(u"clean_db")
def test_package_show_error():
    dataset = factories.Dataset(
        resources=[{u"url": u"http://example.com/a.csv", u"format": u"csv"}]
    )
    # delete 'activity.data.package.resources' so it needs migrating
    activity = package_activity_list(dataset["id"], 0, 0)[0]
    activity = model.Activity.get(activity.id)
    activity.data = {u"actor": None, u"package": {u"title": u"Test Dataset"}}
    model.Session.commit()
    model.Session.remove()
    # double check that worked...
    assert (
        not model.Activity.get(activity.id).data["package"].get(u"resources")
    )

    errors = defaultdict(int)
    # package_show raises an exception - could be because data doesn't
    # conform to the latest dataset schema or is incompatible with
    # currently installed plugins. Those errors shouldn't prevent the
    # migration from going ahead.
    ckan.logic._actions["package_show"] = mock.MagicMock(
        side_effect=Exception(u"Schema error")
    )

    try:
        with PackageDictizeMonkeyPatch():
            migrate_dataset(dataset["name"], errors)
    finally:
        # restore package_show
        ckan.logic.clear_actions_cache()

    assert dict(errors) == {u"Schema error": 1}


@pytest.mark.usefixtures(u"clean_db")
def test_wipe_activity_detail():
    dataset = factories.Dataset()
    user = factories.User()
    activity = factories.Activity(
        user_id=user["id"],
        object_id=dataset["id"],
        revision_id=None,
        activity_type=u"new package",
        data={u"package": copy.deepcopy(dataset), u"actor": u"Mr Someone"},
    )
    ad = model.ActivityDetail(
        activity_id=activity["id"],
        object_id=dataset["id"],
        object_type=u"package",
        activity_type=u"new package",
    )
    model.Session.add(ad)
    model.Session.commit()
    assert model.Session.query(model.ActivityDetail).count() == 1
    wipe_activity_detail(delete_activity_detail=u"y")
    assert model.Session.query(model.ActivityDetail).count() == 0


@pytest.mark.usefixtures(u"clean_db")
def test_dont_wipe_activity_detail():
    dataset = factories.Dataset()
    user = factories.User()
    activity = factories.Activity(
        user_id=user["id"],
        object_id=dataset["id"],
        revision_id=None,
        activity_type=u"new package",
        data={u"package": copy.deepcopy(dataset), u"actor": u"Mr Someone"},
    )
    ad = model.ActivityDetail(
        activity_id=activity["id"],
        object_id=dataset["id"],
        object_type=u"package",
        activity_type=u"new package",
    )
    model.Session.add(ad)
    model.Session.commit()
    assert model.Session.query(model.ActivityDetail).count() == 1
    wipe_activity_detail(delete_activity_detail=u"n")  # i.e. don't do it!
    assert model.Session.query(model.ActivityDetail).count() == 1
