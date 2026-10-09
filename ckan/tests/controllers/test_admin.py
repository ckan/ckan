# encoding: utf-8

import pytest
from bs4 import BeautifulSoup

import ckan.lib.jobs as jobs
import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import ckan.views.admin as admin_view
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


ENT_TYPE_FACTORY = {
    "dataset": factories.Dataset,
    "group": factories.Group,
    "organization": factories.Organization,
}


@pytest.mark.usefixtures("clean_db", "clean_index")
class TestTrashView(helpers.RQTestBase):
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
        """A sysadmin should be able to access trash view, defaulting to the
        dataset tab."""
        trash_url = url_for("admin.trash")
        trash_response = app.get(trash_url, headers=sysadmin_headers, status=200)
        assert "There are no datasets to purge" in trash_response

    def test_trash_unknown_ent_type_404s(self, app, sysadmin_headers):
        trash_url = url_for("admin.trash", ent_type="not-a-real-type")
        app.get(trash_url, headers=sysadmin_headers, status=404)

    @pytest.mark.parametrize("ent_type", ["dataset", "group", "organization"])
    def test_trash_empty_tab_has_no_entities(self, app, sysadmin_headers, ent_type):
        """An active (non-deleted) entity should never show up in its tab."""
        ENT_TYPE_FACTORY[ent_type]()

        trash_url = url_for("admin.trash", ent_type=ent_type)
        trash_response = app.get(trash_url, headers=sysadmin_headers, status=200)

        response_html = BeautifulSoup(trash_response.body)
        assert len(response_html.select('input[name="entity_id"]')) == 0
        assert f"form-bulk-{ent_type}" not in trash_response

    @pytest.mark.parametrize("ent_type", ["group", "organization"])
    def test_trash_tab_lists_only_deleted_entities_of_that_type(
        self, app, sysadmin_headers, ent_type
    ):
        factory = ENT_TYPE_FACTORY[ent_type]
        factory(state="deleted")
        factory(state="deleted")
        factory()

        trash_url = url_for("admin.trash", ent_type=ent_type)
        response = app.get(trash_url, headers=sysadmin_headers, status=200)

        response_html = BeautifulSoup(response.body)
        assert len(response_html.select('input[name="entity_id"]')) == 2
        assert f"form-bulk-{ent_type}" in response

    @pytest.mark.ckan_config("ckan.search.remove_deleted_packages", True)
    def test_trash_dataset_tab_from_db(self, app, sysadmin_headers):
        factories.Dataset(state="deleted")
        factories.Dataset(state="deleted")
        factories.Dataset()

        trash_url = url_for("admin.trash", ent_type="dataset")
        response = app.get(trash_url, headers=sysadmin_headers, status=200)

        response_html = BeautifulSoup(response.body)
        assert len(response_html.select('input[name="entity_id"]')) == 2

    @pytest.mark.usefixtures("clean_index")
    @pytest.mark.ckan_config("ckan.search.remove_deleted_packages", False)
    def test_trash_dataset_tab_from_search_index(self, app, sysadmin_headers):
        factories.Dataset(state="deleted")
        factories.Dataset(state="deleted")
        factories.Dataset()

        trash_url = url_for("admin.trash", ent_type="dataset")
        response = app.get(trash_url, headers=sysadmin_headers, status=200)

        response_html = BeautifulSoup(response.body)
        assert len(response_html.select('input[name="entity_id"]')) == 2

    @pytest.mark.ckan_config("ckan.search.remove_deleted_packages", True)
    def test_trash_dataset_tab_search_filters_by_title(self, app, sysadmin_headers):
        factories.Dataset(state="deleted", title="alpha dataset")
        factories.Dataset(state="deleted", title="beta dataset")

        trash_url = url_for("admin.trash", ent_type="dataset")
        response = app.get(
            trash_url, headers=sysadmin_headers, status=200, params={"q": "alpha"}
        )

        response_html = BeautifulSoup(response.body)
        assert len(response_html.select('input[name="entity_id"]')) == 1
        assert "alpha dataset" in response.body
        assert "beta dataset" not in response.body

    @pytest.mark.parametrize("ent_type", ["group", "organization"])
    def test_trash_search_filters_group_or_org_by_title(
        self, app, sysadmin_headers, ent_type
    ):
        factory = ENT_TYPE_FACTORY[ent_type]
        factory(state="deleted", title="alpha")
        factory(state="deleted", title="beta")

        trash_url = url_for("admin.trash", ent_type=ent_type)
        response = app.get(
            trash_url, headers=sysadmin_headers, status=200, params={"q": "alpha"}
        )

        response_html = BeautifulSoup(response.body)
        assert len(response_html.select('input[name="entity_id"]')) == 1

    def test_trash_search_no_results_hides_purge_all(self, app, sysadmin_headers):
        factories.Dataset(state="deleted", title="alpha dataset")

        trash_url = url_for("admin.trash", ent_type="dataset")
        response = app.get(
            trash_url, headers=sysadmin_headers, status=200, params={"q": "no-match"}
        )

        assert "No results for your search." in response.body
        assert "purge-all" not in response.body

    def test_trash_purge_single_selected_is_synchronous(self, app, sysadmin_headers):
        """Selecting exactly one entity purges it immediately, no
        background job involved."""
        dataset = factories.Dataset(state="deleted", type="custom_dataset")
        assert model.Session.query(model.Package).count() == 1

        trash_url = url_for("admin.trash", ent_type="dataset")
        response = app.post(
            trash_url,
            data={"action": "purge_selected", "entity_id": dataset["id"]},
            headers=sysadmin_headers,
        )
        assert "Entity has been purged" in response.body

        assert model.Session.query(model.Package).count() == 0
        assert self.all_jobs() == []

    def test_trash_restore_single_dataset(self, app, sysadmin_headers):
        """Restoring a deleted entity via the row action sets it back to
        active instead of purging it."""
        dataset = factories.Dataset(state="deleted")

        trash_url = url_for("admin.trash", ent_type="dataset")
        response = app.post(
            trash_url,
            data={"action": "restore_single", "entity_id": dataset["id"]},
            headers=sysadmin_headers,
        )

        pkg = model.Package.get(dataset["id"])

        assert pkg
        assert "Entity has been restored" in response.body
        assert pkg.state == model.State.ACTIVE

    @pytest.mark.parametrize("ent_type", ["group", "organization"])
    def test_trash_restore_single_group_or_org(self, app, sysadmin_headers, ent_type):
        entity = ENT_TYPE_FACTORY[ent_type](state="deleted")

        trash_url = url_for("admin.trash", ent_type=ent_type)
        response = app.post(
            trash_url,
            data={"action": "restore_single", "entity_id": entity["id"]},
            headers=sysadmin_headers,
        )

        group = model.Group.get(entity["id"])

        assert group
        assert "Entity has been restored" in response.body
        assert group.state == model.State.ACTIVE

    def test_trash_restore_single_not_found(self, app, sysadmin_headers):
        trash_url = url_for("admin.trash", ent_type="dataset")
        response = app.post(
            trash_url,
            data={"action": "restore_single", "entity_id": "does-not-exist"},
            headers=sysadmin_headers,
        )
        assert "Entity not found" in response.body

    def test_trash_purge_selected_multiple_is_queued(self, app, sysadmin_headers):
        """Selecting more than one entity enqueues a background job instead
        of purging inline."""
        ds1 = factories.Dataset(state="deleted")
        ds2 = factories.Dataset(state="deleted")
        factories.Dataset()
        assert model.Session.query(model.Package).count() == 3

        trash_url = url_for("admin.trash", ent_type="dataset")
        response = app.post(
            trash_url,
            data={
                "action": "purge_selected",
                "entity_id": [ds1["id"], ds2["id"]],
            },
            headers=sysadmin_headers,
        )
        assert "Purge job for 2 dataset(s) has been queued" in response.body

        # nothing purged yet: the job hasn't been run, only enqueued
        assert model.Session.query(model.Package).count() == 3
        assert len(self.all_jobs()) == 1

    def test_trash_purge_selected_no_ids_flashes_error(self, app, sysadmin_headers):
        factories.Dataset(state="deleted")

        trash_url = url_for("admin.trash", ent_type="dataset")
        response = app.post(
            trash_url, data={"action": "purge_selected"}, headers=sysadmin_headers
        )
        assert "No entities selected" in response.body
        assert self.all_jobs() == []

    @pytest.mark.parametrize("ent_type", ["dataset", "group", "organization"])
    def test_trash_purge_all_is_queued(self, app, sysadmin_headers, ent_type):
        factory = ENT_TYPE_FACTORY[ent_type]
        factory(state="deleted")
        factory(state="deleted")
        factory()

        trash_url = url_for("admin.trash", ent_type=ent_type)
        response = app.post(
            trash_url, data={"action": "purge_all"}, headers=sysadmin_headers
        )
        assert "has been queued" in response.body
        assert len(self.all_jobs()) == 1

    def test_trash_cancel_purge(self, app, sysadmin_headers):
        """Cancelling purge doesn't purge anything."""
        factories.Organization(state="deleted")
        factories.Organization(state="deleted")

        orgs_before_purge = (
            model.Session.query(model.Group).filter_by(is_organization=True).count()
        )
        assert orgs_before_purge == 2

        trash_url = url_for("admin.trash", ent_type="organization")
        response = app.post(
            trash_url, data={"cancel": ""}, headers=sysadmin_headers, status=200
        )
        assert "Organizations have been purged" not in response

        orgs_after_purge = (
            model.Session.query(model.Group).filter_by(is_organization=True).count()
        )
        assert orgs_after_purge == 2
        assert self.all_jobs() == []

    def test_trash_page_shows_empty_purge_jobs_panel(self, app, sysadmin_headers):
        trash_url = url_for("admin.trash")
        response = app.get(trash_url, headers=sysadmin_headers, status=200)
        assert "No purge jobs yet." in response.body

    def test_trash_page_lists_queued_purge_job(self, app, sysadmin_headers):
        ds1 = factories.Dataset(state="deleted")
        ds2 = factories.Dataset(state="deleted")

        trash_url = url_for("admin.trash", ent_type="dataset")
        app.post(
            trash_url,
            data={
                "action": "purge_selected",
                "entity_id": [ds1["id"], ds2["id"]],
            },
            headers=sysadmin_headers,
        )

        response = app.get(trash_url, headers=sysadmin_headers, status=200)
        assert "Purge 2 dataset(s)" in response.body
        assert "queued" in response.body


