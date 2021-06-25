# encoding: utf-8

import csv
import datetime
from io import StringIO
import pytest
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as plugins
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.tests.factories as factories
from ckan.tests.helpers import call_action


@pytest.mark.ckan_config(
    "ckan.plugins", "test_resource_preview test_json_resource_preview"
)
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
class TestPluggablePreviews:
    def test_hook(self, app):
        res = factories.Resource()
        plugin = plugins.get_plugin("test_resource_preview")
        plugin.calls.clear()
        url = h.url_for(
            "resource.datapreview", id=res["package_id"], resource_id=res["id"]
        )
        result = app.get(url, status=409)
        assert "No preview" in result

        # no preview for type "ümlaut", should not fail
        res["format"] = u"ümlaut"
        call_action("resource_update", **res)
        result = app.get(url, status=409)
        assert "No preview" in result

        res["format"] = "mock"
        call_action("resource_update", **res)

        result = app.get(url, status=200)

        assert "mock-preview" in result
        assert "mock-preview.js" in result

        assert plugin.calls["can_preview"] == 3
        assert plugin.calls["setup_template_variables"] == 1
        assert plugin.calls["preview_templates"] == 1

        result = app.get(
            h.url_for(
                "resource.read", id=res["package_id"], resource_id=res["id"]
            )
        )
        assert 'data-module="data-viewer"' in result
        assert "<iframe" in result
        assert url in result


@pytest.fixture
def export(tmp_path):
    """Export CKAN's tracking data and return it.

    This simulates calling `paster tracking export` on the command line.

    """
    # FIXME: Can this be done as more of a functional test where we
    # actually test calling the command and passing the args? By calling
    # the method directly, we're not testing the command-line parsing.
    from ckan.cli.tracking import export_tracking
    import ckan.model

    path = tmp_path / "report.csv"

    def exporter():
        export_tracking(engine=ckan.model.meta.engine, output_filename=path)

        return list(csv.DictReader(path.open("r")))

    return exporter


@pytest.fixture
def track(app):
    """Post some data to /_tracking directly.

    This simulates what's supposed when you view a page with tracking
    enabled (an ajax request posts to /_tracking).

    """

    def func(url, type_="page", ip="199.204.138.90", browser="firefox"):
        params = {"url": url, "type": type_}
        extra_environ = {
            # The tracking middleware crashes if these aren't present.
            "HTTP_USER_AGENT": browser,
            "REMOTE_ADDR": ip,
            "HTTP_ACCEPT_LANGUAGE": "en",
            "HTTP_ACCEPT_ENCODING": "gzip, deflate",
        }
        app.post("/_tracking", params=params, extra_environ=extra_environ)

    return func


def update_tracking_summary():
    """Update CKAN's tracking summary data.

    This simulates calling `paster tracking update` on the command line.

    """
    # FIXME: Can this be done as more of a functional test where we
    # actually test calling the command and passing the args? By calling
    # the method directly, we're not testing the command-line parsing.
    import ckan.cli.tracking as tracking
    import ckan.model

    date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime(
        "%Y-%m-%d"
    )
    tracking.update_all(engine=ckan.model.meta.engine, start_date=date)


