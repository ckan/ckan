# encoding: utf-8

import pytest

import ckan.logic as logic
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers


@pytest.mark.usefixtures("non_clean_db")
class TestUserCreatePasswordOptional:
    def test_ignore_auth_can_create_user_without_password(self):
        stub = factories.User.stub()

        user = helpers.call_action(
            "user_create",
            context={"ignore_auth": True},
            name=stub.name,
            email=stub.email,
        )

        assert user["name"] == stub.name
        assert user["email"] == stub.email

    @pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
    def test_normal_user_creation_still_requires_password(self):
        stub = factories.User.stub()
        context = {"user": None, "ignore_auth": False}

        with pytest.raises(logic.ValidationError) as err:
            helpers.call_action(
                "user_create",
                context=context,
                name=stub.name,
                email=stub.email,
            )

        assert err.value.error_dict == {"password": ["Missing value"]}
