# encoding: utf-8

import json
import pytest
from ckan.lib.create_test_data import CreateTestData
import ckan.model as model

import ckan.tests.factories as factories



class TestActionTermTranslation(object):
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db, clean_index):
        CreateTestData.create()
        self.sysadmin_user = model.User.get("testsysadmin")
        self.normal_user = model.User.get("annafan")

    def test_1_update_single(self, app):

        res = app.post(
            "/api/action/term_translation_update",
            json={"term": "moo", "term_translation": "moo", "lang_code": "fr"},
            extra_environ={"Authorization": str(self.sysadmin_user.apikey)},
            status=200,
        )

        assert json.loads(res.body)["success"]

        res = app.post(
            "/api/action/term_translation_update",
            json={
                "term": "moo",
                "term_translation": "moomoo",
                "lang_code": "fr",
            },
            extra_environ={"Authorization": str(self.sysadmin_user.apikey)},
            status=200,
        )

        assert json.loads(res.body)["success"]

        res = app.post(
            "/api/action/term_translation_update",
            json={
                "term": "moo",
                "term_translation": "moomoo",
                "lang_code": "en",
            },
            extra_environ={"Authorization": str(self.sysadmin_user.apikey)},
            status=200,
        )

        assert json.loads(res.body)["success"]

        res = app.post(
            "/api/action/term_translation_show",
            json={"terms": ["moo"]},
            extra_environ={"Authorization": str(self.sysadmin_user.apikey)},
            status=200,
        )

        assert json.loads(res.body)["success"]
        # sort the result since the order is not important and is implementation
        # dependent
        assert sorted(
            json.loads(res.body)["result"], key=dict.items
        ) == sorted(
            [
                {
                    u"lang_code": u"fr",
                    u"term": u"moo",
                    u"term_translation": u"moomoo",
                },
                {
                    u"lang_code": u"en",
                    u"term": u"moo",
                    u"term_translation": u"moomoo",
                },
            ],
            key=dict.items,
        ), json.loads(
            res.body
        )

    def test_2_update_many(self, app):

        data = {
            "data": [
                {
                    "term": "many",
                    "term_translation": "manymoo",
                    "lang_code": "fr",
                },
                {
                    "term": "many",
                    "term_translation": "manymoo",
                    "lang_code": "en",
                },
                {
                    "term": "many",
                    "term_translation": "manymoomoo",
                    "lang_code": "en",
                },
            ]
        }
        res = app.post(
            "/api/action/term_translation_update_many",
            json=data,
            extra_environ={"Authorization": str(self.sysadmin_user.apikey)},
            status=200,
        )

        assert (
            json.loads(res.body)["result"]["success"] == "3 rows updated"
        ), json.loads(res.body)

        res = app.post(
            "/api/action/term_translation_show",
            json={"terms": ["many"]},
            extra_environ={"Authorization": str(self.sysadmin_user.apikey)},
            status=200,
        )

        # sort the result since the order is not important and is implementation
        # dependent
        assert sorted(
            json.loads(res.body)["result"], key=dict.items
        ) == sorted(
            [
                {
                    u"lang_code": u"fr",
                    u"term": u"many",
                    u"term_translation": u"manymoo",
                },
                {
                    u"lang_code": u"en",
                    u"term": u"many",
                    u"term_translation": u"manymoomoo",
                },
            ],
            key=dict.items,
        ), json.loads(
            res.body
        )


class TestBulkActions(object):
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_db, clean_index, app, with_request_context):
        factories.Sysadmin(apikey=u"sysadmin")

        data_dict = "%s=1" % json.dumps({"name": "org"})
        org = factories.Organization(name="org")
        self.org_id = org["id"]

        self.package_ids = [
            factories.Dataset(owner_org=org["id"])["id"] for _ in range(12)
        ]

    def test_01_make_private_then_public(self, app):
        data_dict = {"datasets": self.package_ids, "org_id": self.org_id}
        res = app.post(
            "/api/action/bulk_update_private",
            extra_environ={"Authorization": "sysadmin"},
            json=data_dict,
        )

        dataset_list = [
            row.private
            for row in model.Session.query(model.Package.private).all()
        ]
        assert len(dataset_list) == 12, len(dataset_list)
        assert all(dataset_list)

        res = app.get("/api/action/package_search?q=*:*")
        assert json.loads(res.body)["result"]["count"] == 0

        res = app.post(
            "/api/action/bulk_update_public",
            extra_environ={"Authorization": "sysadmin"},
            json=data_dict,
        )

        dataset_list = [
            row.private
            for row in model.Session.query(model.Package.private).all()
        ]
        assert len(dataset_list) == 12, len(dataset_list)
        assert not any(dataset_list)

        res = app.get("/api/action/package_search?q=*:*")
        assert json.loads(res.body)["result"]["count"] == 12

    def test_02_bulk_delete(self, app):

        res = app.post(
            "/api/action/bulk_update_delete",
            extra_environ={"Authorization": "sysadmin"},
            json={"datasets": self.package_ids, "org_id": self.org_id},
        )

        dataset_list = [
            row.state for row in model.Session.query(model.Package.state).all()
        ]
        assert len(dataset_list) == 12, len(dataset_list)
        assert all(state == "deleted" for state in dataset_list)

        res = app.get("/api/action/package_search?q=*:*")
        assert json.loads(res.body)["result"]["count"] == 0
