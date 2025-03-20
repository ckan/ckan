import pytest
from ckan.lib.helpers import url_for
from ckan.tests import factories


@pytest.mark.usefixtures("clean_db")
class TestUserApiTokenUI:
    def test_user_page_api_token(self, app):
        """ user/<id>/api-tokens list"""
        user = factories.User()

        user_url = url_for("user.api_tokens", id=user['name'])
        api_token_response = app.get(user_url, status=200)

        assert 'Create API Token' in api_token_response

    def test_user_page_api_token_post(self, app):
        """ user/<id>/api-tokens post to create a new token"""
        user = factories.User()

        user_url = url_for("user.api_tokens", id=user['name'])
        # We expect a ~clean page with the token in a flash message and
        # a button to create more tokens
        api_token_response = app.post(user_url, status=200)
        assert 'Create New API Token' in api_token_response
