# -*- coding: utf-8 -*-

import pytest

import ckan.plugins.toolkit as tk
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("clean_db", "with_plugins", "reset_index")
@pytest.mark.ckan_config("ckan.activity_list_limit", "5")
@pytest.mark.ckan_config("ckan.activity_list_limit_max", "7")
class TestPagination():

    def test_pagination(self, app):
        user = factories.User()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])

        for i in range(0, 8):
            dataset["notes"] = f"Update number: {i}"
            helpers.call_action(
                "package_update",
                context={"user": user["name"]},
                **dataset,
            )

        # Test initial pagination buttons are rendered correctly
        url = tk.url_for("dataset.activity", id=dataset["id"])
        response = app.get(url)

        assert '<a href="None" class="btn disabled">Newer activities</a>' in response.body
        assert f'<a href="/dataset/activity/{dataset["id"]}?before=' in response.body

        url = tk.url_for("activity.organization_activity", id=org["id"])
        response = app.get(url)

        assert '<a href="None" class="btn disabled">Newer activities</a>' in response.body
        assert f'<a href="/organization/activity/{org["id"]}?before=' in response.body
