# encoding: utf-8

import pytest
from bs4 import BeautifulSoup

import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.common import config
from ckan.lib.helpers import url_for
from ckan.model.system_info import get_system_info

submit_and_follow = helpers.submit_and_follow
webtest_submit = helpers.webtest_submit


def _get_admin_config_page(app):
    user = factories.Sysadmin()
    env = {"REMOTE_USER": user["name"].encode("ascii")}
    response = app.get(url=url_for(controller="admin", action="config"),
                       extra_environ=env)
    return env, response


def _reset_config(app):
    """Reset config via action"""
    user = factories.Sysadmin()
    env = {"REMOTE_USER": user["name"].encode("ascii")}
    app.post(url=url_for("admin.reset_config"), extra_environ=env)


class TestConfig(object):
    """View tests to go along with 'Customizing look and feel' docs."""
    @pytest.mark.usefixtures("clean_db")
    def test_form_renders(self, app):
        """admin-config-form in the response"""

        env, response = _get_admin_config_page(app)
        assert "admin-config-form" in response.forms

    @pytest.mark.usefixtures("clean_db")
    def test_site_title(self, app):
        """Configure the site title"""
        # current site title
        index_response = app.get("/")
        assert "Welcome - CKAN" in index_response

        # change site title
        env, config_response = _get_admin_config_page(app)
        config_form = config_response.forms["admin-config-form"]
        config_form["ckan.site_title"] = "Test Site Title"
        webtest_submit(config_form, "save", status=302, extra_environ=env)

        # new site title
        new_index_response = app.get("/")
        assert "Welcome - Test Site Title" in new_index_response

        # reset config value
        _reset_config(app)
        reset_index_response = app.get("/")
        assert "Welcome - CKAN" in reset_index_response

    @pytest.mark.usefixtures("clean_db")
    def test_main_css_list(self, app):
        """Style list contains pre-configured styles"""

        STYLE_NAMES = ["Default", "Red", "Green", "Maroon", "Fuchsia"]

        env, config_response = _get_admin_config_page(app)
        config_response_html = BeautifulSoup(config_response.body)
        style_select_options = config_response_html.select(
            "#field-ckan-main-css option")
        for option in style_select_options:
            assert option.string in STYLE_NAMES

    @pytest.mark.usefixtures("clean_db")
    def test_main_css(self, app):
        """Select a colour style"""

        # current style
        index_response = app.get("/")
        assert "main.css" in index_response or "main.min.css" in index_response

        # set new style css
        env, config_response = _get_admin_config_page(app)
        config_form = config_response.forms["admin-config-form"]
        config_form["ckan.main_css"] = "/base/css/red.css"
        webtest_submit(config_form, "save", status=302, extra_environ=env)

        # new style
        new_index_response = app.get("/")
        assert "red.css" in new_index_response or "red.min.css" in new_index_response
        assert "main.css" not in new_index_response
        assert "main.min.css" not in new_index_response

        # reset config value
        _reset_config(app)
        reset_index_response = app.get("/")
        assert ("main.css" in reset_index_response
                or "main.min.css" in reset_index_response)

    @pytest.mark.usefixtures("clean_db")
    def test_tag_line(self, app):
        """Add a tag line (only when no logo)"""
        # current tagline
        index_response = app.get("/")
        assert "Special Tagline" not in index_response

        # set new tagline css
        env, config_response = _get_admin_config_page(app)
        config_form = config_response.forms["admin-config-form"]
        config_form["ckan.site_description"] = "Special Tagline"
        webtest_submit(config_form, "save", status=302, extra_environ=env)

        # new tagline not visible yet
        new_index_response = app.get("/")
        assert "Special Tagline" not in new_index_response

        # remove logo
        env, config_response = _get_admin_config_page(app)
        config_form = config_response.forms["admin-config-form"]
        config_form["ckan.site_logo"] = ""
        webtest_submit(config_form, "save", status=302, extra_environ=env)

        # new tagline
        new_index_response = app.get("/")
        assert "Special Tagline" in new_index_response

        # reset config value
        _reset_config(app)
        reset_index_response = app.get("/")
        assert "Special Tagline" not in reset_index_response

    @pytest.mark.usefixtures("clean_db")
    def test_about(self, app):
        """Add some About tag text"""

        # current about
        about_response = app.get("/about")
        assert "My special about text" not in about_response

        # set new about
        env, config_response = _get_admin_config_page(app)
        config_form = config_response.forms["admin-config-form"]
        config_form["ckan.site_about"] = "My special about text"
        webtest_submit(config_form, "save", status=302, extra_environ=env)

        # new about
        new_about_response = app.get("/about")
        assert "My special about text" in new_about_response

        # reset config value
        _reset_config(app)
        reset_about_response = app.get("/about")
        assert "My special about text" not in reset_about_response

    @pytest.mark.usefixtures("clean_db")
    def test_intro(self, app):
        """Add some Intro tag text"""

        # current intro
        intro_response = app.get("/")
        assert "My special intro text" not in intro_response

        # set new intro
        env, config_response = _get_admin_config_page(app)
        config_form = config_response.forms["admin-config-form"]
        config_form["ckan.site_intro_text"] = "My special intro text"
        webtest_submit(config_form, "save", status=302, extra_environ=env)

        # new intro
        new_intro_response = app.get("/")
        assert "My special intro text" in new_intro_response

        # reset config value
        _reset_config(app)
        reset_intro_response = app.get("/")
        assert "My special intro text" not in reset_intro_response

    @pytest.mark.usefixtures("clean_db")
    def test_custom_css(self, app):
        """Add some custom css to the head element"""
        # current tagline
        intro_response_html = BeautifulSoup(app.get("/").body)
        style_tag = intro_response_html.select("head style")
        assert len(style_tag) == 0

        # set new tagline css
        env, config_response = _get_admin_config_page(app)
        config_form = config_response.forms["admin-config-form"]
        config_form["ckan.site_custom_css"] = "body {background-color:red}"
        webtest_submit(config_form, "save", status=302, extra_environ=env)

        # new tagline not visible yet
        new_intro_response_html = BeautifulSoup(app.get("/").body)
        style_tag = new_intro_response_html.select("head style")
        assert len(style_tag) == 1
        assert style_tag[0].text.strip() == "body {background-color:red}"

        # reset config value
        _reset_config(app)
        reset_intro_response_html = BeautifulSoup(app.get("/").body)
        style_tag = reset_intro_response_html.select("head style")
        assert len(style_tag) == 0

    @pytest.mark.ckan_config("debug", True)
    @pytest.mark.usefixtures("clean_db")
    def test_homepage_style(self, app):
        """Select a homepage style"""
        # current style
        index_response = app.get("/")
        assert "<!-- Snippet home/layout1.html start -->" in index_response

        # set new style css
        env, config_response = _get_admin_config_page(app)
        config_form = config_response.forms["admin-config-form"]
        config_form["ckan.homepage_style"] = "2"
        webtest_submit(config_form, "save", status=302, extra_environ=env)

        # new style
        new_index_response = app.get("/")
        assert "<!-- Snippet home/layout1.html start -->" not in new_index_response
        assert "<!-- Snippet home/layout2.html start -->" in new_index_response

        # reset config value
        _reset_config(app)
        reset_index_response = app.get("/")
        assert "<!-- Snippet home/layout1.html start -->" in reset_index_response


