# encoding: utf-8

import pytest
from bs4 import BeautifulSoup

import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.common import config
from ckan.lib.helpers import url_for
from ckan.model.system_info import get_system_info


@pytest.fixture
def sysadmin_headers():
    user = factories.SysadminWithToken()
    headers = {"Authorization": user["token"]}
    return headers


@pytest.fixture
def user_headers():
    user = factories.UserWithToken()
    headers = {"Authorization": user["token"]}
    return headers


def _reset_config(app, sysadmin_headers):
    """Reset config via action"""
    app.post(url=url_for("admin.reset_config"), headers=sysadmin_headers)


@pytest.mark.usefixtures("clean_db")
def test_index(app, user_headers, sysadmin_headers):

    url = url_for("admin.index")
    # Anonymous User
    response = app.get(url, status=403)

    # Normal User
    response = app.get(url, headers=user_headers, status=403)

    # Sysadmin User
    response = app.get(url, headers=sysadmin_headers)
    assert "Administration" in response, response


@pytest.mark.usefixtures("clean_db")
class TestConfig(object):
    """View tests to go along with 'Customizing look and feel' docs."""

    def test_site_title(self, app, sysadmin_headers):
        """Configure the site title"""

        _reset_config(app, sysadmin_headers)

        # current site title
        index_response = app.get("/")
        assert "Welcome - CKAN" in index_response

        url = url_for(u"admin.config")

        # change site title
        form = {"ckan.site_title": "Test Site Title", "save": ""}
        app.post(url, headers=sysadmin_headers, data=form)

        # new site title
        new_index_response = app.get("/")
        assert "Welcome - Test Site Title" in new_index_response

        # reset config value
        _reset_config(app, sysadmin_headers)
        reset_index_response = app.get("/")
        assert "Welcome - CKAN" in reset_index_response

    def test_main_theme(self, app, sysadmin_headers):
        """Define a custom css file"""

        # current style
        index_response = app.get("/")
        assert "main.css" in index_response or "main.min.css" in index_response

        url = url_for(u"admin.config")

        # set new style css
        form = {"ckan.theme": "css/main-rtl", "save": ""}
        resp = app.post(url, headers=sysadmin_headers, data=form)

        assert "main-rtl.css" in resp or "main-rtl.min.css" in resp
        assert not helpers.body_contains(resp, "main.min.css")

    def test_tag_line(self, app, sysadmin_headers):
        """Add a tag line (only when no logo)"""

        # current tagline
        index_response = app.get("/")
        assert "Special Tagline" not in index_response

        url = url_for(u"admin.config")

        # set new tagline css
        form = {"ckan.site_description": "Special Tagline", "save": ""}
        app.post(url, data=form, headers=sysadmin_headers)

        # new tagline not visible yet
        new_index_response = app.get("/")
        assert "Special Tagline" not in new_index_response

        url = url_for(u"admin.config")
        # remove logo
        form = {"ckan.site_logo": "", "save": ""}
        app.post(url, data=form, headers=sysadmin_headers)

        # new tagline
        new_index_response = app.get("/")
        assert "Special Tagline" in new_index_response

        # reset config value
        _reset_config(app, sysadmin_headers)
        reset_index_response = app.get("/")
        assert "Special Tagline" not in reset_index_response

    def test_about(self, app, sysadmin_headers):
        """Add some About tag text"""

        # current about
        about_response = app.get("/about")
        assert "My special about text" not in about_response

        # set new about
        url = url_for(u"admin.config")
        form = {"ckan.site_about": "My special about text", "save": ""}
        app.post(url, headers=sysadmin_headers, data=form)

        # new about
        new_about_response = app.get("/about")
        assert "My special about text" in new_about_response

        # reset config value
        _reset_config(app, sysadmin_headers)
        reset_about_response = app.get("/about")
        assert "My special about text" not in reset_about_response

    def test_intro(self, app, sysadmin_headers):
        """Add some Intro tag text"""

        # current intro
        intro_response = app.get("/")
        assert "My special intro text" not in intro_response

        # set new intro
        url = url_for(u"admin.config")
        form = {"ckan.site_intro_text": "My special intro text", "save": ""}
        app.post(url, headers=sysadmin_headers, data=form)

        # new intro
        new_intro_response = app.get("/")
        assert "My special intro text" in new_intro_response

        # reset config value
        _reset_config(app, sysadmin_headers)
        reset_intro_response = app.get("/")
        assert "My special intro text" not in reset_intro_response

    def test_custom_css(self, app, sysadmin_headers):
        """Add some custom css to the head element"""
        # current tagline
        intro_response_html = BeautifulSoup(app.get("/").body)
        style_tag = intro_response_html.select("head style")
        assert len(style_tag) == 0

        # set new tagline css
        url = url_for(u"admin.config")
        form = {
            "ckan.site_custom_css": "body {background-color:red}",
            "save": "",
        }
        app.post(url, headers=sysadmin_headers, data=form)

        # new tagline not visible yet
        new_intro_response_html = BeautifulSoup(app.get("/").body)
        style_tag = new_intro_response_html.select("head style")
        assert len(style_tag) == 1
        assert style_tag[0].string.strip() == "body {background-color:red}"

        # reset config value
        _reset_config(app, sysadmin_headers)
        reset_intro_response_html = BeautifulSoup(app.get("/").body)
        style_tag = reset_intro_response_html.select("head style")
        assert len(style_tag) == 0


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestTrashView(object):
    """View tests for permanently deleting datasets with Admin Trash."""

    def test_trash_view_anon_user(self, app):
        """An anon user shouldn't be able to access trash view."""
        trash_url = url_for("admin.trash")
        trash_response = app.get(trash_url)
        assert trash_response.status_code == 403

    def test_trash_view_normal_user(self, app, user_headers):
        """A normal logged in user shouldn't be able to access trash view."""
        trash_url = url_for("admin.trash")
        trash_response = app.get(trash_url, headers=user_headers, status=403)
        assert trash_response.status_code == 403

    def test_trash_view_sysadmin(self, app, sysadmin_headers):
        """A sysadmin should be able to access trash view."""
        trash_url = url_for("admin.trash")
        trash_response = app.get(trash_url, headers=sysadmin_headers, status=200)
        # On the purge page
        assert "purge-all" in trash_response

    def test_trash_no_datasets(self, app, sysadmin_headers):
        """Getting the trash view with no 'deleted' datasets should list no
        datasets."""
        factories.Dataset()

        trash_url = url_for("admin.trash")
        trash_response = app.get(trash_url, headers=sysadmin_headers, status=200)

        response_html = BeautifulSoup(trash_response.body)
        trash_pkg_list = response_html.select("ul.package-list li")
        # no packages available to purge
        assert len(trash_pkg_list) == 0

    def test_trash_no_groups(self, app, sysadmin_headers):
        """Getting the trash view with no 'deleted' groups should list no
        groups."""
        factories.Group()

        trash_url = url_for("admin.trash")
        trash_response = app.get(trash_url, headers=sysadmin_headers, status=200)

        response_html = BeautifulSoup(trash_response.body)
        trash_grp_list = response_html.select("ul.group-list li")
        # no packages available to purge
        assert len(trash_grp_list) == 0

    def test_trash_no_organizations(self, app, sysadmin_headers):
        """Getting the trash view with no 'deleted' organizations should list no
        organizations."""
        factories.Organization()

        trash_url = url_for("admin.trash")
        trash_response = app.get(trash_url, headers=sysadmin_headers, status=200)

        response_html = BeautifulSoup(trash_response.body)
        trash_org_list = response_html.select("ul.organization-list li")
        # no packages available to purge
        assert len(trash_org_list) == 0

    @pytest.mark.ckan_config("ckan.search.remove_deleted_packages", True)
    def test_trash_with_deleted_datasets(self, app, sysadmin_headers):
        """Getting the trash view with 'deleted' datasets should list the
        datasets."""
        factories.Dataset(state="deleted")
        factories.Dataset(state="deleted")
        factories.Dataset()

        trash_url = url_for("admin.trash")
        response = app.get(trash_url, headers=sysadmin_headers, status=200)

        response_html = BeautifulSoup(response.body)
        trash_pkg_list = response_html.select("ul.package-list li")
        # Two packages in the list to purge
        assert len(trash_pkg_list) == 2

    @pytest.mark.usefixtures("clean_index")
    @pytest.mark.ckan_config("ckan.search.remove_deleted_packages", False)
    def test_trash_with_deleted_datasets_no_remove_deleted_packages(self, app, sysadmin_headers):
        """Getting the trash view with 'deleted' datasets should list the
        datasets."""
        factories.Dataset(state="deleted")
        factories.Dataset(state="deleted")
        factories.Dataset()

        trash_url = url_for("admin.trash")

        response = app.get(trash_url, headers=sysadmin_headers, status=200)

        response_html = BeautifulSoup(response.body)
        trash_pkg_list = response_html.select("ul.package-list li")
        # Two packages in the list to purge
        assert len(trash_pkg_list) == 2

    def test_trash_with_deleted_groups(self, app, sysadmin_headers):
        """Getting the trash view with "deleted" groups should list the
        groups."""
        factories.Group(state="deleted")
        factories.Group(state="deleted")
        factories.Group()

        trash_url = url_for("admin.trash")
        response = app.get(trash_url, headers=sysadmin_headers, status=200)

        response_html = BeautifulSoup(response.body)
        trash_grp_list = response_html.select("ul.group-list li")
        # Two groups in the list to purge
        assert len(trash_grp_list) == 2

    def test_trash_with_deleted_organizations(self, app, sysadmin_headers):
        """Getting the trash view with 'deleted' organizations should list the
        organizations."""
        factories.Organization(state="deleted")
        factories.Organization(state="deleted")
        factories.Organization()

        trash_url = url_for("admin.trash")
        response = app.get(trash_url, headers=sysadmin_headers, status=200)

        response_html = BeautifulSoup(response.body)
        trash_org_list = response_html.select("ul.organization-list li")
        # Two organizations in the list to purge
        assert len(trash_org_list) == 2

    def test_trash_with_deleted_entities(self, app, sysadmin_headers):
        """Getting the trash view with 'deleted' entities should list the
        all types of entities."""
        factories.Dataset(state="deleted")
        factories.Group(state="deleted")
        factories.Organization(state="deleted")
        factories.Organization()

        trash_url = url_for("admin.trash")
        response = app.get(trash_url, headers=sysadmin_headers, status=200)

        response_html = BeautifulSoup(response.body)

        # Getting the amount of entity of each type to purge
        trash_pkg_list = len(response_html.select("ul.package-list li"))
        trash_grp_list = len(response_html.select("ul.group-list li"))
        trash_org_list = len(response_html.select("ul.organization-list li"))
        entities_amount = trash_pkg_list + trash_grp_list + trash_org_list

        # One entity of each type in the list to purge
        assert entities_amount == 3

    def test_trash_purge_custom_ds_type(self, app, sysadmin_headers):
        """Posting the trash view with 'deleted' datasets, purges the
        datasets."""
        factories.Dataset(state="deleted", type="custom_dataset")
        # how many datasets before purge
        pkgs_before_purge = model.Session.query(model.Package).count()
        assert pkgs_before_purge == 1

        trash_url = url_for("admin.trash")
        response = app.post(trash_url, data={"action": "package"}, headers=sysadmin_headers)
        # check for flash success msg
        assert "datasets have been purged" in response.body

        # how many datasets after purge
        pkgs_after_purge = model.Session.query(model.Package).count()
        assert pkgs_after_purge == 0

    @pytest.mark.ckan_config("ckan.search.remove_deleted_packages", True)
    def test_trash_purge_deleted_datasets(self, app, sysadmin_headers):
        """Posting the trash view with 'deleted' datasets, purges the
        datasets."""
        factories.Dataset(state="deleted")
        factories.Dataset(state="deleted")
        factories.Dataset()
        # how many datasets before purge
        pkgs_before_purge = model.Session.query(model.Package).count()
        assert pkgs_before_purge == 3

        trash_url = url_for("admin.trash")
        response = app.post(trash_url, data={"action": "package"}, headers=sysadmin_headers)
        # check for flash success msg
        assert "datasets have been purged" in response.body

        # how many datasets after purge
        pkgs_after_purge = model.Session.query(model.Package).count()
        assert pkgs_after_purge == 1

    @pytest.mark.usefixtures("clean_index")
    @pytest.mark.ckan_config("ckan.search.remove_deleted_packages", False)
    def test_trash_purge_deleted_datasets_no_remove_deleted_packages(self, app, sysadmin_headers):
        """Posting the trash view with 'deleted' datasets, purges the
        datasets."""
        factories.Dataset(state="deleted")
        factories.Dataset(state="deleted")
        factories.Dataset()
        # how many datasets before purge
        pkgs_before_purge = model.Session.query(model.Package).count()
        assert pkgs_before_purge == 3

        trash_url = url_for("admin.trash")
        response = app.post(trash_url, data={"action": "package"}, headers=sysadmin_headers)
        # check for flash success msg
        assert "datasets have been purged" in response.body

        # how many datasets after purge
        pkgs_after_purge = model.Session.query(model.Package).count()
        assert pkgs_after_purge == 1

    def test_trash_purge_deleted_groups(self, app, sysadmin_headers):
        """Posting the trash view with 'deleted' groups, purges the
        groups."""
        factories.Group(state="deleted")
        factories.Group(state="deleted")
        factories.Group()
        # how many groups before purge
        grps_before_purge = model.Session.query(model.Group).count()
        assert grps_before_purge == 3

        trash_url = url_for("admin.trash")
        response = app.post(trash_url, data={"action": "group"}, headers=sysadmin_headers)
        # check for flash success msg
        assert "groups have been purged" in response

        # how many groups after purge
        grps_after_purge = model.Session.query(model.Group).count()
        assert grps_after_purge == 1

    def test_trash_purge_deleted_organization(self, app, sysadmin_headers):
        """Posting the trash view with 'deleted' organizations, purges the
        organizations."""
        factories.Organization(state="deleted")
        factories.Organization(state="deleted")
        factories.Organization()
        # how many organizations before purge
        orgs_before_purge = model.Session.query(model.Group).filter_by(
            is_organization=True).count()
        assert orgs_before_purge == 3

        trash_url = url_for("admin.trash")
        response = app.post(trash_url, data={"action": "organization"}, headers=sysadmin_headers)
        # check for flash success msg
        assert "organizations have been purged" in response

        # how many organizations after purge
        orgs_after_purge = model.Session.query(model.Group).filter_by(
            is_organization=True).count()
        assert orgs_after_purge == 1

    @pytest.mark.ckan_config("ckan.search.remove_deleted_packages", True)
    def test_trash_purge_all(self, app, sysadmin_headers):
        """Posting the trash view with 'deleted' entities and
        purge all button purges everything"""
        factories.Dataset(state="deleted", type="custom_dataset")
        factories.Group(state="deleted")
        factories.Organization(state="deleted")
        factories.Organization(state="deleted", type="custom_org")
        factories.Organization()
        # how many entities before purge
        pkgs_before_purge = model.Session.query(model.Package).count()
        orgs_and_grps_before_purge = model.Session.query(model.Group).count()
        assert pkgs_before_purge + orgs_and_grps_before_purge == 5

        trash_url = url_for("admin.trash")
        response = app.post(trash_url, data={"action": "all"}, headers=sysadmin_headers)
        # check for flash success msg
        assert "Massive purge complete" in response

        # how many entities after purge
        pkgs_after_purge = model.Session.query(model.Package).count()
        orgs_and_grps_after_purge = model.Session.query(model.Group).count()
        assert pkgs_after_purge + orgs_and_grps_after_purge == 1

    @pytest.mark.usefixtures("clean_index")
    @pytest.mark.ckan_config("ckan.search.remove_deleted_packages", False)
    def test_trash_purge_all_no_remove_deleted_packages(self, app, sysadmin_headers):
        """Posting the trash view with 'deleted' entities and
        purge all button purges everything"""
        factories.Dataset(state="deleted", type="custom_dataset")
        factories.Group(state="deleted")
        factories.Organization(state="deleted")
        factories.Organization(state="deleted", type="custom_org")
        factories.Organization()

        # how many entities before purge
        pkgs_before_purge = model.Session.query(model.Package).count()
        orgs_and_grps_before_purge = model.Session.query(model.Group).count()
        assert pkgs_before_purge + orgs_and_grps_before_purge == 5
        trash_url = url_for("admin.trash")
        response = app.post(trash_url, data={"action": "all"}, headers=sysadmin_headers)
        # check for flash success msg
        assert "Massive purge complete" in response

        # how many entities after purge
        pkgs_after_purge = model.Session.query(model.Package).count()
        orgs_and_grps_after_purge = model.Session.query(model.Group).count()
        assert pkgs_after_purge + orgs_and_grps_after_purge == 1

    def test_trash_cancel_purge(self, app, sysadmin_headers):
        """Cancelling purge doesn't purge anything."""
        factories.Organization(state="deleted")
        factories.Organization(state="deleted")

        # how many organizations before purge
        orgs_before_purge = model.Session.query(model.Group).filter_by(
            is_organization=True).count()
        assert orgs_before_purge == 2

        trash_url = url_for("admin.trash", name="purge-organization")
        response = app.post(trash_url, data={"cancel": ""}, headers=sysadmin_headers, status=200)
        # flash success msg should be absent
        assert "Organizations have been purged" not in response

        # how many organizations after cancel purge
        orgs_after_purge = model.Session.query(model.Group).filter_by(
            is_organization=True).count()
        assert orgs_after_purge == 2

    def test_trash_no_button_with_no_deleted_datasets(self, app, sysadmin_headers):
        """Getting the trash view with no 'deleted' datasets should not
        contain the purge button."""
        trash_url = url_for("admin.trash")
        trash_response = app.get(trash_url, headers=sysadmin_headers, status=200)
        assert "form-purge-package" not in trash_response

    def test_trash_button_with_deleted_datasets(self, app, sysadmin_headers):
        """Getting the trash view with 'deleted' datasets should
        contain the purge button."""
        factories.Dataset(state="deleted")

        trash_url = url_for("admin.trash")
        trash_response = app.get(trash_url, headers=sysadmin_headers, status=200)
        assert "form-purge-package" in trash_response


