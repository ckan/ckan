import click
import ckan.plugins as p

from typing import Any, Callable

from ckan.plugins import toolkit
from ckan.types import Context, CKANApp
from ckan.common import CKANConfig

from .cli.tracking import tracking
from .helpers import popular
from .middleware import TrackingMiddleware
from .model import TrackingSummary


class TrackingPlugin(p.SingletonPlugin):
    p.implements(p.IClick)
    p.implements(p.IConfigurer)
    p.implements(p.IMiddleware, inherit=True)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.ITemplateHelpers)

    # IClick
    def get_commands(self) -> "list[click.Command]":
        return [tracking]

    # IConfigurer
    def update_config(self, config: CKANConfig) -> None:
        toolkit.add_resource("assets", "tracking")
        toolkit.add_template_directory(config, "templates")

    # IMiddleware
    def make_middleware(self, app: CKANApp, config: CKANConfig) -> Any:
        app = TrackingMiddleware(app, config)
        return app

    # IPackageController
    def after_dataset_show(
            self,
            context: Context,
            pkg_dict: "dict[str, Any]"
            ) -> "dict[str, Any]":
        """Appends tracking summary data to the package dict.

        Tracking data is not stored in Solr so we need to retrieve it
        from the database.
        """
        tracking_summary = TrackingSummary.get_for_package(
            pkg_dict["id"]
            )
        pkg_dict["tracking_summary"] = tracking_summary

        for resource_dict in pkg_dict['resources']:
            summary = TrackingSummary.get_for_resource(
                resource_dict['url']
                )
            resource_dict['tracking_summary'] = summary

        return pkg_dict

    def after_dataset_search(
            self,
            search_results: "dict[str, Any]",
            search_params: "dict[str, Any]"
            ) -> "dict[str, Any]":
        """Add tracking summary to search results.

        Tracking data is indexed but not stored in Solr so we need to
        fetch it from the database. This can cause some discrepancies since
        the number of views when indexing might have been different than
        when this code is run.
        """
        for package_dict in search_results["results"]:
            tracking_summary = TrackingSummary.get_for_package(
                package_dict["id"]
                )
            package_dict["tracking_summary"] = tracking_summary
            for resource_dict in package_dict['resources']:
                summary = TrackingSummary.get_for_resource(
                    resource_dict['url']
                    )
                resource_dict['tracking_summary'] = summary
        return search_results

    def before_dataset_index(
            self, pkg_dict: "dict[str, Any]"
            ) -> "dict[str, Any]":
        """ Index tracking information.

        This method will index (but not store) the tracking information of the
        dataset. This will only allow us to sort Solr's queries by views. For
        the actual data we will query the database after the search.

        It will also remove the tracking_summary key from the package dict since
        it is not a valid Solr field.
        """
        pkg_dict.pop("tracking_summary", None)
        for r in pkg_dict.get('resources', []):
            r.pop('tracking_summary', None)

        tracking_summary = TrackingSummary.get_for_package(
            pkg_dict["id"]
            )
        pkg_dict['views_total'] = tracking_summary['total']
        pkg_dict['views_recent'] = tracking_summary['recent']
        return pkg_dict

    # ITemplateHelpers
    def get_helpers(self) -> "dict[str, Callable[...,Any]]":
        return {
            "popular": popular,
        }
