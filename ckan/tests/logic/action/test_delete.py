# encoding: utf-8

import re
from unittest import mock

import pytest

import ckan.lib.jobs as jobs
import ckan.lib.api_token as api_token
import ckan.logic as logic
from ckan.logic.action.get import package_show as core_package_show
import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers


@pytest.mark.usefixtures("non_clean_db")
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

    def test_resource_delete_for_delete(self):

        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset['id'])

        mock_package_show = mock.MagicMock()
        mock_package_show.side_effect = lambda context, data_dict: core_package_show(context, data_dict)

        with mock.patch.dict('ckan.logic._actions', {'package_show': mock_package_show}):
            helpers.call_action('resource_delete', id=resource['id'], description='hey')
            assert mock_package_show.call_args_list[1][0][0].get('for_update') is True

    @pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
    @pytest.mark.ckan_config("ckan.auth.allow_admin_collaborators", True)
    @pytest.mark.parametrize("role", ["admin", "editor"])
    def test_collaborators_can_delete_resources(self, role):

        org1 = factories.Organization()
        dataset = factories.Dataset(owner_org=org1["id"])
        resource = factories.Resource(package_id=dataset["id"])

        user = factories.User()

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity=role,
        )

        context = {
            "user": user["name"],
            "ignore_auth": False,
        }

        helpers.call_action(
            "resource_delete", context=context, id=resource["id"]
        )


@pytest.mark.usefixtures("non_clean_db")
class TestDeleteResource(object):
    def test_01_delete_resource(self):
        res = factories.Resource()
        pkg = helpers.call_action("package_show", id=res["package_id"])
        assert len(pkg["resources"]) == 1
        helpers.call_action("resource_delete", id=res["id"])
        pkg = helpers.call_action("package_show", id=res["package_id"])
        assert len(pkg["resources"]) == 0


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
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


@pytest.mark.ckan_config("ckan.plugins", "image_view datatables_view")
@pytest.mark.ckan_config("ckan.views.default_views", "")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
class TestClearResourceViews(object):
    def test_resource_view_clear(self):
        initial = model.Session.query(model.ResourceView).count()

        factories.ResourceView(view_type="image_view")
        factories.ResourceView(view_type="image_view")

        factories.ResourceView(view_type="datatables_view")
        factories.ResourceView(view_type="datatables_view")

        count = model.Session.query(model.ResourceView).count()

        assert count == initial + 4

        helpers.call_action("resource_view_clear", context={})

        count = model.Session.query(model.ResourceView).count()

        assert count == 0

    @pytest.mark.usefixtures("clean_db")
    def test_resource_view_clear_with_types(self):

        model.Session.query(model.ResourceView).count()
        factories.ResourceView(view_type="image_view")
        factories.ResourceView(view_type="image_view")

        factories.ResourceView(view_type="datatables_view")
        factories.ResourceView(view_type="datatables_view")

        count = model.Session.query(model.ResourceView).count()

        assert count == 4

        helpers.call_action(
            "resource_view_clear", context={}, view_types=["image_view"]
        )

        view_types = model.Session.query(model.ResourceView.view_type).all()

        assert len(view_types) == 2
        for view_type in view_types:
            assert view_type[0] == "datatables_view"


