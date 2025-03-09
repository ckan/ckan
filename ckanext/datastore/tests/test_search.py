# encoding: utf-8

import json
import pytest
import sqlalchemy.orm as orm

import ckan.lib.create_test_data as ctd
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as p
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import ckanext.datastore.backend.postgres as db
from ckanext.datastore.tests.helpers import extract


@pytest.mark.usefixtures("with_request_context")
class TestDatastoreSearch(object):
    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_fts_on_field_calculates_ranks_only_on_that_specific_field(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [
                {"from": "Brazil", "to": "Brazil"},
                {"from": "Brazil", "to": "Italy"},
            ],
        }
        result = helpers.call_action("datastore_create", **data)
        search_data = {
            "resource_id": resource["id"],
            "fields": "from, rank from",
            "q": {"from": "Brazil"},
        }
        result = helpers.call_action("datastore_search", **search_data)
        ranks = [r["rank from"] for r in result["records"]]
        assert len(result["records"]) == 2
        assert len(set(ranks)) == 1

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_fts_works_on_non_textual_fields(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [
                {"from": "Brazil", "year": {"foo": 2014}},
                {"from": "Brazil", "year": {"foo": 1986}},
            ],
        }
        result = helpers.call_action("datastore_create", **data)

        search_data = {
            "resource_id": resource["id"],
            "fields": "year",
            "plain": False,
            "q": {"year": "20:*"},
        }
        result = helpers.call_action("datastore_search", **search_data)
        assert len(result["records"]) == 1
        assert result["records"][0]["year"] == {"foo": 2014}

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_all_params_work_with_fields_with_whitespaces(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"the year": 2014}, {"the year": 2013}],
        }
        result = helpers.call_action("datastore_create", **data)
        search_data = {
            "resource_id": resource["id"],
            "fields": "the year",
            "sort": "the year",
            "filters": {"the year": 2013},
            "q": {"the year": "2013"},
        }
        result = helpers.call_action("datastore_search", **search_data)
        result_years = [r["the year"] for r in result["records"]]
        assert result_years == [2013]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_total(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"the year": 2014}, {"the year": 2013}],
        }
        result = helpers.call_action("datastore_create", **data)
        search_data = {"resource_id": resource["id"], "include_total": True}
        result = helpers.call_action("datastore_search", **search_data)
        assert result["total"] == 2
        assert not (result.get("total_was_estimated"))

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_without_total(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"the year": 2014}, {"the year": 2013}],
        }
        result = helpers.call_action("datastore_create", **data)
        search_data = {"resource_id": resource["id"], "include_total": False}
        result = helpers.call_action("datastore_search", **search_data)
        assert "total" not in result
        assert "total_was_estimated" not in result

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_estimate_total(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"the year": 1900 + i} for i in range(100)],
        }
        result = helpers.call_action("datastore_create", **data)
        analyze_sql = """
                    ANALYZE "{resource}";
            """.format(
            resource=resource["id"]
        )
        db.get_write_engine().execute(analyze_sql)
        search_data = {
            "resource_id": resource["id"],
            "total_estimation_threshold": 50,
        }
        result = helpers.call_action("datastore_search", **search_data)
        assert result.get("total_was_estimated")
        assert 95 < result["total"] < 105, result["total"]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_estimate_total_with_filters(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"the year": 1900 + i} for i in range(3)] * 10,
        }
        result = helpers.call_action("datastore_create", **data)
        analyze_sql = """
                    ANALYZE "{resource}";
            """.format(
            resource=resource["id"]
        )
        db.get_write_engine().execute(analyze_sql)
        search_data = {
            "resource_id": resource["id"],
            "filters": {u"the year": 1901},
            "total_estimation_threshold": 5,
        }
        result = helpers.call_action("datastore_search", **search_data)
        assert result["total"] == 10
        # estimation is not compatible with filters
        assert not (result.get("total_was_estimated"))

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_estimate_total_with_distinct(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"the year": 1900 + i} for i in range(3)] * 10,
        }
        result = helpers.call_action("datastore_create", **data)
        analyze_sql = """
                    ANALYZE "{resource}";
            """.format(
            resource=resource["id"]
        )
        db.get_write_engine().execute(analyze_sql)
        search_data = {
            "resource_id": resource["id"],
            "fields": ["the year"],
            "distinct": True,
            "total_estimation_threshold": 1,
        }
        result = helpers.call_action("datastore_search", **search_data)
        assert result["total"] == 3
        # estimation is not compatible with distinct
        assert not (result.get("total_was_estimated"))

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_estimate_total_where_analyze_is_not_already_done(self):
        # ANALYSE is done by latest datapusher/xloader, but need to cope in
        # if tables created in other ways which may not have had an ANALYSE
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"the year": 1900 + i} for i in range(100)],
        }
        result = helpers.call_action("datastore_create", **data)
        search_data = {
            "resource_id": resource["id"],
            "total_estimation_threshold": 50,
        }
        result = helpers.call_action("datastore_search", **search_data)
        assert result.get("total_was_estimated")
        assert 95 < result["total"] < 105, result["total"]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_estimate_total_with_zero_threshold(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"the year": 1900 + i} for i in range(100)],
        }
        result = helpers.call_action("datastore_create", **data)
        analyze_sql = """
                    ANALYZE "{resource}";
            """.format(
            resource=resource["id"]
        )
        db.get_write_engine().execute(analyze_sql)
        search_data = {
            "resource_id": resource["id"],
            "total_estimation_threshold": 0,
        }
        result = helpers.call_action("datastore_search", **search_data)
        # threshold of 0 means always estimate
        assert result.get("total_was_estimated")
        assert 95 < result["total"] < 105, result["total"]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_estimate_total_off(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"the year": 1900 + i} for i in range(100)],
        }
        result = helpers.call_action("datastore_create", **data)
        analyze_sql = """
                    ANALYZE "{resource}";
            """.format(
            resource=resource["id"]
        )
        db.get_write_engine().execute(analyze_sql)
        search_data = {
            "resource_id": resource["id"],
            "total_estimation_threshold": None,
        }
        result = helpers.call_action("datastore_search", **search_data)
        # threshold of None means don't estimate
        assert not (result.get("total_was_estimated"))

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_estimate_total_default_off(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"the year": 1900 + i} for i in range(100)],
        }
        result = helpers.call_action("datastore_create", **data)
        analyze_sql = """
                    ANALYZE "{resource}";
            """.format(
            resource=resource["id"]
        )
        db.get_write_engine().execute(analyze_sql)
        search_data = {
            "resource_id": resource["id"],
            # don't specify total_estimation_threshold
        }
        result = helpers.call_action("datastore_search", **search_data)
        # default threshold is None, meaning don't estimate
        assert not (result.get("total_was_estimated"))

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_limit(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"the year": 2014}, {"the year": 2013}],
        }
        result = helpers.call_action("datastore_create", **data)
        search_data = {"resource_id": resource["id"], "limit": 1}
        result = helpers.call_action("datastore_search", **search_data)
        assert result["total"] == 2
        assert result["records"] == [{u"the year": 2014, u"_id": 1}]
        assert result["limit"] == 1

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_limit_invalid(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"the year": 2014}, {"the year": 2013}],
        }
        helpers.call_action("datastore_create", **data)
        search_data = {"resource_id": resource["id"], "limit": "bad"}
        with pytest.raises(logic.ValidationError, match="Invalid integer"):
            helpers.call_action("datastore_search", **search_data)

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_limit_invalid_negative(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"the year": 2014}, {"the year": 2013}],
        }
        helpers.call_action("datastore_create", **data)
        search_data = {"resource_id": resource["id"], "limit": -1}
        with pytest.raises(
            logic.ValidationError, match="Must be a natural number"
        ):
            helpers.call_action("datastore_search", **search_data)

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    @pytest.mark.ckan_config("ckan.datastore.search.rows_default", "1")
    def test_search_limit_config_default(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"the year": 2014}, {"the year": 2013}],
        }
        result = helpers.call_action("datastore_create", **data)
        search_data = {
            "resource_id": resource["id"],
            # limit not specified - leaving to the configured default of 1
        }
        result = helpers.call_action("datastore_search", **search_data)
        assert result["total"] == 2
        assert result["records"] == [{u"the year": 2014, u"_id": 1}]
        assert result["limit"] == 1

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    @pytest.mark.ckan_config("ckan.datastore.search.rows_default", "1")
    def test_search_limit_config(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [
                {"the year": 2015},
                {"the year": 2014},
                {"the year": 2013},
            ],
        }
        result = helpers.call_action("datastore_create", **data)
        search_data = {
            "resource_id": resource["id"],
            "limit": 2,  # specified limit overrides the rows_default
        }
        result = helpers.call_action("datastore_search", **search_data)
        assert result["total"] == 3
        assert result["records"] == [
            {u"the year": 2015, u"_id": 1},
            {u"the year": 2014, u"_id": 2},
        ]
        assert result["limit"] == 2

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    @pytest.mark.ckan_config("ckan.datastore.search.rows_max", "1")
    def test_search_limit_config_max(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"the year": 2014}, {"the year": 2013}],
        }
        result = helpers.call_action("datastore_create", **data)
        search_data = {
            "resource_id": resource["id"],
            # limit not specified - leaving to the configured default of 1
        }
        result = helpers.call_action("datastore_search", **search_data)
        assert result["total"] == 2
        assert result["records"] == [{u"the year": 2014, u"_id": 1}]
        assert result["limit"] == 1

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    @pytest.mark.ckan_config("ckan.datastore.search.rows_default", "1")
    @pytest.mark.ckan_config("ckan.datastore.search.rows_max", "2")
    def test_search_limit_config_combination(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [
                {"the year": 2016},
                {"the year": 2015},
                {"the year": 2014},
                {"the year": 2013},
            ],
        }
        result = helpers.call_action("datastore_create", **data)
        search_data = {
            "resource_id": resource["id"],
            "limit": 3,  # ignored because it is above rows_max
        }
        result = helpers.call_action("datastore_search", **search_data)
        assert result["total"] == 4
        # returns 2 records,
        # ignoring the rows_default because we specified limit
        # but limit is more than rows_max so rows_max=2 wins
        assert result["records"] == [
            {u"the year": 2016, u"_id": 1},
            {u"the year": 2015, u"_id": 2},
        ]
        assert result["limit"] == 2

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_filter_with_percent_in_column_name(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "primary_key": "id",
            "fields": [
                {"id": "id", "type": "text"},
                {"id": "bo%ok", "type": "text"},
                {"id": "author", "type": "text"},
            ],
            "records": [{"id": "1%", "bo%ok": u"El Nino", "author": "Torres"}],
        }
        helpers.call_action("datastore_create", **data)

        search_data = {
            "resource_id": resource["id"],
            "filters": {u"bo%ok": "El Nino"},
        }
        result = helpers.call_action("datastore_search", **search_data)
        assert result["total"] == 1


