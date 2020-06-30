# encoding: utf-8

import re

import pytest
from six import text_type

import ckan.lib.jobs as jobs
import ckan.lib.search as search
import ckan.lib.api_token as api_token
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as p
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestDelete:
    def test_resource_delete(self):
        user = factories.User()
        sysadmin = factories.Sysadmin()
        resource = factories.Resource(user=user)
        context = {}
        params = {"id": resource["id"]}

        helpers.call_action("resource_delete", context, **params)

        # Not even a sysadmin can see it now
        with pytest.raises(logic.NotFound):
            helpers.call_action(
                "resource_show", {"user": sysadmin["name"]}, **params
            )
        # It is still there but with state=deleted
        res_obj = model.Resource.get(resource["id"])
        assert res_obj.state == "deleted"


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
class TestDeleteResourceViews(object):
    def test_resource_view_delete(self):
        resource_view = factories.ResourceView()

        params = {"id": resource_view["id"]}

        helpers.call_action("resource_view_delete", context={}, **params)

        with pytest.raises(logic.NotFound):
            helpers.call_action("resource_view_show", context={}, **params)

        # The model object is actually deleted
        resource_view_obj = model.ResourceView.get(resource_view["id"])
        assert resource_view_obj is None

    def test_delete_no_id_raises_validation_error(self):

        params = {}

        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_delete", context={}, **params)

    def test_delete_wrong_id_raises_not_found_error(self):

        params = {"id": "does_not_exist"}

        with pytest.raises(logic.NotFound):
            helpers.call_action("resource_view_delete", context={}, **params)


@pytest.mark.ckan_config("ckan.plugins", "image_view recline_view")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestClearResourceViews(object):
    def test_resource_view_clear(self):
        factories.ResourceView(view_type="image_view")
        factories.ResourceView(view_type="image_view")

        factories.ResourceView(view_type="recline_view")
        factories.ResourceView(view_type="recline_view")

        count = model.Session.query(model.ResourceView).count()

        assert count == 4

        helpers.call_action("resource_view_clear", context={})

        count = model.Session.query(model.ResourceView).count()

        assert count == 0

    def test_resource_view_clear_with_types(self):
        factories.ResourceView(view_type="image_view")
        factories.ResourceView(view_type="image_view")

        factories.ResourceView(view_type="recline_view")
        factories.ResourceView(view_type="recline_view")

        count = model.Session.query(model.ResourceView).count()

        assert count == 4

        helpers.call_action(
            "resource_view_clear", context={}, view_types=["image_view"]
        )

        view_types = model.Session.query(model.ResourceView.view_type).all()

        assert len(view_types) == 2
        for view_type in view_types:
            assert view_type[0] == "recline_view"


