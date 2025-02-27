# encoding: utf-8

from __future__ import annotations

from typing import Any, Optional, Literal
from ckan.common import CKANConfig

from ckan.plugins.toolkit import add_template_directory, h
from ckan import plugins

from ckanext.example_iformredirect import views


class ExampleIFormRedirectPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IFormRedirect)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IConfigurer)

    # IConfigurer

    def update_config(self, config: CKANConfig):
        add_template_directory(config, 'templates')

    # IBlueprint

    def get_blueprint(self):
        return [views.resource_first]

    # IFormRedirect

    def dataset_save_redirect(
            self, package_type: str, package_name: str,
            action: Literal['create', 'edit'], save_action: Optional[str],
            data: dict[str, Any],
            ) -> Optional[str]:
        # done after dataset metadata
        return h.url_for(f'{package_type}.read', id=package_name)

    def resource_save_redirect(
            self, package_type: str, package_name: str, resource_id: Optional[str],
            action: Literal['create', 'edit'], save_action: str,
            data: dict[str, Any],
            ) -> Optional[str]:
        if action == 'edit':
            return h.url_for(
                f'{package_type}_resource.read',
                id=package_name, resource_id=resource_id
            )
        if save_action == 'again':
            return h.url_for(
                '{}_resource.new'.format(package_type), id=package_name,
            )
        # edit dataset page after resource
        return h.url_for(u'{}.edit'.format(package_type), id=package_name)
