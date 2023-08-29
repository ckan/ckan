# -*- coding: utf-8 -*-

import pytest

import ckan.plugins.toolkit as tk
import ckan.tests.helpers as helpers
import ckan.model as model


@pytest.mark.ckan_config("ckan.plugins", "activity")
@pytest.mark.usefixtures("with_plugins")
class TestAuth:
    @pytest.mark.ckan_config(
        "ckan.auth.public_activity_stream_detail", "false"
    )
    def test_config_option_public_activity_stream_detail_denied(self, package):
        """Config option says an anon user is not authorized to get activity
        stream data/detail.
        """
        context = {"user": None, "model": model}
        with pytest.raises(tk.NotAuthorized):
            helpers.call_auth(
                "package_activity_list",
                context=context,
                id=package["id"],
                include_data=True,
            )

    @pytest.mark.ckan_config("ckan.auth.public_activity_stream_detail", "true")
    def test_config_option_public_activity_stream_detail(self, package):
        """Config option says an anon user is authorized to get activity
        stream data/detail.
        """
        context = {"user": None, "model": model}
        helpers.call_auth(
            "package_activity_list",
            context=context,
            id=package["id"],
            include_data=True,
        )

    def test_normal_user_cant_use_it(self, user):
        context = {"user": user["name"], "model": model}

        with pytest.raises(tk.NotAuthorized):
            helpers.call_auth("activity_create", context=context)