class TestDeleteTags(object):
    def test_tag_delete_with_unicode_returns_unicode_error(self):
        # There is not a lot of call for it, but in theory there could be
        # unicode in the ActionError error message, so ensure that comes
        # through in NotFound as unicode.
        with pytest.raises(logic.NotFound) as e:
            helpers.call_action("tag_delete", id=u"Delta symbol: \u0394")
        assert u"Delta symbol: \u0394" in e.value.message

    def test_no_id(self):
        with pytest.raises(logic.ValidationError):
            helpers.call_action("tag_delete")

    def test_does_not_exist(self):
        with pytest.raises(logic.NotFound):
            helpers.call_action("tag_delete", id="not-a-real-id")

    @pytest.mark.usefixtures("non_clean_db")
    def test_vocab_does_not_exist(self):
        vocab = factories.Vocabulary(tags=[{"name": "testtag"}])
        tag = vocab["tags"][0]
        with pytest.raises(logic.NotFound):
            helpers.call_action(
                "tag_delete", id=tag["id"], vocabulary_id="not-a-real-id"
            )

    @pytest.mark.usefixtures("clean_db")
    def test_delete_tag(self):
        tag1 = factories.Tag.stub().name
        tag2 = factories.Tag.stub().name
        pkg = factories.Dataset(tags=[{"name": tag2}, {"name": tag1}])
        assert len(pkg["tags"]) == 2
        tags = {t["name"] for t in pkg["tags"]}
        assert set(helpers.call_action("tag_list")) == tags

        for tag in pkg["tags"]:
            helpers.call_action("tag_delete", id=tag["id"])

        assert helpers.call_action("tag_list") == []
        pkg = helpers.call_action("package_show", id=pkg["id"])
        assert pkg["tags"] == []


@pytest.mark.usefixtures("non_clean_db")
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

    @pytest.mark.usefixtures("clean_db")
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
        parent = factories.Group()
        user = factories.User()
        group1 = factories.Group(
            extras=[{"key": "key1", "value": "val1"}],
            users=[{"name": user["name"]}],
            groups=[{"name": parent["name"]}],
        )
        ds = factories.Dataset(groups=[{"name": group1["name"]}])
        child = factories.Group(groups=[{"name": group1["name"]}])

        helpers.call_action("group_purge", id=group1["name"])

        # the Group and related objects are gone
        assert not model.Group.get(group1["name"])
        assert (
            model.Session.query(model.GroupExtra)
            .filter_by(group_id=group1["id"])
            .all()
            == []
        )
        # the only members left are the users for the parent and child
        assert sorted(
            (m.table_name, m.group.name)
            for m in model.Session.query(model.Member)
            .join(model.Group)
            .filter(
                model.Group.id.in_([parent["id"], child["id"], group1["id"]])
            )
        ) == sorted([("user", child["name"]), ("user", parent["name"])])
        # the dataset is still there though
        assert model.Package.get(ds["name"])

    def test_missing_id_returns_error(self):
        with pytest.raises(logic.ValidationError):
            helpers.call_action("group_purge")

    def test_bad_id_returns_404(self):
        with pytest.raises(logic.NotFound):
            helpers.call_action("group_purge", id="123")


@pytest.mark.usefixtures("non_clean_db")
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

    @pytest.mark.usefixtures("clean_db")
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
        parent = factories.Organization()
        user = factories.User()
        org1 = factories.Organization(
            extras=[{"key": "key1", "value": "val1"}],
            users=[{"name": user["name"]}],
            groups=[{"name": parent["name"]}],
        )
        ds = factories.Dataset(owner_org=org1["id"])
        child = factories.Organization(groups=[{"name": org1["name"]}])

        helpers.call_action("organization_purge", id=org1["name"])

        # the Organization and related objects are gone
        assert not model.Group.get(org1["id"])
        assert (
            model.Session.query(model.GroupExtra)
            .filter_by(group_id=org1["id"])
            .all()
            == []
        )
        # the only members left are the users for the parent and child
        assert sorted(
            (m.table_name, m.group.name)
            for m in model.Session.query(model.Member)
            .join(model.Group)
            .filter(
                model.Group.id.in_([parent["id"], child["id"], org1["id"]])
            )
        ) == sorted([("user", child["name"]), ("user", parent["name"])])
        # the dataset is still there though
        assert model.Package.get(ds["name"])

    def test_missing_id_returns_error(self):
        with pytest.raises(logic.ValidationError):
            helpers.call_action("organization_purge")

    def test_bad_id_returns_404(self):
        with pytest.raises(logic.NotFound):

            helpers.call_action("organization_purge", id="123")