@pytest.mark.usefixtures("with_request_context")
class TestDatastoreSearchLegacyTests(object):
    sysadmin_user = None
    normal_user = None

    @pytest.fixture(autouse=True)
    def initial_data(self, clean_datastore, app):
        ctd.CreateTestData.create()
        self.sysadmin_user = factories.Sysadmin()
        self.sysadmin_token = factories.APIToken(user=self.sysadmin_user["id"])
        self.sysadmin_token = self.sysadmin_token["token"]
        self.normal_user = factories.User()
        self.normal_user_token = factories.APIToken(user=self.normal_user["id"])
        self.normal_user_token = self.normal_user_token["token"]
        self.dataset = model.Package.get("annakarenina")
        self.resource = self.dataset.resources[0]
        self.data = {
            "resource_id": self.resource.id,
            "force": True,
            "aliases": "books3",
            "fields": [
                {"id": u"b\xfck", "type": "text"},
                {"id": "author", "type": "text"},
                {"id": "published"},
                {"id": u"characters", u"type": u"_text"},
                {"id": "rating with %"},
            ],
            "records": [
                {
                    u"b\xfck": "annakarenina",
                    "author": "tolstoy",
                    "published": "2005-03-01",
                    "nested": ["b", {"moo": "moo"}],
                    u"characters": [u"Princess Anna", u"Sergius"],
                    "rating with %": "60%",
                },
                {
                    u"b\xfck": "warandpeace",
                    "author": "tolstoy",
                    "nested": {"a": "b"},
                    "rating with %": "99%",
                },
            ],
        }
        auth = {"Authorization": self.sysadmin_token}
        res = app.post(
            "/api/action/datastore_create", json=self.data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True

        # Make an organization, because private datasets must belong to one.
        self.organization = helpers.call_action(
            "organization_create",
            {"user": self.sysadmin_user["name"]},
            name="test_org",
        )

        self.expected_records = [
            {
                u"published": u"2005-03-01T00:00:00",
                u"_id": 1,
                u"nested": [u"b", {u"moo": u"moo"}],
                u"b\xfck": u"annakarenina",
                u"author": u"tolstoy",
                u"characters": [u"Princess Anna", u"Sergius"],
                u"rating with %": u"60%",
            },
            {
                u"published": None,
                u"_id": 2,
                u"nested": {u"a": u"b"},
                u"b\xfck": u"warandpeace",
                u"author": u"tolstoy",
                u"characters": None,
                u"rating with %": u"99%",
            },
        ]

        engine = db.get_write_engine()
        self.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_basic(self, app):
        data = {"resource_id": self.data["resource_id"]}
        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert result["total"] == len(self.data["records"])
        assert result["records"] == self.expected_records, result["records"]

        # search with parameter id should yield the same results
        data = {"id": self.data["resource_id"]}
        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert result["total"] == len(self.data["records"])
        assert result["records"] == self.expected_records, result["records"]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_private_dataset(self, app):
        group = self.dataset.get_groups()[0]
        context = {
            "user": self.sysadmin_user["name"],
            "ignore_auth": True,
            "model": model,
        }
        package = p.toolkit.get_action("package_create")(
            context,
            {
                "name": "privatedataset",
                "private": True,
                "owner_org": self.organization["id"],
                "groups": [{"id": group.id}],
            },
        )
        resource = p.toolkit.get_action("resource_create")(
            context,
            {
                "name": "privateresource",
                "url": "https://www.example.com/",
                "package_id": package["id"],
            },
        )
        helpers.call_action("datastore_create", resource_id=resource["id"], force=True)
        data = {"resource_id": resource["id"]}
        auth = {"Authorization": self.normal_user_token}

        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is False

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_alias(self, app):
        data = {"resource_id": self.data["aliases"]}
        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict_alias = json.loads(res.data)
        result = res_dict_alias["result"]
        assert result["total"] == len(self.data["records"])
        assert result["records"] == self.expected_records, result["records"]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_invalid_field(self, app):
        data = {
            "resource_id": self.data["resource_id"],
            "fields": [{"id": "bad"}],
        }
        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search",
            json=data,
            extra_environ=auth,
            status=409,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is False

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_fields(self, app):
        data = {"resource_id": self.data["resource_id"], "fields": [u"b\xfck"]}
        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert result["total"] == len(self.data["records"])
        assert result["records"] == [
            {u"b\xfck": "annakarenina"},
            {u"b\xfck": "warandpeace"},
        ], result["records"]

        data = {
            "resource_id": self.data["resource_id"],
            "fields": u"b\xfck, author",
        }
        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert result["total"] == len(self.data["records"])
        assert result["records"] == [
            {u"b\xfck": "annakarenina", "author": "tolstoy"},
            {u"b\xfck": "warandpeace", "author": "tolstoy"},
        ], result["records"]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_distinct(self, app):
        data = {
            "resource_id": self.data["resource_id"],
            "fields": [u"author"],
            "distinct": True,
        }

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert result["total"] == 1
        assert result["records"] == [{u"author": "tolstoy"}], result["records"]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_filters(self, app):
        data = {
            "resource_id": self.data["resource_id"],
            "filters": {u"b\xfck": "annakarenina"},
        }

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert result["total"] == 1
        assert result["records"] == [self.expected_records[0]]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_filter_array_field(self, app):
        data = {
            "resource_id": self.data["resource_id"],
            "filters": {u"characters": [u"Princess Anna", u"Sergius"]},
        }

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert result["total"] == 1
        assert result["records"] == [self.expected_records[0]]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_multiple_filters_on_same_field(self, app):
        data = {
            "resource_id": self.data["resource_id"],
            "filters": {u"b\xfck": [u"annakarenina", u"warandpeace"]},
        }

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert result["total"] == 2
        assert result["records"] == self.expected_records

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_filter_normal_field_passing_multiple_values_in_array(
        self, app
    ):
        data = {
            "resource_id": self.data["resource_id"],
            "filters": {u"b\xfck": [u"annakarenina", u"warandpeace"]},
        }

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert result["total"] == 2
        assert result["records"] == self.expected_records, result["records"]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_filters_get(self, app):
        filters = {u"b\xfck": "annakarenina"}
        res = app.get(
            "/api/action/datastore_search?resource_id={0}&filters={1}".format(
                self.data["resource_id"], json.dumps(filters)
            )
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert result["total"] == 1
        assert result["records"] == [self.expected_records[0]]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_invalid_filter(self, app):
        data = {
            "resource_id": self.data["resource_id"],
            # invalid because author is not a numeric field
            "filters": {u"author": 42},
        }

        auth = {"Authorization": self.sysadmin_token}
        res = app.post(
            "/api/action/datastore_search",
            json=data,
            extra_environ=auth,
            status=409,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is False

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_sort(self, app):
        data = {
            "resource_id": self.data["resource_id"],
            "sort": u"b\xfck asc, author desc",
        }
        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert result["total"] == 2

        assert result["records"] == self.expected_records, result["records"]

        data = {
            "resource_id": self.data["resource_id"],
            "sort": [u"b\xfck desc", '"author" asc'],
        }
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert result["total"] == 2

        assert result["records"] == self.expected_records[::-1]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_invalid(self, app):
        data = {
            "resource_id": self.data["resource_id"],
            "sort": u"f\xfc\xfc asc",
        }
        auth = {"Authorization": self.sysadmin_token}
        res = app.post(
            "/api/action/datastore_search",
            json=data,
            extra_environ=auth,
            status=409,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is False
        error_msg = res_dict["error"]["sort"][0]
        assert (
            u"f\xfc\xfc" in error_msg
        ), 'Expected "{0}" to contain "{1}"'.format(error_msg, u"f\xfc\xfc")

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_offset(self, app):
        data = {
            "resource_id": self.data["resource_id"],
            "limit": 1,
            "offset": 1,
        }

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert result["total"] == 2
        assert result["records"] == [self.expected_records[1]]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_invalid_offset(self, app):
        data = {"resource_id": self.data["resource_id"], "offset": "bad"}

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search",
            json=data,
            extra_environ=auth,
            status=409,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is False

        data = {"resource_id": self.data["resource_id"], "offset": -1}

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search",
            json=data,
            extra_environ=auth,
            status=409,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is False

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_full_text(self, app):
        data = {"resource_id": self.data["resource_id"], "q": "annakarenina"}

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert result["total"] == 1

        results = [
            extract(
                result["records"][0],
                [
                    u"_id",
                    u"author",
                    u"b\xfck",
                    u"nested",
                    u"published",
                    u"characters",
                    u"rating with %",
                ],
            )
        ]
        assert results == [self.expected_records[0]], results["records"]

        data = {"resource_id": self.data["resource_id"], "q": "tolstoy"}

        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert result["total"] == 2
        results = [
            extract(
                record,
                [
                    u"_id",
                    u"author",
                    u"b\xfck",
                    u"nested",
                    u"published",
                    u"characters",
                    u"rating with %",
                ],
            )
            for record in result["records"]
        ]
        assert results == self.expected_records, result["records"]

        expected_fields = [
            {u"type": u"int", u"id": u"_id"},
            {u"type": u"text", u"id": u"b\xfck"},
            {u"type": u"text", u"id": u"author"},
            {u"type": u"timestamp", u"id": u"published"},
            {u"type": u"json", u"id": u"nested"},
        ]
        for field in expected_fields:
            assert field in result["fields"]

        # test multiple word queries (connected with and)
        data = {
            "resource_id": self.data["resource_id"],
            "plain": True,
            "q": "tolstoy annakarenina",
        }

        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert result["total"] == 1
        results = [
            extract(
                result["records"][0],
                [
                    u"_id",
                    u"author",
                    u"b\xfck",
                    u"nested",
                    u"published",
                    u"characters",
                    u"rating with %",
                ],
            )
        ]
        assert results == [self.expected_records[0]], results["records"]

        for field in expected_fields:
            assert field in result["fields"], field

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_full_text_on_specific_column(self, app):
        data = {
            "resource_id": self.data["resource_id"],
            "q": {u"b\xfck": "annakarenina"},
        }

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        assert len(res_dict["result"]["records"]) == 1
        assert (
            res_dict["result"]["records"][0]["_id"]
            == self.expected_records[0]["_id"]
        )

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_full_text_on_specific_column_even_if_q_is_a_json_string(
        self, app
    ):
        data = {
            "resource_id": self.data["resource_id"],
            "q": u'{"b\xfck": "annakarenina"}',
        }

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        assert len(res_dict["result"]["records"]) == 1
        assert (
            res_dict["result"]["records"][0]["_id"]
            == self.expected_records[0]["_id"]
        )

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_full_text_invalid_field_name(self, app):
        data = {
            "resource_id": self.data["resource_id"],
            "q": {"invalid_field_name": "value"},
        }

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search",
            json=data,
            extra_environ=auth,
            status=409,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is False

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_full_text_invalid_field_value(self, app):
        data = {
            "resource_id": self.data["resource_id"],
            "q": {"author": ["invalid", "value"]},
        }

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search",
            json=data,
            extra_environ=auth,
            status=409,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is False

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_table_metadata(self, app):
        data = {"resource_id": "_table_metadata"}

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_is_unsuccessful_when_called_with_filters_not_as_dict(
        self, app
    ):
        data = {
            "resource_id": self.data["resource_id"],
            "filters": "the-filter",
        }

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search",
            json=data,
            extra_environ=auth,
            status=409,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is False
        assert res_dict["error"].get("filters") is not None, res_dict["error"]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_is_unsuccessful_when_called_with_invalid_filters(
        self, app
    ):
        data = {
            "resource_id": self.data["resource_id"],
            "filters": {"invalid-column-name": "value"},
        }

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search",
            json=data,
            extra_environ=auth,
            status=409,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is False
        assert res_dict["error"].get("filters") is not None, res_dict["error"]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_is_unsuccessful_when_called_with_invalid_fields(self, app):
        data = {
            "resource_id": self.data["resource_id"],
            "fields": ["invalid-column-name"],
        }

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search",
            json=data,
            extra_environ=auth,
            status=409,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is False
        assert res_dict["error"].get("fields") is not None, res_dict["error"]


class TestDatastoreFullTextSearchLegacyTests(object):
    @pytest.fixture(autouse=True)
    def initial_data(self, clean_datastore, app):
        ctd.CreateTestData.create()
        self.sysadmin_user = factories.Sysadmin()
        self.sysadmin_token = factories.APIToken(user=self.sysadmin_user["id"])
        self.sysadmin_token = self.sysadmin_token["token"]
        self.normal_user = factories.User()
        self.normal_user_token = factories.APIToken(user=self.normal_user["id"])
        self.normal_user_token = self.normal_user_token["token"]
        resource = model.Package.get("annakarenina").resources[0]
        self.data = dict(
            resource_id=resource.id,
            force=True,
            fields=[
                {"id": "id"},
                {"id": "date", "type": "date"},
                {"id": "x"},
                {"id": "y"},
                {"id": "z"},
                {"id": "country"},
                {"id": "title"},
                {"id": "lat"},
                {"id": "lon"},
            ],
            records=[
                {
                    "id": 0,
                    "date": "2011-01-01",
                    "x": 1,
                    "y": 2,
                    "z": 3,
                    "country": "DE",
                    "title": "first 99",
                    "lat": 52.56,
                    "lon": 13.40,
                },
                {
                    "id": 1,
                    "date": "2011-02-02",
                    "x": 2,
                    "y": 4,
                    "z": 24,
                    "country": "UK",
                    "title": "second",
                    "lat": 54.97,
                    "lon": -1.60,
                },
                {
                    "id": 2,
                    "date": "2011-03-03",
                    "x": 3,
                    "y": 6,
                    "z": 9,
                    "country": "US",
                    "title": "third",
                    "lat": 40.00,
                    "lon": -75.5,
                },
                {
                    "id": 3,
                    "date": "2011-04-04",
                    "x": 4,
                    "y": 8,
                    "z": 6,
                    "country": "UK",
                    "title": "fourth",
                    "lat": 57.27,
                    "lon": -6.20,
                },
                {
                    "id": 4,
                    "date": "2011-05-04",
                    "x": 5,
                    "y": 10,
                    "z": 15,
                    "country": "UK",
                    "title": "fifth",
                    "lat": 51.58,
                    "lon": 0,
                },
                {
                    "id": 5,
                    "date": "2011-06-02",
                    "x": 6,
                    "y": 12,
                    "z": 18,
                    "country": "DE",
                    "title": "sixth 53.56",
                    "lat": 51.04,
                    "lon": 7.9,
                },
            ],
        )
        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_create", json=self.data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_search_full_text(self, app):
        data = {"resource_id": self.data["resource_id"], "q": "DE"}

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["result"]["total"] == 2

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_advanced_search_full_text(self, app):
        data = {
            "resource_id": self.data["resource_id"],
            "plain": "False",
            "q": "DE | UK",
        }

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["result"]["total"] == 5

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_full_text_search_on_integers_within_text_strings(self, app):
        data = {"resource_id": self.data["resource_id"], "q": "99"}

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["result"]["total"] == 1

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_full_text_search_on_integers(self, app):
        data = {"resource_id": self.data["resource_id"], "q": "4"}

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["result"]["total"] == 3

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_full_text_search_on_decimal_within_text_strings(self, app):
        data = {"resource_id": self.data["resource_id"], "q": "53.56"}

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["result"]["total"] == 1

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_full_text_search_on_decimal(self, app):
        data = {"resource_id": self.data["resource_id"], "q": "52.56"}

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["result"]["total"] == 1

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_full_text_search_on_date(self, app):
        data = {"resource_id": self.data["resource_id"], "q": "2011-01-01"}

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["result"]["total"] == 1

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_full_text_search_on_json_like_string_succeeds(self, app):
        data = {"resource_id": self.data["resource_id"], "q": '"{}"'}

        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"]


class TestDatastoreSQLLegacyTests(object):
    sysadmin_user = None
    normal_user = None

    @pytest.fixture(autouse=True)
    def initial_data(self, clean_datastore, app):
        ctd.CreateTestData.create()
        self.sysadmin_user = factories.Sysadmin()
        self.sysadmin_token = factories.APIToken(user=self.sysadmin_user["id"])
        self.sysadmin_token = self.sysadmin_token["token"]
        self.normal_user = factories.User()
        self.normal_user_token = factories.APIToken(user=self.normal_user["id"])
        self.normal_user_token = self.normal_user_token["token"]
        self.dataset = model.Package.get("annakarenina")
        resource = self.dataset.resources[0]
        self.data = {
            "resource_id": resource.id,
            "force": True,
            "aliases": "books4",
            "fields": [
                {"id": u"b\xfck", "type": "text"},
                {"id": "author", "type": "text"},
                {"id": "published"},
            ],
            "records": [
                {
                    u"b\xfck": "annakarenina",
                    "author": "tolstoy",
                    "published": "2005-03-01",
                    "nested": ["b", {"moo": "moo"}],
                },
                {
                    u"b\xfck": "warandpeace",
                    "author": "tolstoy",
                    "nested": {"a": "b"},
                },
            ],
        }
        auth = {"Authorization": self.sysadmin_token}
        res = app.post(
            "/api/action/datastore_create", json=self.data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True

        # Make an organization, because private datasets must belong to one.
        self.organization = helpers.call_action(
            "organization_create",
            {"user": self.sysadmin_user["name"]},
            name="test_org",
        )

        self.expected_records = [
            {
                u"_full_text": [
                    u"'annakarenina'",
                    u"'b'",
                    u"'moo'",
                    u"'tolstoy'",
                    u"'2005'",
                ],
                u"_id": 1,
                u"author": u"tolstoy",
                u"b\xfck": u"annakarenina",
                u"nested": [u"b", {u"moo": u"moo"}],
                u"published": u"2005-03-01T00:00:00",
            },
            {
                u"_full_text": [u"'tolstoy'", u"'warandpeac'", u"'b'"],
                u"_id": 2,
                u"author": u"tolstoy",
                u"b\xfck": u"warandpeace",
                u"nested": {u"a": u"b"},
                u"published": None,
            },
        ]
        self.expected_join_results = [
            {u"first": 1, u"second": 1},
            {u"first": 1, u"second": 2},
        ]

        engine = db.get_write_engine()
        self.Session = orm.scoped_session(orm.sessionmaker(bind=engine))

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_select_where_like_with_percent(self, app):
        query = 'SELECT * FROM public."{0}" WHERE "author" LIKE \'tol%\''.format(
            self.data["resource_id"]
        )
        data = {"sql": query}
        auth = {"Authorization": self.sysadmin_token}
        res = app.post(
            "/api/action/datastore_search_sql", json=data, extra_environ=auth,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert len(result["records"]) == len(self.expected_records)
        for (row_index, row) in enumerate(result["records"]):
            expected_row = self.expected_records[row_index]
            assert set(row.keys()) == set(expected_row.keys())
            for field in row:
                if field == "_full_text":
                    for ft_value in expected_row["_full_text"]:
                        assert ft_value in row["_full_text"]
                else:
                    assert row[field] == expected_row[field]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_self_join(self, app):
        query = """
            select a._id as first, b._id as second
            from "{0}" AS a,
                 "{0}" AS b
            where a.author = b.author
            limit 2
            """.format(
            self.data["resource_id"]
        )
        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search_sql",
            json={"sql": query},
            extra_environ=auth,
        )

        res_dict = json.loads(res.data)
        assert res_dict["success"] is True
        result = res_dict["result"]
        assert result["records"] == self.expected_join_results

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures(
        "clean_datastore", "with_plugins", "with_request_context"
    )
    def test_new_datastore_table_from_private_resource(self, app):
        # make a private CKAN resource
        group = self.dataset.get_groups()[0]
        context = {
            "user": self.sysadmin_user["name"],
            "ignore_auth": True,
            "model": model,
        }
        package = p.toolkit.get_action("package_create")(
            context,
            {
                "name": "privatedataset",
                "private": True,
                "owner_org": self.organization["id"],
                "groups": [{"id": group.id}],
            },
        )
        resource = p.toolkit.get_action("resource_create")(
            context,
            {
                "name": "privateresource",
                "url": "https://www.example.com/",
                "package_id": package["id"],
            },
        )

        auth = {"Authorization": self.sysadmin_token}
        helpers.call_action(
            "datastore_create", resource_id=resource["id"], force=True
        )

        # new resource should be private
        query = 'SELECT * FROM "{0}"'.format(resource["id"])
        data = {"sql": query}
        auth = {"Authorization": self.normal_user_token}
        res = app.post(
            "/api/action/datastore_search_sql",
            json=data,
            extra_environ=auth,
            status=403,
        )
        res_dict = json.loads(res.data)
        assert res_dict["success"] is False
        assert res_dict["error"]["__type"] == "Authorization Error"

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_not_authorized_to_access_system_tables(self, app):
        test_cases = [
            "SELECT * FROM pg_roles",
            "SELECT * FROM pg_catalog.pg_database",
            "SELECT rolpassword FROM pg_roles",
            """SELECT p.rolpassword
               FROM pg_roles p
               JOIN "{0}" r
               ON p.rolpassword = r.author""".format(
                self.data["resource_id"]
            ),
        ]
        for query in test_cases:
            data = {"sql": query.replace("\n", "")}
            res = app.post(
                "/api/action/datastore_search_sql", json=data, status=403,
            )
            res_dict = json.loads(res.data)
            assert res_dict["success"] is False
            assert res_dict["error"]["__type"] == "Authorization Error"


class TestDatastoreSQLFunctional(object):
    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures(
        "clean_datastore", "with_plugins", "with_request_context"
    )
    def test_search_sql_enforces_private(self):
        user1 = factories.User()
        user2 = factories.User()
        user3 = factories.User()
        ctx1 = {u"user": user1["name"], u"ignore_auth": False}
        ctx2 = {u"user": user2["name"], u"ignore_auth": False}
        ctx3 = {u"user": user3["name"], u"ignore_auth": False}

        org1 = factories.Organization(
            user=user1,
            users=[{u"name": user3["name"], u"capacity": u"member"}],
        )
        org2 = factories.Organization(
            user=user2,
            users=[{u"name": user3["name"], u"capacity": u"member"}],
        )
        ds1 = factories.Dataset(owner_org=org1["id"], private=True)
        ds2 = factories.Dataset(owner_org=org2["id"], private=True)
        r1 = helpers.call_action(
            u"datastore_create",
            resource={u"package_id": ds1["id"]},
            fields=[{u"id": u"spam", u"type": u"text"}],
        )
        r2 = helpers.call_action(
            u"datastore_create",
            resource={u"package_id": ds2["id"]},
            fields=[{u"id": u"ham", u"type": u"text"}],
        )

        sql1 = 'SELECT spam FROM "{0}"'.format(r1["resource_id"])
        sql2 = 'SELECT ham FROM "{0}"'.format(r2["resource_id"])
        sql3 = 'SELECT spam, ham FROM "{0}", "{1}"'.format(
            r1["resource_id"], r2["resource_id"]
        )

        with pytest.raises(p.toolkit.NotAuthorized):
            helpers.call_action("datastore_search_sql", context=ctx2, sql=sql1)
        with pytest.raises(p.toolkit.NotAuthorized):
            helpers.call_action("datastore_search_sql", context=ctx1, sql=sql2)
        with pytest.raises(p.toolkit.NotAuthorized):
            helpers.call_action("datastore_search_sql", context=ctx1, sql=sql3)
        with pytest.raises(p.toolkit.NotAuthorized):
            helpers.call_action("datastore_search_sql", context=ctx2, sql=sql3)
        helpers.call_action("datastore_search_sql", context=ctx1, sql=sql1)
        helpers.call_action("datastore_search_sql", context=ctx2, sql=sql2)
        helpers.call_action("datastore_search_sql", context=ctx3, sql=sql3)

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_validates_sql_has_a_single_statement(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"the year": 2014}, {"the year": 2013}],
        }
        helpers.call_action("datastore_create", **data)
        sql = 'SELECT * FROM public."{0}"; SELECT * FROM public."{0}";'.format(
            resource["id"]
        )
        with pytest.raises(
            p.toolkit.ValidationError, match="Query is not a single statement"
        ):
            helpers.call_action("datastore_search_sql", sql=sql)

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_works_with_semicolons_inside_strings(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"author": "bob"}, {"author": "jane"}],
        }
        helpers.call_action("datastore_create", **data)
        sql = 'SELECT * FROM public."{0}" WHERE "author" = \'foo; bar\''.format(
            resource["id"]
        )
        helpers.call_action("datastore_search_sql", sql=sql)

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_works_with_allowed_functions(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"author": "bob"}, {"author": "jane"}],
        }
        helpers.call_action("datastore_create", **data)

        sql = 'SELECT upper(author) from "{}"'.format(
            resource["id"]
        )
        helpers.call_action("datastore_search_sql", sql=sql)

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_not_authorized_with_disallowed_functions(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"author": "bob"}, {"author": "jane"}],
        }
        helpers.call_action("datastore_create", **data)

        sql = "SELECT query_to_xml('SELECT upper(author) from \"{}\"', true, true, '')".format(
            resource["id"]
        )
        with pytest.raises(p.toolkit.NotAuthorized):
            helpers.call_action("datastore_search_sql", sql=sql)

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_allowed_functions_are_case_insensitive(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"author": "bob"}, {"author": "jane"}],
        }
        helpers.call_action("datastore_create", **data)

        sql = 'SELECT UpPeR(author) from "{}"'.format(
            resource["id"]
        )
        helpers.call_action("datastore_search_sql", sql=sql)

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_quoted_allowed_functions_are_case_sensitive(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [{"author": "bob"}, {"author": "jane"}],
        }
        helpers.call_action("datastore_create", **data)

        sql = 'SELECT count(*) from "{}"'.format(
            resource["id"]
        )
        helpers.call_action("datastore_search_sql", sql=sql)

        sql = 'SELECT CoUnT(*) from "{}"'.format(
            resource["id"]
        )
        with pytest.raises(p.toolkit.NotAuthorized):
            helpers.call_action("datastore_search_sql", sql=sql)

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_invalid_statement(self):
        sql = "SELECT ** FROM foobar"
        with pytest.raises(
            logic.ValidationError, match='syntax error at or near "FROM"'
        ):
            helpers.call_action("datastore_search_sql", sql=sql)

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_select_basic(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [
                {
                    u"b\xfck": "annakarenina",
                    "author": "tolstoy",
                    "published": "2005-03-01",
                    "nested": ["b", {"moo": "moo"}],
                },
                {
                    u"b\xfck": "warandpeace",
                    "author": "tolstoy",
                    "nested": {"a": "b"},
                },
            ],
        }
        expected_records = [
            {
                u"_full_text": [
                    u"'annakarenina'",
                    u"'b'",
                    u"'moo'",
                    u"'tolstoy'",
                    u"'2005'",
                ],
                u"_id": 1,
                u"author": u"tolstoy",
                u"b\xfck": u"annakarenina",
                u"nested": [u"b", {u"moo": u"moo"}],
                u"published": u"2005-03-01T00:00:00",
            },
            {
                u"_full_text": [u"'tolstoy'", u"'warandpeac'", u"'b'"],
                u"_id": 2,
                u"author": u"tolstoy",
                u"b\xfck": u"warandpeace",
                u"nested": {u"a": u"b"},
                u"published": None,
            },
        ]
        helpers.call_action("datastore_create", **data)
        sql = 'SELECT * FROM "{0}"'.format(resource["id"])
        result = helpers.call_action("datastore_search_sql", sql=sql)
        assert len(result["records"]) == 2
        for (row_index, row) in enumerate(result["records"]):
            expected_row = expected_records[row_index]
            assert set(row.keys()) == set(expected_row.keys())
            for field in row:
                if field == "_full_text":
                    for ft_value in expected_row["_full_text"]:
                        assert ft_value in row["_full_text"]
                else:
                    assert row[field] == expected_row[field]
        assert u"records_truncated" not in result

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_alias_search(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "aliases": "books4",
            "records": [
                {
                    u"b\xfck": "annakarenina",
                    "author": "tolstoy",
                    "published": "2005-03-01",
                    "nested": ["b", {"moo": "moo"}],
                },
                {
                    u"b\xfck": "warandpeace",
                    "author": "tolstoy",
                    "nested": {"a": "b"},
                },
            ],
        }
        helpers.call_action("datastore_create", **data)
        sql = 'SELECT * FROM "{0}"'.format(resource["id"])
        result = helpers.call_action("datastore_search_sql", sql=sql)
        sql = 'SELECT * FROM "books4"'
        result_with_alias = helpers.call_action(
            "datastore_search_sql", sql=sql
        )
        assert result["records"] == result_with_alias["records"]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    @pytest.mark.ckan_config("ckan.datastore.search.rows_max", "2")
    def test_search_limit(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [
                {"the year": 2014},
                {"the year": 2013},
                {"the year": 2015},
                {"the year": 2016},
            ],
        }
        result = helpers.call_action("datastore_create", **data)
        sql = 'SELECT * FROM "{0}"'.format(resource["id"])
        result = helpers.call_action("datastore_search_sql", sql=sql)
        assert len(result["records"]) == 2
        assert [res[u"the year"] for res in result["records"]] == [2014, 2013]
        assert result[u"records_truncated"]