@pytest.mark.usefixtures("clean_db")
class TestPurgeJobStatuses(helpers.RQTestBase):
    """Unit tests for the trash page's job-status panel data."""

    def test_purge_job_statuses_reports_queued_job(self):
        job = jobs.enqueue(
            admin_view.purge_entities_job,
            args=["dataset", []],
            title="Purge 0 dataset(s)",
            queue=admin_view._purge_queue_name(),
        )

        statuses = admin_view._purge_job_statuses()

        assert any(
            s["id"] == job.id and s["status"] == "queued" and s["title"] == job.meta["title"]
            for s in statuses
        )

    def test_purge_job_statuses_ignores_other_queues(self):
        jobs.enqueue(jobs.test_job, title="unrelated job")

        statuses = admin_view._purge_job_statuses()

        assert statuses == []


@pytest.mark.usefixtures("clean_db")
class TestPurgeEntitiesJob(object):
    """Unit tests for the background purge job itself, run inline (not
    via an RQ worker)."""

    def test_purge_entities_job_purges_given_ids(self):
        ds1 = factories.Dataset(state="deleted")
        ds2 = factories.Dataset(state="deleted")
        factories.Dataset()
        assert model.Session.query(model.Package).count() == 3

        admin_view.purge_entities_job("dataset", [ds1["id"], ds2["id"]])

        assert model.Session.query(model.Package).count() == 1

    def test_purge_entities_job_none_ids_purges_all_deleted(self):
        factories.Group(state="deleted")
        factories.Group(state="deleted")
        factories.Group()
        assert model.Session.query(model.Group).count() == 3

        admin_view.purge_entities_job("group", None)

        assert model.Session.query(model.Group).count() == 1

    def test_purge_entities_job_skips_missing_ids(self):
        ds = factories.Dataset(state="deleted")

        # one bad id should not prevent the good one from being purged
        admin_view.purge_entities_job("dataset", ["does-not-exist", ds["id"]])

        assert model.Session.query(model.Package).count() == 0


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
