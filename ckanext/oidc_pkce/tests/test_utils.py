import pytest

from ckan import model

from ckanext.oidc_pkce import utils


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestSyncUser:
    def test_user_created(self, user_info):
        utils.sync_user(user_info)

        assert model.User.by_email(user_info["email"])

    def test_existing_user_attached(self, user_factory, user_info):
        user = user_factory(email=user_info["email"])
        utils.sync_user(user_info)

        attached = model.User.by_email(user_info["email"])
        if isinstance(attached, list):
            # CKAN < 2.10
            attached = attached[0]

        assert user["id"] == attached.id

    def test_sync_by_case_insensitive_email(self, user_factory, user_info):
        user = user_factory(email=user_info["email"].upper())
        utils.sync_user(user_info)

        attached = model.User.by_email(user_info["email"])
        if isinstance(attached, list):
            # CKAN < 2.10
            attached = attached[0]

        assert user["id"] == attached.id