class TestDeleteTags(object):
    def test_tag_delete_with_unicode_returns_unicode_error(self):
        # There is not a lot of call for it, but in theory there could be
        # unicode in the ActionError error message, so ensure that comes
        # through in NotFound as unicode.
        try:
            helpers.call_action("tag_delete", id=u"Delta symbol: \u0394")
        except logic.NotFound as e:
            assert u"Delta symbol: \u0394" in text_type(e)
        else:
            assert 0, "Should have raised NotFound"


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestGroupPurge(object):
    def test_a_non_sysadmin_cant_purge_group(self):
        user = factories.User()
        group = factories.Group(user=user)

        with pytest.raises(logic.NotAuthorized):
            helpers.call_action(
                "group_purge",
                context={"user": user["name"], "ignore_auth": False},
                id=group["name"],
            )

    def test_purged_group_does_not_show(self):
        group = factories.Group()

        helpers.call_action("group_purge", id=group["name"])

        with pytest.raises(logic.NotFound):
            helpers.call_action("group_show", context={}, id=group["name"])

    def test_purged_group_is_not_listed(self):
        group = factories.Group()

        helpers.call_action("group_purge", id=group["name"])

        assert helpers.call_action("group_list", context={}) == []

    def test_dataset_in_a_purged_group_no_longer_shows_that_group(self):
        group = factories.Group()
        dataset = factories.Dataset(groups=[{"name": group["name"]}])

        helpers.call_action("group_purge", id=group["name"])

        dataset_shown = helpers.call_action(
            "package_show", context={}, id=dataset["id"]
        )
        assert dataset_shown["groups"] == []

    @pytest.mark.usefixtures("clean_index")
    def test_purged_group_is_not_in_search_results_for_its_ex_dataset(self):
        group = factories.Group()
        dataset = factories.Dataset(groups=[{"name": group["name"]}])

        def get_search_result_groups():
            results = helpers.call_action(
                "package_search", q=dataset["title"]
            )["results"]
            return [g["name"] for g in results[0]["groups"]]

        assert get_search_result_groups() == [group["name"]]

        helpers.call_action("group_purge", id=group["name"])

        assert get_search_result_groups() == []

    def test_purged_group_leaves_no_trace_in_the_model(self):
        factories.Group(name="parent")
        user = factories.User()
        group1 = factories.Group(
            name="group1",
            extras=[{"key": "key1", "value": "val1"}],
            users=[{"name": user["name"]}],
            groups=[{"name": "parent"}],
        )
        factories.Dataset(name="ds", groups=[{"name": "group1"}])
        factories.Group(name="child", groups=[{"name": "group1"}])

        helpers.call_action("group_purge", id=group1["name"])

        # the Group and related objects are gone
        assert sorted(
            [g.name for g in model.Session.query(model.Group).all()]
        ) == ["child", "parent"]
        assert model.Session.query(model.GroupExtra).all() == []
        # the only members left are the users for the parent and child
        assert sorted(
            [
                (m.table_name, m.group.name)
                for m in model.Session.query(model.Member).join(model.Group)
            ]
        ) == [("user", "child"), ("user", "parent")]
        # the dataset is still there though
        assert [p.name for p in model.Session.query(model.Package)] == ["ds"]

    def test_missing_id_returns_error(self):
        with pytest.raises(logic.ValidationError):
            helpers.call_action("group_purge")

    def test_bad_id_returns_404(self):
        with pytest.raises(logic.NotFound):
            helpers.call_action("group_purge", id="123")


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestOrganizationPurge(object):
    def test_a_non_sysadmin_cant_purge_org(self):
        user = factories.User()
        org = factories.Organization(user=user)

        with pytest.raises(logic.NotAuthorized):
            helpers.call_action(
                "organization_purge",
                context={"user": user["name"], "ignore_auth": False},
                id=org["name"],
            )

    def test_purged_org_does_not_show(self):
        org = factories.Organization()

        helpers.call_action("organization_purge", id=org["name"])

        with pytest.raises(logic.NotFound):
            helpers.call_action(
                "organization_show", context={}, id=org["name"]
            )

    def test_purged_org_is_not_listed(self):
        org = factories.Organization()

        helpers.call_action("organization_purge", id=org["name"])

        assert helpers.call_action("organization_list", context={}) == []

    def test_dataset_in_a_purged_org_no_longer_shows_that_org(self):
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])

        helpers.call_action("organization_purge", id=org["name"])

        dataset_shown = helpers.call_action(
            "package_show", context={}, id=dataset["id"]
        )
        assert dataset_shown["owner_org"] is None

    @pytest.mark.usefixtures("clean_index")
    def test_purged_org_is_not_in_search_results_for_its_ex_dataset(self):
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])

        def get_search_result_owner_org():
            results = helpers.call_action(
                "package_search", q=dataset["title"]
            )["results"]
            return results[0]["owner_org"]

        assert get_search_result_owner_org() == org["id"]

        helpers.call_action("organization_purge", id=org["name"])

        assert get_search_result_owner_org() is None

    def test_purged_organization_leaves_no_trace_in_the_model(self):
        factories.Organization(name="parent")
        user = factories.User()
        org1 = factories.Organization(
            name="org1",
            extras=[{"key": "key1", "value": "val1"}],
            users=[{"name": user["name"]}],
            groups=[{"name": "parent"}],
        )
        factories.Dataset(name="ds", owner_org=org1["id"])
        factories.Organization(name="child", groups=[{"name": "org1"}])

        helpers.call_action("organization_purge", id=org1["name"])

        # the Organization and related objects are gone
        assert sorted(
            [o.name for o in model.Session.query(model.Group).all()]
        ) == ["child", "parent"]
        assert model.Session.query(model.GroupExtra).all() == []
        # the only members left are the users for the parent and child
        assert sorted(
            [
                (m.table_name, m.group.name)
                for m in model.Session.query(model.Member).join(model.Group)
            ]
        ) == [("user", "child"), ("user", "parent")]
        # the dataset is still there though
        assert [p.name for p in model.Session.query(model.Package)] == ["ds"]

    def test_missing_id_returns_error(self):
        with pytest.raises(logic.ValidationError):
            helpers.call_action("organization_purge")

    def test_bad_id_returns_404(self):
        with pytest.raises(logic.NotFound):

            helpers.call_action("organization_purge", id="123")


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestDatasetPurge(object):
    def test_a_non_sysadmin_cant_purge_dataset(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        with pytest.raises(logic.NotAuthorized):
            helpers.call_action(
                "dataset_purge",
                context={"user": user["name"], "ignore_auth": False},
                id=dataset["name"],
            )

    def test_purged_dataset_does_not_show(self):
        dataset = factories.Dataset()

        helpers.call_action(
            "dataset_purge", context={"ignore_auth": True}, id=dataset["name"]
        )

        with pytest.raises(logic.NotFound):
            helpers.call_action("package_show", context={}, id=dataset["name"])

    def test_purged_dataset_is_not_listed(self):
        dataset = factories.Dataset()

        helpers.call_action("dataset_purge", id=dataset["name"])

        assert helpers.call_action("package_list", context={}) == []

    def test_group_no_longer_shows_its_purged_dataset(self):
        group = factories.Group()
        dataset = factories.Dataset(groups=[{"name": group["name"]}])

        helpers.call_action("dataset_purge", id=dataset["name"])

        dataset_shown = helpers.call_action(
            "group_show", context={}, id=group["id"], include_datasets=True
        )
        assert dataset_shown["packages"] == []

    @pytest.mark.usefixtures("clean_index", "with_plugins")
    def test_purged_dataset_is_not_in_search_results(self):
        dataset = factories.Dataset()

        def get_search_results():
            results = helpers.call_action(
                "package_search", q=dataset["title"]
            )["results"]
            return [d["name"] for d in results]

        assert get_search_results() == [dataset["name"]]
        helpers.call_action("dataset_purge", id=dataset["name"])

        assert get_search_results() == []

    def test_purged_dataset_leaves_no_trace_in_the_model(self):
        factories.Group(name="group1")
        org = factories.Organization()
        dataset = factories.Dataset(
            tags=[{"name": "tag1"}],
            groups=[{"name": "group1"}],
            owner_org=org["id"],
            extras=[{"key": "testkey", "value": "testvalue"}],
        )
        factories.Resource(package_id=dataset["id"])

        helpers.call_action(
            "dataset_purge", context={"ignore_auth": True}, id=dataset["name"]
        )

        # the Package and related objects are gone
        assert model.Session.query(model.Package).all() == []
        assert model.Session.query(model.Resource).all() == []
        assert model.Session.query(model.PackageTag).all() == []
        # there is no clean-up of the tag object itself, just the PackageTag.
        assert [t.name for t in model.Session.query(model.Tag).all()] == [
            "tag1"
        ]
        assert model.Session.query(model.PackageExtra).all() == []
        # the only member left is for the user created in factories.Group() and
        # factories.Organization()
        assert sorted(
            [
                (m.table_name, m.group.name)
                for m in model.Session.query(model.Member).join(model.Group)
            ]
        ) == [("user", "group1"), ("user", org["name"])]

    def test_purged_dataset_removed_from_relationships(self):
        child = factories.Dataset()
        parent = factories.Dataset()
        grandparent = factories.Dataset()

        helpers.call_action(
            "package_relationship_create",
            subject=child["id"],
            type="child_of",
            object=parent["id"],
        )

        helpers.call_action(
            "package_relationship_create",
            subject=parent["id"],
            type="child_of",
            object=grandparent["id"],
        )

        assert len(model.Session.query(model.PackageRelationship).all()) == 2

        helpers.call_action(
            "dataset_purge", context={"ignore_auth": True}, id=parent["name"]
        )

        assert model.Session.query(model.PackageRelationship).all() == []

    def test_missing_id_returns_error(self):
        with pytest.raises(logic.ValidationError):
            helpers.call_action("dataset_purge")

    def test_bad_id_returns_404(self):
        with pytest.raises(logic.NotFound):

            helpers.call_action("dataset_purge", id="123")


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestUserDelete(object):
    def test_user_delete(self):
        user = factories.User()
        context = {}
        params = {u"id": user[u"id"]}

        helpers.call_action(u"user_delete", context, **params)

        # It is still there but with state=deleted
        user_obj = model.User.get(user[u"id"])
        assert user_obj.state == u"deleted"

    def test_user_delete_but_user_doesnt_exist(self):
        context = {}
        params = {u"id": "unknown"}

        with pytest.raises(logic.NotFound):
            helpers.call_action(u"user_delete", context, **params)

    def test_user_delete_removes_memberships(self):
        user = factories.User()
        factories.Organization(
            users=[{u"name": user[u"id"], u"capacity": u"admin"}]
        )

        factories.Group(users=[{u"name": user[u"id"], u"capacity": u"admin"}])

        user_memberships = (
            model.Session.query(model.Member)
            .filter(model.Member.table_id == user[u"id"])
            .all()
        )

        assert len(user_memberships) == 2

        assert [m.state for m in user_memberships] == [u"active", u"active"]

        context = {}
        params = {u"id": user[u"id"]}

        helpers.call_action(u"user_delete", context, **params)

        user_memberships = (
            model.Session.query(model.Member)
            .filter(model.Member.table_id == user[u"id"])
            .all()
        )

        # Member objects are still there, but flagged as deleted
        assert len(user_memberships) == 2

        assert [m.state for m in user_memberships] == [u"deleted", u"deleted"]

    def test_user_delete_removes_memberships_when_using_name(self):
        user = factories.User()
        factories.Organization(
            users=[{u"name": user[u"id"], u"capacity": u"admin"}]
        )

        factories.Group(users=[{u"name": user[u"id"], u"capacity": u"admin"}])

        context = {}
        params = {u"id": user[u"name"]}

        helpers.call_action(u"user_delete", context, **params)

        user_memberships = (
            model.Session.query(model.Member)
            .filter(model.Member.table_id == user[u"id"])
            .all()
        )

        # Member objects are still there, but flagged as deleted
        assert len(user_memberships) == 2

        assert [m.state for m in user_memberships] == [u"deleted", u"deleted"]

    @pytest.mark.ckan_config(u"ckan.auth.allow_dataset_collaborators", True)
    def test_user_delete_removes_collaborations(self):
        user = factories.User()
        dataset = factories.Dataset()
        helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=user['id'], capacity='editor')

        assert len(helpers.call_action('package_collaborator_list', id=dataset['id'])) == 1

        context = {}
        params = {u"id": user[u"id"]}

        helpers.call_action(u"user_delete", context, **params)

        assert len(helpers.call_action('package_collaborator_list', id=dataset['id'])) == 0