class TestTrashView(object):
    """View tests for permanently deleting datasets with Admin Trash."""
    @pytest.mark.ckan_config("debug", True)
    def test_trash_view_anon_user(self, app):
        """An anon user shouldn't be able to access trash view."""
        trash_url = url_for(controller="admin", action="trash")
        trash_response = app.get(trash_url, status=403)

    @pytest.mark.usefixtures("clean_db")
    def test_trash_view_normal_user(self, app):
        """A normal logged in user shouldn't be able to access trash view."""
        user = factories.User()

        env = {"REMOTE_USER": user["name"].encode("ascii")}
        trash_url = url_for(controller="admin", action="trash")
        trash_response = app.get(trash_url, extra_environ=env, status=403)
        assert "Need to be system administrator to administer" in trash_response

    @pytest.mark.usefixtures("clean_db")
    def test_trash_view_sysadmin(self, app):
        """A sysadmin should be able to access trash view."""
        user = factories.Sysadmin()

        env = {"REMOTE_USER": user["name"].encode("ascii")}
        trash_url = url_for(controller="admin", action="trash")
        trash_response = app.get(trash_url, extra_environ=env, status=200)
        # On the purge page
        assert "form-purge-packages" in trash_response

    @pytest.mark.usefixtures("clean_db")
    def test_trash_no_datasets(self, app):
        """Getting the trash view with no 'deleted' datasets should list no
        datasets."""
        factories.Dataset()
        user = factories.Sysadmin()

        env = {"REMOTE_USER": user["name"].encode("ascii")}
        trash_url = url_for(controller="admin", action="trash")
        trash_response = app.get(trash_url, extra_environ=env, status=200)

        trash_response_html = BeautifulSoup(trash_response.body)
        # it's called a 'user list' for some reason
        trash_pkg_list = trash_response_html.select("ul.user-list li")
        # no packages available to purge
        assert len(trash_pkg_list) == 0

    @pytest.mark.usefixtures("clean_db")
    def test_trash_with_deleted_datasets(self, app):
        """Getting the trash view with 'deleted' datasets should list the
        datasets."""
        user = factories.Sysadmin()
        factories.Dataset(state="deleted")
        factories.Dataset(state="deleted")
        factories.Dataset()

        env = {"REMOTE_USER": user["name"].encode("ascii")}
        trash_url = url_for(controller="admin", action="trash")
        trash_response = app.get(trash_url, extra_environ=env, status=200)

        trash_response_html = BeautifulSoup(trash_response.body)
        # it's called a 'user list' for some reason
        trash_pkg_list = trash_response_html.select("ul.user-list li")
        # Two packages in the list to purge
        assert len(trash_pkg_list) == 2

    @pytest.mark.usefixtures("clean_db")
    def test_trash_purge_deleted_datasets(self, app):
        """Posting the trash view with 'deleted' datasets, purges the
        datasets."""
        user = factories.Sysadmin()
        factories.Dataset(state="deleted")
        factories.Dataset(state="deleted")
        factories.Dataset()

        # how many datasets before purge
        pkgs_before_purge = model.Session.query(model.Package).count()
        assert pkgs_before_purge == 3

        env = {"REMOTE_USER": user["name"].encode("ascii")}
        trash_url = url_for(controller="admin", action="trash")
        trash_response = app.get(trash_url, extra_environ=env, status=200)

        # submit the purge form
        purge_form = trash_response.forms["form-purge-packages"]
        purge_response = webtest_submit(purge_form,
                                        "purge-packages",
                                        status=302,
                                        extra_environ=env)
        purge_response = purge_response.follow(extra_environ=env)
        # redirected back to trash page
        assert "Purge complete" in purge_response

        # how many datasets after purge
        pkgs_before_purge = model.Session.query(model.Package).count()
        assert pkgs_before_purge == 1