@pytest.mark.usefixtures("non_clean_db")
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

    @pytest.mark.usefixtures("clean_db")
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
        group = factories.Group()
        org = factories.Organization()
        tag = factories.Tag.stub().name
        dataset = factories.Dataset(
            tags=[{"name": tag}],
            groups=[{"name": group["name"]}],
            owner_org=org["id"],
            extras=[{"key": "testkey", "value": "testvalue"}],
        )
        factories.Resource(package_id=dataset["id"])

        helpers.call_action(
            "dataset_purge", context={"ignore_auth": True}, id=dataset["name"]
        )

        # the Package and related objects are gone
        assert not model.Package.get(dataset["id"])
        assert (
            model.Session.query(model.Resource)
            .filter_by(package_id=dataset["id"])
            .all()
            == []
        )
        assert (
            model.Session.query(model.PackageTag)
            .filter_by(package_id=dataset["id"])
            .all()
            == []
        )
        # there is no clean-up of the tag object itself, just the PackageTag.
        assert model.Session.query(model.Tag).filter_by(name=tag).one()

        assert (
            model.Session.query(model.PackageExtra)
            .filter_by(package_id=dataset["id"])
            .all()
            == []
        )
        # the only member left is for the user created in factories.Group() and
        # factories.Organization()
        assert sorted(
            (m.table_name, m.group.name)
            for m in model.Session.query(model.Member)
            .join(model.Group)
            .filter(model.Group.id.in_([group["id"], org["id"]]))
        ) == sorted([("user", group["name"]), ("user", org["name"])])

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


@pytest.mark.usefixtures("non_clean_db")
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
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity="editor",
        )

        assert (
            len(
                helpers.call_action(
                    "package_collaborator_list", id=dataset["id"]
                )
            )
            == 1
        )

        context = {}
        params = {u"id": user[u"id"]}

        helpers.call_action(u"user_delete", context, **params)

        assert (
            len(
                helpers.call_action(
                    "package_collaborator_list", id=dataset["id"]
                )
            )
            == 0
        )


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
        self.enqueue(queue=u"q1")
        self.enqueue(queue=u"q1")
        self.enqueue(queue=u"q2")
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


@pytest.mark.usefixtures(u"non_clean_db")
class TestApiToken(object):
    def test_token_revoke(self):
        user = factories.User()
        token = helpers.call_action(
            u"api_token_create",
            context={u"model": model, u"user": user[u"name"]},
            user=user[u"name"],
            name="token-name",
        )["token"]
        token2 = helpers.call_action(
            u"api_token_create",
            context={u"model": model, u"user": user[u"name"]},
            user=user[u"name"],
            name="token-name-2",
        )["token"]

        tokens = helpers.call_action(
            u"api_token_list",
            context={u"model": model, u"user": user[u"name"]},
            user_id=user[u"name"],
        )
        assert len(tokens) == 2

        helpers.call_action(
            u"api_token_revoke",
            context={u"model": model, u"user": user[u"name"]},
            token=token,
        )

        tokens = helpers.call_action(
            u"api_token_list",
            context={u"model": model, u"user": user[u"name"]},
            user_id=user[u"name"],
        )
        assert len(tokens) == 1

        helpers.call_action(
            u"api_token_revoke",
            context={u"model": model, u"user": user[u"name"]},
            jti=api_token.decode(token2)[u"jti"],
        )

        tokens = helpers.call_action(
            u"api_token_list",
            context={u"model": model, u"user": user[u"name"]},
            user_id=user[u"name"],
        )
        assert len(tokens) == 0


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config(u"ckan.auth.allow_dataset_collaborators", False)
def test_delete_package_collaborator_when_config_disabled():

    dataset = factories.Dataset()
    user = factories.User()

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "package_collaborator_delete", id=dataset["id"], user_id=user["id"]
        )


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config(u"ckan.auth.allow_dataset_collaborators", True)
class TestPackageMemberDelete(object):
    def test_delete(self):

        dataset = factories.Dataset()
        user = factories.User()
        capacity = "editor"

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity=capacity,
        )

        assert (
            model.Session.query(model.PackageMember)
            .filter_by(package_id=dataset["id"])
            .count()
            == 1
        )

        helpers.call_action(
            "package_collaborator_delete", id=dataset["id"], user_id=user["id"]
        )

        assert (
            model.Session.query(model.PackageMember)
            .filter_by(package_id=dataset["id"])
            .count()
            == 0
        )

    def test_delete_dataset_not_found(self):
        dataset = {"id": "xxx"}
        user = factories.User()

        with pytest.raises(logic.NotFound):
            helpers.call_action(
                "package_collaborator_delete",
                id=dataset["id"],
                user_id=user["id"],
            )

    def test_delete_user_not_found(self):
        dataset = factories.Dataset()
        user = {"id": "yyy"}

        with pytest.raises(logic.NotFound):
            helpers.call_action(
                "package_collaborator_delete",
                id=dataset["id"],
                user_id=user["id"],
            )


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config(u"ckan.auth.allow_dataset_collaborators", True)
def test_package_delete_removes_collaborations():

    user = factories.User()
    dataset = factories.Dataset()
    helpers.call_action(
        "package_collaborator_create",
        id=dataset["id"],
        user_id=user["id"],
        capacity="editor",
    )

    assert (
        len(
            helpers.call_action(
                "package_collaborator_list_for_user", id=user["id"]
            )
        )
        == 1
    )

    context = {}
    params = {u"id": dataset[u"id"]}

    helpers.call_action(u"package_delete", context, **params)

    assert (
        len(
            helpers.call_action(
                "package_collaborator_list_for_user", id=user["id"]
            )
        )
        == 0
    )