class TestJobClear(helpers.FunctionalRQTestBase):
    def test_all_queues(self):
        """
        Test clearing all queues.
        """
        self.enqueue()
        self.enqueue(queue=u"q")
        self.enqueue(queue=u"q")
        self.enqueue(queue=u"q")
        queues = helpers.call_action(u"job_clear")
        assert {jobs.DEFAULT_QUEUE_NAME, u"q"} == set(queues)
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 0

    def test_specific_queues(self):
        """
        Test clearing specific queues.
        """
        job1 = self.enqueue()
        job2 = self.enqueue(queue=u"q1")
        job3 = self.enqueue(queue=u"q1")
        job4 = self.enqueue(queue=u"q2")
        with helpers.recorded_logs(u"ckan.logic") as logs:
            queues = helpers.call_action(u"job_clear", queues=[u"q1", u"q2"])
        assert {u"q1", u"q2"} == set(queues)
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 1
        assert all_jobs[0] == job1
        logs.assert_log(u"info", u"q1")
        logs.assert_log(u"info", u"q2")


class TestJobCancel(helpers.FunctionalRQTestBase):
    def test_existing_job(self):
        """
        Test cancelling an existing job.
        """
        job1 = self.enqueue(queue=u"q")
        job2 = self.enqueue(queue=u"q")
        with helpers.recorded_logs(u"ckan.logic") as logs:
            helpers.call_action(u"job_cancel", id=job1.id)
        all_jobs = self.all_jobs()
        assert len(all_jobs) == 1
        assert all_jobs[0] == job2
        with pytest.raises(KeyError):
            jobs.job_from_id(job1.id)
        logs.assert_log(u"info", re.escape(job1.id))

    def test_not_existing_job(self):
        with pytest.raises(logic.NotFound):
            helpers.call_action(u"job_cancel", id=u"does-not-exist")


