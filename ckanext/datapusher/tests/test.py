# encoding: utf-8

import datetime

import json
import pytest
import responses

import ckan.lib.create_test_data as ctd
import ckan.model as model
import ckan.plugins as p
from ckan.tests import factories
from ckan.tests.helpers import call_action
from ckan.common import config
from ckanext.datastore.tests.helpers import set_url_type
from ckanext.datapusher.tests import get_api_token


@pytest.mark.ckan_config("ckan.plugins", "datastore datapusher")
@pytest.mark.ckan_config("ckan.datapusher.api_token", get_api_token())
@pytest.mark.usefixtures("with_plugins", "non_clean_db")
class TestDatastoreNew:
    def test_create_ckan_resource_in_package(self, app, api_token):
        package = factories.Dataset.model()
        data = {"resource": {"package_id": package.id}}
        auth = {"Authorization": api_token["token"]}
        res = app.post(
            "/api/action/datastore_create",
            json=data,
            extra_environ=auth,
            status=200,
        )
        res_dict = json.loads(res.body)

        assert "resource_id" in res_dict["result"]
        assert len(package.resources) == 1

        res = call_action("resource_show",
                          id=res_dict["result"]["resource_id"])
        assert res["url"].endswith("/datastore/dump/" + res["id"]), res

    @responses.activate
    def test_providing_res_with_url_calls_datapusher_correctly(self, app):
        config["datapusher.url"] = "http://datapusher.ckan.org"
        responses.add(
            responses.POST,
            "http://datapusher.ckan.org/job",
            content_type="application/json",
            body=json.dumps({"job_id": "foo", "job_key": "bar"}),
        )
        responses.add_passthru(config["solr_url"])

        package = factories.Dataset.model()

        call_action("datastore_create",
                    resource=dict(package_id=package.id, url="demo.ckan.org"))

        assert len(package.resources) == 1
        resource = package.resources[0]
        data = json.loads(responses.calls[-1].request.body)
        assert data["metadata"]["resource_id"] == resource.id, data
        assert not data["metadata"].get("ignore_hash"), data
        assert data["result_url"].endswith("/action/datapusher_hook"), data
        assert data["result_url"].startswith("http://"), data