class TestVocabularyDelete(object):
    @pytest.mark.usefixtures("non_clean_db")
    def test_basic(self):
        vocab = factories.Vocabulary()
        helpers.call_action("vocabulary_delete", id=vocab["id"])

        assert vocab["id"] not in {
            v["name"] for v in helpers.call_action("vocabulary_list")
        }

    @pytest.mark.usefixtures("non_clean_db")
    def test_not_existing(self):
        with pytest.raises(logic.NotFound):
            helpers.call_action("vocabulary_delete", id="does-not-exist")

    def test_no_id(self):
        with pytest.raises(logic.ValidationError):
            helpers.call_action("vocabulary_delete")


@pytest.mark.usefixtures("non_clean_db")
class TestMemberDelete:
    def test_member_delete_accepts_object_name_or_id(self):
        org = factories.Organization()
        user = factories.User()
        helpers.call_action(
            "member_delete",
            object=user["id"],
            id=org["id"],
            object_type="user",
            capacity="member",
        )
        helpers.call_action(
            "member_create",
            object=user["name"],
            id=org["id"],
            object_type="user",
            capacity="member",
        )

    def test_member_delete_raises_if_user_unauthorized_to_update_group(self):
        org = factories.Organization()
        pkg = factories.Dataset()
        user = factories.User()
        context = {"ignore_auth": False, "user": user["name"]}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_action(
                "member_delete",
                context,
                object=pkg["name"],
                id=org["id"],
                object_type="package",
                capacity="member",
            )

    def test_member_delete_raises_if_any_required_parameter_isnt_defined(self):
        org = factories.Organization()
        pkg = factories.Dataset()
        data = dict(
            object=pkg["name"],
            id=org["id"],
            object_type="package",
            capacity="member",
        )
        for key in ["id", "object", "object_type"]:
            payload = data.copy()
            payload.pop(key)
            with pytest.raises(logic.ValidationError):
                helpers.call_action("member_delete", **payload)

    def test_member_delete_raises_if_group_wasnt_found(self):
        pkg = factories.Dataset()
        with pytest.raises(logic.NotFound):
            helpers.call_action(
                "member_delete",
                object=pkg["name"],
                id="not-real",
                object_type="package",
                capacity="member",
            )

    def test_member_delete_raises_if_object_wasnt_found(self):
        org = factories.Organization()
        with pytest.raises(logic.NotFound):
            helpers.call_action(
                "member_delete",
                object="not-real",
                id=org["id"],
                object_type="package",
                capacity="member",
            )

    def test_member_delete_raises_if_object_type_is_invalid(self):
        org = factories.Organization()
        pkg = factories.Dataset()
        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "member_delete",
                object=pkg["name"],
                id=org["id"],
                object_type="notvalid",
                capacity="member",
            )
