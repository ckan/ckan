# encoding: utf-8
from __future__ import annotations

from ckan.common import CKANConfig
from ckan.types import Action, AuthFunction, Context
import logging
from typing import Any, Callable, cast

import ckan.model as model
import ckan.plugins as p
import ckanext.datapusher.views as views
import ckanext.datapusher.helpers as helpers
import ckanext.datapusher.logic.action as action
import ckanext.datapusher.logic.auth as auth

log = logging.getLogger(__name__)


class DatastoreException(Exception):
    pass


@p.toolkit.blanket.config_declarations
class DatapusherPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IResourceUrlChange)
    p.implements(p.IResourceController, inherit=True)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IBlueprint)

    legacy_mode = False
    resource_show_action = None

    def update_config(self, config: CKANConfig):
        templates_base = config.get(u'ckan.base_templates_folder')
        p.toolkit.add_template_directory(config, templates_base)
        p.toolkit.add_public_directory(config, 'public')
        p.toolkit.add_resource('assets', 'ckanext-datapusher')

    def configure(self, config: CKANConfig):
        self.config = config

        for config_option in (
            "ckan.site_url",
            "ckan.datapusher.url",
            "ckan.datapusher.api_token",
        ):
            if not config.get(config_option):
                raise Exception(
                    u'Config option `{0}` must be set to use the DataPusher.'.
                    format(config_option)
                )

    # IResourceUrlChange

    def notify(self, resource: model.Resource):
        context = cast(Context, {
            u'model': model,
            u'ignore_auth': True,
        })
        resource_dict = p.toolkit.get_action(u'resource_show')(
            context, {
                u'id': resource.id,
            }
        )
        self._submit_to_datapusher(resource_dict)

    # IResourceController

    def after_resource_create(
            self, context: Context, resource_dict: dict[str, Any]):

        self._submit_to_datapusher(resource_dict)

    def after_update(
            self, context: Context, resource_dict: dict[str, Any]):

        self._submit_to_datapusher(resource_dict)

    def _submit_to_datapusher(self, resource_dict: dict[str, Any]):
        context = cast(Context, {
            u'model': model,
            u'ignore_auth': True,
            u'defer_commit': True
        })

        resource_format = resource_dict.get('format')
        supported_formats = p.toolkit.config.get(
            'ckan.datapusher.formats'
        )

        submit = (
            resource_format
            and resource_format.lower() in supported_formats
            and resource_dict.get('url_type') != u'datapusher'
        )

        if not submit:
            return

        try:
            task = p.toolkit.get_action(u'task_status_show')(
                context, {
                    u'entity_id': resource_dict['id'],
                    u'task_type': u'datapusher',
                    u'key': u'datapusher'
                }
            )

            if task.get(u'state') in (u'pending', u'submitting'):
                # There already is a pending DataPusher submission,
                # skip this one ...
                log.debug(
                    u'Skipping DataPusher submission for '
                    u'resource {0}'.format(resource_dict['id'])
                )
                return
        except p.toolkit.ObjectNotFound:
            pass

        try:
            log.debug(
                u'Submitting resource {0}'.format(resource_dict['id']) +
                u' to DataPusher'
            )
            p.toolkit.get_action(u'datapusher_submit')(
                context, {
                    u'resource_id': resource_dict['id']
                }
            )
        except p.toolkit.ValidationError as e:
            # If datapusher is offline want to catch error instead
            # of raising otherwise resource save will fail with 500
            log.critical(e)
            pass

    def get_actions(self) -> dict[str, Action]:
        return {
            u'datapusher_submit': action.datapusher_submit,
            u'datapusher_hook': action.datapusher_hook,
            u'datapusher_status': action.datapusher_status
        }

    def get_auth_functions(self) -> dict[str, AuthFunction]:
        return {
            u'datapusher_submit': auth.datapusher_submit,
            u'datapusher_status': auth.datapusher_status
        }

    def get_helpers(self) -> dict[str, Callable[..., Any]]:
        return {
            u'datapusher_status': helpers.datapusher_status,
            u'datapusher_status_description': helpers.
            datapusher_status_description,
        }

    # IBlueprint

    def get_blueprint(self):
        return views.get_blueprints()