class TestAdminConfigUpdate(object):
    def _update_config_option(self, app):
        sysadmin = factories.Sysadmin()
        env = {"REMOTE_USER": sysadmin["name"].encode("ascii")}

        url = url_for(controller="admin", action="config")

        response = app.get(url=url, extra_environ=env)
        form = response.forms[1]
        form["ckan.site_title"] = "My Updated Site Title"

        webtest_submit(form, "save", status=302, extra_environ=env)

    @pytest.mark.usefixtures("clean_db")
    def test_admin_config_update(self, make_app):
        """Changing a config option using the admin interface appropriately
        updates value returned by config_option_show,
        system_info.get_system_info and in the title tag in templates."""

        # test value before update
        # config_option_show returns default value
        before_update = helpers.call_action("config_option_show",
                                            key="ckan.site_title")
        assert before_update == "CKAN"

        # system_info.get_system_info returns None, or default
        # test value before update
        before_update = get_system_info("ckan.site_title")
        assert before_update is None
        # test value before update with default
        before_update_default = get_system_info("ckan.site_title",
                                                config["ckan.site_title"])
        assert before_update_default == "CKAN"

        # title tag contains default value
        app = make_app()
        home_page_before = app.get("/", status=200)
        assert "Welcome - CKAN" in home_page_before

        # update the option
        self._update_config_option(app)

        # test config_option_show returns new value after update
        after_update = helpers.call_action("config_option_show",
                                           key="ckan.site_title")
        assert after_update == "My Updated Site Title"

        # system_info.get_system_info returns new value
        after_update = get_system_info("ckan.site_title")
        assert after_update == "My Updated Site Title"
        # test value after update with default
        after_update_default = get_system_info("ckan.site_title",
                                               config["ckan.site_title"])
        assert after_update_default == "My Updated Site Title"

        # title tag contains new value
        home_page_after = app.get("/", status=200)
        assert "Welcome - My Updated Site Title" in home_page_after
