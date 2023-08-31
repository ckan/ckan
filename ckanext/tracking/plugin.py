import click
import ckan.plugins as p

from typing import Any

from ckan import model
from ckan.plugins import toolkit
from ckan.types import Context, CKANApp
from ckan.common import CKANConfig

from .cli.tracking import tracking
from .middleware import TrackingMiddleware



class TrackingPlugin(p.SingletonPlugin):

    p.implements(p.IClick)
    p.implements(p.IConfigurer)
    p.implements(p.IMiddleware, inherit=True)
    p.implements(p.IPackageController, inherit=True)

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
    def after_dataset_show(self, context: Context, pkg_dict: "dict[str, Any]") -> "dict[str, Any]":
        tracking_summary = model.TrackingSummary.get_for_package(pkg_dict["id"])
        pkg_dict["tracking_summary"] = tracking_summary
        
        for resource_dict in pkg_dict['resources']:
            summary =  model.TrackingSummary.get_for_resource(
                resource_dict['url']
                )
            resource_dict['tracking_summary'] = summary      
        
        return pkg_dict    
    