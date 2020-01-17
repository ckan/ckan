# encoding: utf-8

import datetime

import json
import pytest
import responses
import sqlalchemy.orm as orm

import ckan.plugins as p
import ckan.tests.legacy as tests
import ckanext.datapusher.interfaces as interfaces
import ckanext.datastore.backend.postgres as db
from ckan.tests import helpers, factories


class FakeDataPusherPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable, inherit=True)
    p.implements(interfaces.IDataPusher, inherit=True)

    def configure(self, _config):
        self.after_upload_calls = 0

    def can_upload(self, resource_id):
        return False

    def after_upload(self, context, resource_dict, package_dict):
        self.after_upload_calls += 1


@pytest.mark.ckan_config(
    "ckan.plugins", "datastore datapusher test_datapusher_plugin"
)
@pytest.mark.usefixtures("with_plugins")
class TestInterace(object):
    sysadmin_user = None
    normal_user = None

    @pytest.fixture(autouse=True)
    def setup_class(self, clean_db, test_request_context):
        if not tests.is_datastore_supported():
            pytest.skip("Datastore not supported")

        resource = factories.Resource(url_type="datastore")
        self.dataset = factories.Dataset(resources=[resource])
        with test_request_context():
            self.sysadmin_user = factories.User(
                name="testsysadmin", sysadmin=True
            )
            self.normal_user = factories.User(name="annafan")
        engine = db.get_write_engine()
        self.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

    @responses.activate
    def test_send_datapusher_creates_task(self, test_request_context):
        responses.add(
            responses.POST,
            "http://datapusher.ckan.org/job",
            content_type="application/json",
            body=json.dumps({"job_id": "foo", "job_key": "bar"}),
        )

        resource = self.dataset["resources"][0]

        context = {"ignore_auth": True, "user": self.sysadmin_user["name"]}
        with test_request_context():
            result = p.toolkit.get_action("datapusher_submit")(
                context, {"resource_id": resource["id"]}
            )
        assert not result

        context.pop("task_status", None)

        with pytest.raises(p.toolkit.ObjectNotFound):
            task = p.toolkit.get_action("task_status_show")(
                context,
                {
                    "entity_id": resource["id"],
                    "task_type": "datapusher",
                    "key": "datapusher",
                },
            )

    def test_after_upload_called(self):
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset["id"])

        # Push data directly to the DataStore for the resource to be marked as
        # `datastore_active=True`, so the grid view can be created
        data = {
            "resource_id": resource["id"],
            "fields": [
                {"id": "a", "type": "text"},
                {"id": "b", "type": "text"},
            ],
            "records": [{"a": "1", "b": "2"}],
            "force": True,
        }
        helpers.call_action("datastore_create", **data)

        # Create a task for `datapusher_hook` to update
        task_dict = {
            "entity_id": resource["id"],
            "entity_type": "resource",
            "task_type": "datapusher",
            "key": "datapusher",
            "value": '{"job_id": "my_id", "job_key":"my_key"}',
            "last_updated": str(datetime.datetime.now()),
            "state": "pending",
        }
        helpers.call_action("task_status_update", context={}, **task_dict)

        # Call datapusher_hook with a status of complete to trigger the
        # default views creation
        params = {
            "status": "complete",
            "metadata": {"resource_id": resource["id"]},
        }
        helpers.call_action("datapusher_hook", context={}, **params)

        total = sum(
            plugin.after_upload_calls
            for plugin in p.PluginImplementations(interfaces.IDataPusher)
        )
        assert total == 1, total

        params = {
            "status": "complete",
            "metadata": {"resource_id": resource["id"]},
        }
        helpers.call_action("datapusher_hook", context={}, **params)

        total = sum(
            plugin.after_upload_calls
            for plugin in p.PluginImplementations(interfaces.IDataPusher)
        )
        assert total == 2, total
