# encoding: utf-8

import pytest
from ckan.lib.helpers import url_for
from bs4 import BeautifulSoup

from ckan.tests import factories


class TestHome(object):
    def test_home_renders(self, app):
        response = app.get(url_for("home.index"))
        assert "Welcome to CKAN" in response.body

    def test_template_head_end(self, app):
        # test-core.ini sets ckan.template_head_end to this:
        test_link = (
            '<link rel="stylesheet" '
            'href="TEST_TEMPLATE_HEAD_END.css" type="text/css">'
        )
        response = app.get(url_for("home.index"))
        assert test_link in response.body

    def test_template_footer_end(self, app):
        # test-core.ini sets ckan.template_footer_end to this:
        test_html = "<strong>TEST TEMPLATE_FOOTER_END TEST</strong>"
        response = app.get(url_for("home.index"))
        assert test_html in response.body

    @pytest.mark.usefixtures("non_clean_db")
    def test_email_address_nag(self, app):
        # before CKAN 1.6, users were allowed to have no email addresses
        # can't use factory to create user as without email it fails validation
        from ckan import model

        user = model.User(name="has-no-email", password="correct123")
        model.Session.add(user)
        model.Session.commit()

        user_token = factories.APIToken(user=user.id)
        env = {"Authorization": user_token["token"]}

        response = app.get(url=url_for("home.index"), extra_environ=env)

        assert "update your profile" in response.body
        assert str(url_for("user.edit")) in response.body
        assert " and add your email address." in response.body

    @pytest.mark.usefixtures("non_clean_db")
    def test_email_address_no_nag(self, app):
        user = factories.User(email="filled_in@nicely.com")
        user_token = factories.APIToken(user=user["name"])

        env = {"Authorization": user_token["token"]}
        response = app.get(url=url_for("home.index"), extra_environ=env)

        assert "add your email address" not in response

    @pytest.mark.ckan_config(
        "ckan.legacy_route_mappings", '{"my_home_route": "home.index"}'
    )
    def test_map_pylons_to_flask_route(self, app):
        response = app.get(url_for("my_home_route"))
        assert "Welcome to CKAN" in response.body

        response = app.get(url_for("home"))
        assert "Welcome to CKAN" in response.body

    @pytest.mark.ckan_config(
        "ckan.legacy_route_mappings", {"my_home_route": "home.index"}
    )
    def test_map_pylons_to_flask_route_using_dict(self, app):
        response = app.get(url_for("my_home_route"))
        assert "Welcome to CKAN" in response.body

        response = app.get(url_for("home"))
        assert "Welcome to CKAN" in response.body


@pytest.mark.usefixtures("with_request_context")
class TestI18nURLs(object):
    def test_right_urls_are_rendered_on_language_selector(self, app):

        response = app.get(url_for("home.index"))
        html = BeautifulSoup(response.body)

        select = html.find(id="field-lang-select")
        for option in select.find_all("option"):
            if option.text.strip() == u"English":
                assert option["value"] == "/en/"
            elif option.text.strip() == u"čeština (Česká republika)":
                assert option["value"] == "/cs_CZ/"
            elif option.text.strip() == u"português (Brasil)":
                assert option["value"] == "/pt_BR/"
            elif option.text.strip() == u"srpski (latinica)":
                assert option["value"] == "/sr_Latn/"

    def test_default_english_option_is_selected_on_language_selector(
        self, app
    ):
        response = app.get(url_for("home.index"))
        html = BeautifulSoup(response.body)

        select = html.find(id="field-lang-select")
        for option in select.find_all("option"):
            if option["value"] == "/en/":
                assert option["selected"] == "selected"
            else:
                assert not option.has_attr("selected")

    def test_right_option_is_selected_on_language_selector(self, app):
        response = app.get(url_for("home.index", locale="ca"))
        html = BeautifulSoup(response.body)

        select = html.find(id="field-lang-select")
        for option in select.find_all("option"):
            if option["value"] == "/ca/":
                assert option["selected"] == "selected"
            else:
                assert not option.has_attr("selected")

    def test_redirects_legacy_locales(self, app):
        locales_mapping = [
            ('zh_TW', 'zh_Hant_TW'),
            ('zh_CN', 'zh_Hans_CN'),
        ]

        for locale in locales_mapping:

            legacy_locale = locale[0]
            new_locale = locale[1]

            response = app.get(f'/{legacy_locale}/', follow_redirects=False)

            assert response.status_code == 308
            assert (
                response.headers['Location'] ==
                f'http://test.ckan.net/{new_locale}'
            )

            response = app.get(f'/{legacy_locale}/dataset?some=param', follow_redirects=False)

            assert response.status_code == 308
            assert (
                response.headers['Location'] ==
                f'http://test.ckan.net/{new_locale}/dataset?some=param'
            )