@pytest.mark.usefixtures("clean_db")
class TestAdminConfigUpdate(object):
    def _update_config_option(self, app, sysadmin_headers):
        url = url_for(u"admin.config")
        form = {"ckan.site_title": "My Updated Site Title", "save": ""}
        return app.post(url, headers=sysadmin_headers, data=form)

    def test_admin_config_update(self, app, sysadmin_headers):
        """Changing a config option using the admin interface appropriately
        updates value returned by config_option_show,
        system_info.get_system_info and in the title tag in templates."""

        # test value before update
        # config_option_show returns default value
        before_update = helpers.call_action(
            "config_option_show", key="ckan.site_title"
        )
        assert before_update == "CKAN"

        # system_info.get_system_info returns None, or default
        # test value before update
        before_update = get_system_info("ckan.site_title")
        assert before_update is None
        # test value before update with default
        before_update_default = get_system_info(
            "ckan.site_title", config["ckan.site_title"]
        )
        assert before_update_default == "CKAN"

        # title tag contains default value
        # app = make_app()
        home_page_before = app.get("/", status=200)
        assert "Welcome - CKAN" in home_page_before

        # update the option
        self._update_config_option(app, sysadmin_headers)

        # test config_option_show returns new value after update
        after_update = helpers.call_action(
            "config_option_show", key="ckan.site_title"
        )
        assert after_update == "My Updated Site Title"

        # system_info.get_system_info returns new value
        after_update = get_system_info("ckan.site_title")
        assert after_update == "My Updated Site Title"
        # test value after update with default
        after_update_default = get_system_info(
            "ckan.site_title", config["ckan.site_title"]
        )
        assert after_update_default == "My Updated Site Title"

        # title tag contains new value
        home_page_after = app.get("/", status=200)
        assert "Welcome - My Updated Site Title" in home_page_after

        _reset_config(app, sysadmin_headers)