@pytest.mark.usefixtures("with_request_context")
class TestDatastoreSearchRecordsFormat(object):
    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_sort_results_objects(self):
        ds = factories.Dataset()
        r = helpers.call_action(
            u"datastore_create",
            resource={u"package_id": ds["id"]},
            fields=[
                {u"id": u"num", u"type": u"numeric"},
                {u"id": u"dt", u"type": u"timestamp"},
                {u"id": u"txt", u"type": u"text"},
            ],
            records=[
                {u"num": 10, u"dt": u"2020-01-01", u"txt": "aaab"},
                {u"num": 9, u"dt": u"2020-01-02", u"txt": "aaab"},
                {u"num": 9, u"dt": u"2020-01-01", u"txt": "aaac"},
            ],
        )
        assert helpers.call_action(
            "datastore_search", resource_id=r["resource_id"], sort=u"num, dt"
        )["records"] == [
            {
                u"_id": 3,
                u"num": 9,
                u"dt": u"2020-01-01T00:00:00",
                u"txt": u"aaac",
            },
            {
                u"_id": 2,
                u"num": 9,
                u"dt": u"2020-01-02T00:00:00",
                u"txt": u"aaab",
            },
            {
                u"_id": 1,
                u"num": 10,
                u"dt": u"2020-01-01T00:00:00",
                u"txt": u"aaab",
            },
        ]
        assert helpers.call_action(
            "datastore_search", resource_id=r["resource_id"], sort=u"dt, txt"
        )["records"] == [
            {
                u"_id": 1,
                u"num": 10,
                u"dt": u"2020-01-01T00:00:00",
                u"txt": u"aaab",
            },
            {
                u"_id": 3,
                u"num": 9,
                u"dt": u"2020-01-01T00:00:00",
                u"txt": u"aaac",
            },
            {
                u"_id": 2,
                u"num": 9,
                u"dt": u"2020-01-02T00:00:00",
                u"txt": u"aaab",
            },
        ]
        assert helpers.call_action(
            "datastore_search", resource_id=r["resource_id"], sort=u"txt, num"
        )["records"] == [
            {
                u"_id": 2,
                u"num": 9,
                u"dt": u"2020-01-02T00:00:00",
                u"txt": u"aaab",
            },
            {
                u"_id": 1,
                u"num": 10,
                u"dt": u"2020-01-01T00:00:00",
                u"txt": u"aaab",
            },
            {
                u"_id": 3,
                u"num": 9,
                u"dt": u"2020-01-01T00:00:00",
                u"txt": u"aaac",
            },
        ]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_sort_results_lists(self):
        ds = factories.Dataset()
        r = helpers.call_action(
            u"datastore_create",
            resource={u"package_id": ds["id"]},
            fields=[
                {u"id": u"num", u"type": u"numeric"},
                {u"id": u"dt", u"type": u"timestamp"},
                {u"id": u"txt", u"type": u"text"},
            ],
            records=[
                {u"num": 10, u"dt": u"2020-01-01", u"txt": u"aaab"},
                {u"num": 9, u"dt": u"2020-01-02", u"txt": u"aaab"},
                {u"num": 9, u"dt": u"2020-01-01", u"txt": u"aaac"},
            ],
        )
        assert helpers.call_action(
            "datastore_search",
            resource_id=r["resource_id"],
            records_format=u"lists",
            sort=u"num, dt",
        )["records"] == [
            [3, 9, u"2020-01-01T00:00:00", u"aaac"],
            [2, 9, u"2020-01-02T00:00:00", u"aaab"],
            [1, 10, u"2020-01-01T00:00:00", u"aaab"],
        ]
        assert helpers.call_action(
            "datastore_search",
            resource_id=r["resource_id"],
            records_format=u"lists",
            sort=u"dt, txt",
        )["records"] == [
            [1, 10, u"2020-01-01T00:00:00", u"aaab"],
            [3, 9, u"2020-01-01T00:00:00", u"aaac"],
            [2, 9, u"2020-01-02T00:00:00", u"aaab"],
        ]
        assert helpers.call_action(
            "datastore_search",
            resource_id=r["resource_id"],
            records_format=u"lists",
            sort=u"txt, num",
        )["records"] == [
            [2, 9, u"2020-01-02T00:00:00", u"aaab"],
            [1, 10, u"2020-01-01T00:00:00", u"aaab"],
            [3, 9, u"2020-01-01T00:00:00", u"aaac"],
        ]

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_sort_results_csv(self):
        ds = factories.Dataset()
        r = helpers.call_action(
            u"datastore_create",
            resource={u"package_id": ds["id"]},
            fields=[
                {u"id": u"num", u"type": u"numeric"},
                {u"id": u"dt", u"type": u"timestamp"},
                {u"id": u"txt", u"type": u"text"},
            ],
            records=[
                {u"num": 10, u"dt": u"2020-01-01", u"txt": u"aaab"},
                {u"num": 9, u"dt": u"2020-01-02", u"txt": u"aaab"},
                {u"num": 9, u"dt": u"2020-01-01", u"txt": u"aaac"},
            ],
        )
        assert (
            helpers.call_action(
                "datastore_search",
                resource_id=r["resource_id"],
                records_format=u"csv",
                sort=u"num, dt",
            )["records"]
            == u"3,9,2020-01-01T00:00:00,aaac\n"
            u"2,9,2020-01-02T00:00:00,aaab\n"
            u"1,10,2020-01-01T00:00:00,aaab\n"
        )
        assert (
            helpers.call_action(
                "datastore_search",
                resource_id=r["resource_id"],
                records_format=u"csv",
                sort=u"dt, txt",
            )["records"]
            == u"1,10,2020-01-01T00:00:00,aaab\n"
            u"3,9,2020-01-01T00:00:00,aaac\n"
            u"2,9,2020-01-02T00:00:00,aaab\n"
        )
        assert (
            helpers.call_action(
                "datastore_search",
                resource_id=r["resource_id"],
                records_format=u"csv",
                sort=u"txt, num",
            )["records"]
            == u"2,9,2020-01-02T00:00:00,aaab\n"
            u"1,10,2020-01-01T00:00:00,aaab\n"
            u"3,9,2020-01-01T00:00:00,aaac\n"
        )

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_fields_results_csv(self):
        ds = factories.Dataset()
        r = helpers.call_action(
            u"datastore_create",
            resource={u"package_id": ds["id"]},
            fields=[
                {u"id": u"num", u"type": u"numeric"},
                {u"id": u"dt", u"type": u"timestamp"},
                {u"id": u"txt", u"type": u"text"},
            ],
            records=[
                {u"num": 9, u"dt": u"2020-01-02", u"txt": u"aaab"},
                {u"num": 9, u"dt": u"2020-01-01", u"txt": u"aaac"},
            ],
        )
        r = helpers.call_action(
            "datastore_search",
            resource_id=r["resource_id"],
            records_format=u"csv",
            fields=u"dt, num, txt",
        )
        assert r["fields"] == [
            {u"id": u"dt", u"type": u"timestamp"},
            {u"id": u"num", u"type": u"numeric"},
            {u"id": u"txt", u"type": u"text"},
        ]
        assert (
            r["records"] == u"2020-01-02T00:00:00,9,aaab\n"
            u"2020-01-01T00:00:00,9,aaac\n"
        )
        r = helpers.call_action(
            "datastore_search",
            resource_id=r["resource_id"],
            records_format=u"csv",
            fields=u"dt",
            q=u"aaac",
        )
        assert r["fields"] == [{u"id": u"dt", u"type": u"timestamp"}]
        assert r["records"] == u"2020-01-01T00:00:00\n"
        r = helpers.call_action(
            "datastore_search",
            resource_id=r["resource_id"],
            records_format=u"csv",
            fields=u"txt, rank txt",
            q={u"txt": u"aaac"},
        )
        assert r["fields"] == [
            {u"id": u"txt", u"type": u"text"},
            {u"id": u"rank txt", u"type": u"float"},
        ]
        assert r["records"][:7] == u"aaac,0."

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_fts_on_field_calculates_ranks_specific_field_and_all_fields(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [
                {"from": "Brazil", "to": "Brazil"},
                {"from": "Brazil", "to": "Italy"},
            ],
        }
        result = helpers.call_action("datastore_create", **data)
        search_data = {
            "resource_id": resource["id"],
            "fields": "from, rank from",
            "full_text": "Brazil",
            "q": {"from": "Brazil"},
        }
        result = helpers.call_action("datastore_search", **search_data)
        ranks_from = [r["rank from"] for r in result["records"]]
        assert len(result["records"]) == 2
        assert len(set(ranks_from)) == 1

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_fts_on_field_calculates_ranks_when_q_string_and_fulltext_is_given(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [
                {"from": "Brazil", "to": "Brazil"},
                {"from": "Brazil", "to": "Italy"},
            ],
        }
        result = helpers.call_action("datastore_create", **data)
        search_data = {
            "resource_id": resource["id"],
            "full_text": "Brazil",
            "q": "Brazil",
        }
        result = helpers.call_action("datastore_search", **search_data)
        ranks = [r["rank"] for r in result["records"]]
        assert len(result["records"]) == 2
        assert len(set(ranks)) == 2

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_fts_on_field_calculates_ranks_when_full_text_is_given(self):
        resource = factories.Resource()
        data = {
            "resource_id": resource["id"],
            "force": True,
            "records": [
                {"from": "Brazil", "to": "Brazil"},
                {"from": "Brazil", "to": "Italy"},
            ],
        }
        result = helpers.call_action("datastore_create", **data)
        search_data = {
            "resource_id": resource["id"],
            "full_text": "Brazil",
        }
        result = helpers.call_action("datastore_search", **search_data)
        ranks = [r["rank"] for r in result["records"]]
        assert len(result["records"]) == 2
        assert len(set(ranks)) == 2

    @pytest.mark.ckan_config("ckan.plugins", "datastore")
    @pytest.mark.usefixtures("clean_datastore", "with_plugins")
    def test_results_with_nulls(self):
        ds = factories.Dataset()
        r = helpers.call_action(
            "datastore_create",
            resource={"package_id": ds["id"]},
            fields=[
                {"id": "num", "type": "numeric"},
                {"id": "dt", "type": "timestamp"},
                {"id": "txt", "type": "text"},
                {"id": "lst", "type": "_text"},
            ],
            records=[
                {"num": 10, "dt": "2020-01-01", "txt": "aaab", "lst": ["one"]},
                {"num": 9, "dt": "2020-01-02", "txt": "aaab"},
                {"num": 9, "txt": "aaac", "lst": ["one", "two"]},
                {},  # all nulls
            ],
        )
        assert helpers.call_action(
            "datastore_search",
            resource_id=r["resource_id"],
            records_format=u"lists",
            sort=u"num nulls last, dt nulls last",
        )["records"] == [
            [2, 9, "2020-01-02T00:00:00", "aaab", None],
            [3, 9, None, "aaac", ["one", "two"]],
            [1, 10, "2020-01-01T00:00:00", "aaab", ["one"]],
            [4, None, None, None, None],
        ]
        assert helpers.call_action(
            "datastore_search",
            resource_id=r["resource_id"],
            records_format="lists",
            sort="lst nulls first, num nulls last",
        )["records"] == [
            [2, 9, "2020-01-02T00:00:00", "aaab", None],
            [4, None, None, None, None],
            [1, 10, "2020-01-01T00:00:00", "aaab", ["one"]],
            [3, 9, None, "aaac", ["one", "two"]],
        ]
        assert helpers.call_action(
            "datastore_search",
            resource_id=r["resource_id"],
            records_format=u"objects",
            sort=u"num nulls last, dt nulls last",
        )["records"] == [
            {"_id": 2, "num": 9, "dt": "2020-01-02T00:00:00", "txt": "aaab", "lst": None},
            {"_id": 3, "num": 9, "dt": None, "txt": "aaac", "lst": ["one", "two"]},
            {"_id": 1, "num": 10, "dt": "2020-01-01T00:00:00", "txt": "aaab", "lst": ["one"]},
            {"_id": 4, "num": None, "dt": None, "txt": None, "lst": None},
        ]
        assert helpers.call_action(
            "datastore_search",
            resource_id=r["resource_id"],
            records_format="objects",
            sort="lst nulls first, num nulls last",
        )["records"] == [
            {"_id": 2, "num": 9, "dt": "2020-01-02T00:00:00", "txt": "aaab", "lst": None},
            {"_id": 4, "num": None, "dt": None, "txt": None, "lst": None},
            {"_id": 1, "num": 10, "dt": "2020-01-01T00:00:00", "txt": "aaab", "lst": ["one"]},
            {"_id": 3, "num": 9, "dt": None, "txt": "aaac", "lst": ["one", "two"]},
        ]