@pytest.mark.ckan_config("ckan.plugins", "datastore datapusher")
@pytest.mark.ckan_config("ckan.datapusher.api_token", get_api_token())
@pytest.mark.usefixtures("with_plugins")
class TestDatastoreCreate(object):
    sysadmin_user = None
    normal_user = None

    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db):
        ctd.CreateTestData.create()
        self.sysadmin_user = factories.Sysadmin()
        self.sysadmin_token = factories.APIToken(
            user=self.sysadmin_user["id"])["token"]
        self.normal_user = factories.User()
        self.normal_user_token = factories.APIToken(
            user=self.normal_user["id"])["token"]
        set_url_type(
            model.Package.get("annakarenina").resources, self.sysadmin_user
        )

    @responses.activate
    def test_pass_the_received_ignore_hash_param_to_the_datapusher(self, app):
        config["datapusher.url"] = "http://datapusher.ckan.org"
        responses.add(
            responses.POST,
            "http://datapusher.ckan.org/job",
            content_type="application/json",
            body=json.dumps({"job_id": "foo", "job_key": "bar"}),
        )

        package = model.Package.get("annakarenina")
        resource = package.resources[0]

        call_action(
            "datapusher_submit",
            resource_id=resource.id,
            ignore_hash=True,
        )

        data = json.loads(responses.calls[-1].request.body)
        assert data["metadata"]["ignore_hash"], data

    def test_cant_provide_resource_and_resource_id(self, app):
        package = model.Package.get("annakarenina")
        resource = package.resources[0]
        data = {
            "resource_id": resource.id,
            "resource": {"package_id": package.id},
        }

        auth = {"Authorization": self.sysadmin_token}
        res = app.post(
            "/api/action/datastore_create",
            json=data,
            extra_environ=auth,
            status=409,
        )
        res_dict = json.loads(res.body)

        assert res_dict["error"]["__type"] == "Validation Error"

    @responses.activate
    def test_send_datapusher_creates_task(self, test_request_context):
        responses.add(
            responses.POST,
            "http://datapusher.ckan.org/job",
            content_type="application/json",
            body=json.dumps({"job_id": "foo", "job_key": "bar"}),
        )

        package = model.Package.get("annakarenina")
        resource = package.resources[0]

        context = {"ignore_auth": True, "user": self.sysadmin_user["name"]}
        with test_request_context():
            p.toolkit.get_action("datapusher_submit")(
                context, {"resource_id": resource.id}
            )

        context.pop("task_status", None)

        task = p.toolkit.get_action("task_status_show")(
            context,
            {
                "entity_id": resource.id,
                "task_type": "datapusher",
                "key": "datapusher",
            },
        )

        assert task["state"] == "pending", task

    def _call_datapusher_hook(self, user, app):
        package = model.Package.get("annakarenina")
        resource = package.resources[0]

        context = {"user": self.sysadmin_user["name"]}

        p.toolkit.get_action("task_status_update")(
            context,
            {
                "entity_id": resource.id,
                "entity_type": "resource",
                "task_type": "datapusher",
                "key": "datapusher",
                "value": '{"job_id": "my_id", "job_key":"my_key"}',
                "last_updated": str(datetime.datetime.now()),
                "state": "pending",
            },
        )

        data = {"status": "success", "metadata": {"resource_id": resource.id}}

        if user["sysadmin"]:
            auth = {"Authorization": self.sysadmin_token}
        else:
            auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datapusher_hook",
            json=data,
            extra_environ=auth,
            status=200,
        )
        res_dict = json.loads(res.body)

        assert res_dict["success"] is True

        task = call_action(
            "task_status_show",
            entity_id=resource.id,
            task_type="datapusher",
            key="datapusher",
        )

        assert task["state"] == "success", task

        task = call_action(
            "task_status_show",
            entity_id=resource.id,
            task_type="datapusher",
            key="datapusher",
        )

        assert task["state"] == "success", task

    def test_datapusher_hook_sysadmin(self, app, test_request_context):
        with test_request_context():
            self._call_datapusher_hook(self.sysadmin_user, app)

    def test_datapusher_hook_normal_user(self, app, test_request_context):
        with test_request_context():
            self._call_datapusher_hook(self.normal_user, app)

    def test_datapusher_hook_no_metadata(self, app):
        data = {"status": "success"}

        app.post("/api/action/datapusher_hook", json=data, status=409)

    def test_datapusher_hook_no_status(self, app):
        data = {"metadata": {"resource_id": "res_id"}}

        app.post("/api/action/datapusher_hook", json=data, status=409)

    def test_datapusher_hook_no_resource_id_in_metadata(self, app):
        data = {"status": "success", "metadata": {}}

        app.post("/api/action/datapusher_hook", json=data, status=409)

    @responses.activate
    @pytest.mark.ckan_config(
        "ckan.datapusher.callback_url_base", "https://ckan.example.com"
    )
    @pytest.mark.ckan_config(
        "ckan.datapusher.url", "http://datapusher.ckan.org"
    )
    def test_custom_callback_url_base(self, app):

        package = model.Package.get("annakarenina")
        resource = package.resources[0]

        responses.add(
            responses.POST,
            "http://datapusher.ckan.org/job",
            content_type="application/json",
            body=json.dumps({"job_id": "foo", "job_key": "barloco"}),
        )
        responses.add_passthru(config["solr_url"])

        call_action(
            "datapusher_submit",
            resource_id=resource.id,
            ignore_hash=True,
        )

        data = json.loads(responses.calls[-1].request.body)
        assert (
            data["result_url"]
            == "https://ckan.example.com/api/3/action/datapusher_hook"
        )

    @responses.activate
    @pytest.mark.ckan_config(
        "ckan.datapusher.callback_url_base", "https://ckan.example.com"
    )
    @pytest.mark.ckan_config(
        "ckan.datapusher.url", "http://datapusher.ckan.org"
    )
    def test_create_resource_hooks(self, app):

        responses.add(
            responses.POST,
            "http://datapusher.ckan.org/job",
            content_type="application/json",
            body=json.dumps({"job_id": "foo", "job_key": "barloco"}),
        )
        responses.add_passthru(config["solr_url"])

        dataset = factories.Dataset()
        call_action(
            "resource_create",
            package_id=dataset['id'],
            format='CSV',
        )

    @responses.activate
    @pytest.mark.ckan_config(
        "ckan.datapusher.callback_url_base", "https://ckan.example.com"
    )
    @pytest.mark.ckan_config(
        "ckan.datapusher.url", "http://datapusher.ckan.org"
    )
    def test_update_resource_url_hooks(self, app):

        responses.add(
            responses.POST,
            "http://datapusher.ckan.org/job",
            content_type="application/json",
            body=json.dumps({"job_id": "foo", "job_key": "barloco"}),
        )
        responses.add_passthru(config["solr_url"])

        dataset = factories.Dataset()
        resource = call_action(
            "resource_create",
            package_id=dataset['id'],
            url='http://example.com/old.csv',
            format='CSV',
        )

        resource = call_action(
            "resource_update",
            id=resource['id'],
            url='http://example.com/new.csv',
            format='CSV',
        )
        assert resource