@pytest.mark.usefixtures(u"clean_db")
class TestApiToken(object):

    def test_token_revoke(self):
        user = factories.User()
        token = helpers.call_action(u"api_token_create", context={
            u"model": model,
            u"user": user[u"name"]
        }, user=user[u"name"], name="token-name")['token']
        token2 = helpers.call_action(u"api_token_create", context={
            u"model": model,
            u"user": user[u"name"]
        }, user=user[u"name"], name="token-name-2")['token']

        tokens = helpers.call_action(u"api_token_list", context={
            u"model": model,
            u"user": user[u"name"]
        }, user=user[u"name"])
        assert len(tokens) == 2

        helpers.call_action(u"api_token_revoke", context={
            u"model": model,
            u"user": user[u"name"]
        }, token=token)

        tokens = helpers.call_action(u"api_token_list", context={
            u"model": model,
            u"user": user[u"name"]
        }, user=user[u"name"])
        assert len(tokens) == 1

        helpers.call_action(u"api_token_revoke", context={
            u"model": model,
            u"user": user[u"name"]
        }, jti=api_token.decode(token2)[u'jti'])

        tokens = helpers.call_action(u"api_token_list", context={
            u"model": model,
            u"user": user[u"name"]
        }, user=user[u"name"])
        assert len(tokens) == 0


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config(u"ckan.auth.allow_dataset_collaborators", False)
def test_delete_package_collaborator_when_config_disabled():

    dataset = factories.Dataset()
    user = factories.User()

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            'package_collaborator_delete',
            id=dataset['id'], user_id=user['id'])


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config(u"ckan.auth.allow_dataset_collaborators", True)
class TestPackageMemberDelete(object):

    def test_delete(self):

        dataset = factories.Dataset()
        user = factories.User()
        capacity = 'editor'

        helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=user['id'], capacity=capacity)

        assert model.Session.query(model.PackageMember).count() == 1

        helpers.call_action(
            'package_collaborator_delete',
            id=dataset['id'], user_id=user['id'])

        assert model.Session.query(model.PackageMember).count() == 0

    def test_delete_dataset_not_found(self):
        dataset = {'id': 'xxx'}
        user = factories.User()

        with pytest.raises(logic.NotFound):
            helpers.call_action(
                'package_collaborator_delete',
                id=dataset['id'], user_id=user['id'])

    def test_delete_user_not_found(self):
        dataset = factories.Dataset()
        user = {'id': 'yyy'}

        with pytest.raises(logic.NotFound):
            helpers.call_action(
                'package_collaborator_delete',
                id=dataset['id'], user_id=user['id'])


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config(u"ckan.auth.allow_dataset_collaborators", True)
def test_package_delete_removes_collaborations():

    user = factories.User()
    dataset = factories.Dataset()
    helpers.call_action(
        'package_collaborator_create',
        id=dataset['id'], user_id=user['id'], capacity='editor')

    assert len(helpers.call_action('package_collaborator_list_for_user', id=user['id'])) == 1

    context = {}
    params = {u"id": dataset[u"id"]}

    helpers.call_action(u"package_delete", context, **params)

    assert len(helpers.call_action('package_collaborator_list_for_user', id=user['id'])) == 0