@pytest.mark.usefixtures("clean_db")
class TestTracking(object):
    def test_package_with_0_views(self, app):
        package = factories.Dataset()

        # The API should return 0 recent views and 0 total views for the
        # unviewed package.
        package = call_action(
            "package_show", id=package["name"], include_tracking=True
        )
        tracking_summary = package["tracking_summary"]
        assert tracking_summary["recent"] == 0, (
            "A package that has not "
            "been viewed should have 0 "
            "recent views"
        )
        assert tracking_summary["total"] == 0, (
            "A package that has not "
            "been viewed should have 0 "
            "total views"
        )

    def test_resource_with_0_views(self, app):
        package = factories.Dataset()
        resource = factories.Resource(package_id=package["id"])

        # The package_show() API should return 0 recent views and 0 total
        # views for the unviewed resource.
        package = call_action(
            "package_show", id=package["name"], include_tracking=True
        )
        assert len(package["resources"]) == 1
        resource = package["resources"][0]
        tracking_summary = resource["tracking_summary"]
        assert tracking_summary["recent"] == 0, (
            "A resource that has not "
            "been viewed should have 0 "
            "recent views"
        )
        assert tracking_summary["total"] == 0, (
            "A resource that has not "
            "been viewed should have 0 "
            "total views"
        )

        # The resource_show() API should return 0 recent views and 0 total
        # views for the unviewed resource.
        resource = call_action(
            "resource_show", id=resource["id"], include_tracking=True
        )
        tracking_summary = resource["tracking_summary"]
        assert tracking_summary["recent"] == 0, (
            "A resource that has not "
            "been viewed should have 0 "
            "recent views"
        )
        assert tracking_summary["total"] == 0, (
            "A resource that has not "
            "been viewed should have 0 "
            "total views"
        )

    def test_package_with_one_view(self, app, track):
        package = factories.Dataset()
        resource = factories.Resource(package_id=package["id"])

        url = h.url_for("dataset.read", id=package["name"])
        track(url)

        update_tracking_summary()

        package = call_action(
            "package_show", id=package["name"], include_tracking=True
        )
        tracking_summary = package["tracking_summary"]
        assert tracking_summary["recent"] == 1, (
            "A package that has been "
            "viewed once should have 1 "
            "recent view."
        )
        assert tracking_summary["total"] == 1, (
            "A package that has been "
            "viewed once should have 1 "
            "total view"
        )

        assert len(package["resources"]) == 1
        resource = package["resources"][0]
        tracking_summary = resource["tracking_summary"]
        assert tracking_summary["recent"] == 0, (
            "Viewing a package should "
            "not increase the recent "
            "views of the package's "
            "resources"
        )
        assert tracking_summary["total"] == 0, (
            "Viewing a package should "
            "not increase the total views "
            "of the package's resources"
        )

    def test_resource_with_one_preview(self, app, track):
        package = factories.Dataset()
        resource = factories.Resource(package_id=package["id"])
        url = h.url_for(
            "resource.read", id=package["name"], resource_id=resource["id"]
        )
        track(url)

        update_tracking_summary()

        package = call_action(
            "package_show", id=package["name"], include_tracking=True
        )
        assert len(package["resources"]) == 1
        resource = package["resources"][0]

        assert package["tracking_summary"]["recent"] == 0, (
            "Previewing a "
            "resource should "
            "not increase the "
            "package's recent "
            "views"
        )
        assert package["tracking_summary"]["total"] == 0, (
            "Previewing a "
            "resource should "
            "not increase the "
            "package's total "
            "views"
        )
        # Yes, previewing a resource does _not_ increase its view count.
        assert resource["tracking_summary"]["recent"] == 0, (
            "Previewing a "
            "resource should "
            "not increase "
            "the resource's "
            "recent views"
        )
        assert resource["tracking_summary"]["total"] == 0, (
            "Previewing a "
            "resource should "
            "not increase the "
            "resource's "
            "recent views"
        )

    def test_resource_with_one_download(self, app, track):
        package = factories.Dataset()
        resource = factories.Resource(package_id=package["id"])

        track(resource["url"], type_="resource")
        update_tracking_summary()
        package = call_action(
            "package_show", id=package["name"], include_tracking=True
        )
        assert len(package["resources"]) == 1
        resource = package["resources"][0]
        assert package["tracking_summary"]["recent"] == 0, (
            "Downloading a resource should not increase the package's recent "
            "views"
        )
        assert package["tracking_summary"]["total"] == 0, (
            "Downloading a resource should not increase the package's total "
            "views"
        )
        assert resource["tracking_summary"]["recent"] == 1, (
            "Downloading a resource should increase the resource's recent "
            "views"
        )
        assert resource["tracking_summary"]["total"] == 1, (
            "Downloading a resource should increase the resource's total "
            "views"
        )

        # The resource_show() API should return the same result.
        resource = call_action(
            "resource_show", id=resource["id"], include_tracking=True
        )
        tracking_summary = resource["tracking_summary"]
        assert tracking_summary["recent"] == 1, (
            "Downloading a resource should increase the resource's recent "
            "views"
        )
        assert tracking_summary["total"] == 1, (
            "Downloading a resource should increase the resource's total "
            "views"
        )

    def test_view_page(self, app, track):
        # Visit the front page.
        track(url="", type_="page")
        # Visit the /organization page.
        track(url="/organization", type_="page")
        # Visit the /about page.
        track(url="/about", type_="page")

        update_tracking_summary()
        # There's no way to export page-view (as opposed to resource or
        # dataset) tracking summaries, eg. via the api or a paster command, the
        # only way we can check them is through the model directly.
        import ckan.model as model

        for url in ("", "/organization", "/about"):
            q = model.Session.query(model.TrackingSummary)
            q = q.filter_by(url=url)
            tracking_summary = q.one()
            assert tracking_summary.count == 1, (
                "Viewing a page should " "increase the page's view " "count"
            )
            # For pages (as opposed to datasets and resources) recent_views and
            # running_total always stay at 1. Shrug.
            assert (
                tracking_summary.recent_views == 0
            ), "recent_views for a page is always 0"
            assert (
                tracking_summary.running_total == 0
            ), "running_total for a page is always 0"

    def test_package_with_many_views(self, app, track):
        package = factories.Dataset()
        resource = factories.Resource(package_id=package["id"])
        url = h.url_for("dataset.read", id=package["name"])

        # View the package three times from different IPs.
        track(url, ip="111.222.333.44")
        track(url, ip="111.222.333.55")
        track(url, ip="111.222.333.66")

        update_tracking_summary()

        package = call_action(
            "package_show", id=package["name"], include_tracking=True
        )
        tracking_summary = package["tracking_summary"]
        assert tracking_summary["recent"] == 3, (
            "A package that has been viewed 3 times recently should have 3 "
            "recent views"
        )
        assert (
            tracking_summary["total"] == 3
        ), "A package that has been viewed 3 times should have 3 total views"

        assert len(package["resources"]) == 1
        resource = package["resources"][0]
        tracking_summary = resource["tracking_summary"]
        assert tracking_summary["recent"] == 0, (
            "Viewing a package should not increase the recent views of the "
            "package's resources"
        )
        assert tracking_summary["total"] == 0, (
            "Viewing a package should not increase the total views of the "
            "package's resources"
        )

    def test_resource_with_many_downloads(self, app, track):
        package = factories.Dataset()
        resource = factories.Resource(package_id=package["id"])
        url = resource["url"]

        # Download the resource three times from different IPs.
        track(url, type_="resource", ip="111.222.333.44")
        track(url, type_="resource", ip="111.222.333.55")
        track(url, type_="resource", ip="111.222.333.66")

        update_tracking_summary()

        package = call_action(
            "package_show", id=package["name"], include_tracking=True
        )

        assert len(package["resources"]) == 1
        resource = package["resources"][0]
        tracking_summary = resource["tracking_summary"]
        assert tracking_summary["recent"] == 3, (
            "A resource that has been downloaded 3 times recently should have "
            "3 recent downloads"
        )
        assert tracking_summary["total"] == 3, (
            "A resource that has been downloaded 3 times should have 3 total "
            "downloads"
        )

        tracking_summary = package["tracking_summary"]
        assert tracking_summary["recent"] == 0, (
            "Downloading a resource should not increase the resource's "
            "package's recent views"
        )
        assert tracking_summary["total"] == 0, (
            "Downloading a resource should not increase the resource's "
            "package's total views"
        )

    def test_page_with_many_views(self, app, track):

        # View each page three times, from three different IPs.
        for ip in ("111.111.11.111", "222.222.22.222", "333.333.33.333"):
            # Visit the front page.
            track(url="", type_="page", ip=ip)
            # Visit the /organization page.
            track(url="/organization", type_="page", ip=ip)
            # Visit the /about page.
            track(url="/about", type_="page", ip=ip)

        update_tracking_summary()

        # There's no way to export page-view (as opposed to resource or
        # dataset) tracking summaries, eg. via the api or a paster command, the
        # only way we can check them if through the model directly.
        import ckan.model as model

        for url in ("", "/organization", "/about"):
            q = model.Session.query(model.TrackingSummary)
            q = q.filter_by(url=url)
            tracking_summary = q.one()
            assert tracking_summary.count == 3, (
                "A page that has been viewed three times should have view "
                "count 3"
            )
            # For pages (as opposed to datasets and resources) recent_views and
            # running_total always stay at 1. Shrug.
            assert tracking_summary.recent_views == 0, (
                "recent_views for " "pages is always 0"
            )
            assert tracking_summary.running_total == 0, (
                "running_total for " "pages is always 0"
            )

    def test_dataset_view_count_throttling(self, app, track):
        """If the same user visits the same dataset multiple times on the same
        day, only one view should get counted.

        """
        package = factories.Dataset()
        resource = factories.Resource(package_id=package["id"])
        url = h.url_for("dataset.read", id=package["name"])

        # Visit the dataset three times from the same IP.
        track(url)
        track(url)
        track(url)

        update_tracking_summary()

        package = call_action(
            "package_show", id=package["name"], include_tracking=True
        )

        tracking_summary = package["tracking_summary"]
        assert tracking_summary["recent"] == 1, (
            "Repeat dataset views should " "not add to recent views " "count"
        )
        assert tracking_summary["total"] == 1, (
            "Repeat dataset views should " "not add to total views count"
        )

    def test_resource_download_count_throttling(self, app, track):
        """If the same user downloads the same resource multiple times on the
        same day, only one view should get counted.

        """
        package = factories.Dataset()
        resource = factories.Resource(package_id=package["id"])

        # Download the resource three times from the same IP.
        track(resource["url"], type_="resource")
        track(resource["url"], type_="resource")
        track(resource["url"], type_="resource")

        update_tracking_summary()

        resource = call_action(
            "resource_show", id=resource["id"], include_tracking=True
        )
        tracking_summary = resource["tracking_summary"]
        assert (
            tracking_summary["recent"] == 1
        ), "Repeat resource downloads should not add to recent views count"
        assert (
            tracking_summary["total"] == 1
        ), "Repeat resource downloads should not add to total views count"

    @pytest.mark.usefixtures("clean_index")
    def test_sorting_datasets_by_recent_views(self, app, reset_index, track):
        # FIXME: Have some datasets with different numbers of recent and total
        # views, to make this a better test.
        factories.Dataset(name="consider_phlebas")
        factories.Dataset(name="the_player_of_games")
        factories.Dataset(name="use_of_weapons")

        url = h.url_for("dataset.read", id="consider_phlebas")
        track(url)

        url = h.url_for("dataset.read", id="the_player_of_games")
        track(url, ip="111.11.111.111")
        track(url, ip="222.22.222.222")

        url = h.url_for("dataset.read", id="use_of_weapons")
        track(url, ip="111.11.111.111")
        track(url, ip="222.22.222.222")
        track(url, ip="333.33.333.333")

        update_tracking_summary()

        response = call_action("package_search", sort="views_recent desc")
        assert response["count"] == 3
        assert response["sort"] == "views_recent desc"
        packages = response["results"]
        assert packages[0]["name"] == "use_of_weapons"
        assert packages[1]["name"] == "the_player_of_games"
        assert packages[2]["name"] == "consider_phlebas"

    @pytest.mark.usefixtures("clean_index")
    def test_sorting_datasets_by_total_views(self, app, track):
        # FIXME: Have some datasets with different numbers of recent and total
        # views, to make this a better test.
        factories.Dataset(name="consider_phlebas")
        factories.Dataset(name="the_player_of_games")
        factories.Dataset(name="use_of_weapons")

        url = h.url_for("dataset.read", id="consider_phlebas")
        track(url)

        url = h.url_for("dataset.read", id="the_player_of_games")
        track(url, ip="111.11.111.111")
        track(url, ip="222.22.222.222")

        url = h.url_for("dataset.read", id="use_of_weapons")
        track(url, ip="111.11.111.111")
        track(url, ip="222.22.222.222")
        track(url, ip="333.33.333.333")

        update_tracking_summary()

        response = call_action("package_search", sort="views_total desc")
        assert response["count"] == 3
        assert response["sort"] == "views_total desc"
        packages = response["results"]
        assert packages[0]["name"] == "use_of_weapons"
        assert packages[1]["name"] == "the_player_of_games"
        assert packages[2]["name"] == "consider_phlebas"

    def test_export(self, app, track, export):
        """`paster tracking export` should export tracking data for all
        datasets in CSV format.

        Only dataset tracking data is output to CSV file, not resource or page
        views.

        """
        admin = factories.Sysadmin()

        package_1 = factories.Dataset(user=admin)
        package_2 = factories.Dataset(user=admin, name="another_package")

        # View the package_1 three times from different IPs.
        url = h.url_for("dataset.read", id=package_1["name"])
        track(url, ip="111.222.333.44")
        track(url, ip="111.222.333.55")
        track(url, ip="111.222.333.66")

        # View the package_2 twice from different IPs.
        url = h.url_for("dataset.read", id=package_2["name"])
        track(url, ip="111.222.333.44")
        track(url, ip="111.222.333.55")

        update_tracking_summary()
        lines = export()

        assert len(lines) == 2
        package_1_data = lines[0]
        assert package_1_data["total views"] == "3"
        assert package_1_data["recent views (last 2 weeks)"] == "3"
        package_2_data = lines[1]
        assert package_2_data["total views"] == "2"
        assert package_2_data["recent views (last 2 weeks)"] == "2"
