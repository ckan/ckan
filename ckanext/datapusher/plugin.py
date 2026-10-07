# encoding: utf-8
from __future__ import annotations

from ckan.common import CKANConfig
from ckan.types import Action, AuthFunction, Context
import logging
from typing import Any, Callable, Union

import ckan.model as model
import ckan.plugins as p
import ckanext.datapusher.views as views
import ckanext.datapusher.helpers as helpers
import ckanext.datapusher.logic.action as action
import ckanext.datapusher.logic.auth as auth

from ckan.model.domain_object import DomainObjectOperation, Enum

log = logging.getLogger(__name__)


class DatastoreException(Exception):
    pass


@p.toolkit.blanket.config_declarations
class DatapusherPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IDomainObjectModification)
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

    # IDomainObjectModification

    def notify(self, entity: Union[model.Resource, model.Package],
               operation: Enum[str]):
        """
        Runs before_commit to database for Packages and Resources.
        We only want to check for changed Resources for this.
        We want to check if values have changed, namely the url.
        See: ckan/model/modification.py.DomainObjectModificationExtension
        """
        if operation != DomainObjectOperation.changed \
           or not isinstance(entity, model.Resource):
            return

        # If the resource requires validation, stop here if validation
        # has not been performed or did not succeed. The Validation
        # extension will call resource_patch and this method should
        # be called again. However, url_changed will not be in the entity
        # once Validation does the patch.
        if _is_validation_plugin_loaded() and \
           p.toolkit.asbool(p.toolkit.config.get(
                                'ckan.datapusher.requires_validation')):
            if entity.__dict__.get(
               'extras', {}).get('validation_status', None) != 'success':
                log.debug('Skipping DataPusher submission for '
                          'resource %s because resource has not '
                          'passed validation yet.', entity.id)
                return
        elif not getattr(entity, 'url_changed', False):
            return

        context: Context = {'ignore_auth': True}
        resource_dict = p.toolkit.get_action(u'resource_show')(
            context, {
                u'id': entity.id,
            }
        )
        self._submit_to_datapusher(resource_dict)

    # IResourceController

    def after_resource_create(
            self, context: Context, resource_dict: dict[str, Any]):

        if _is_validation_plugin_loaded() and \
           p.toolkit.asbool(p.toolkit.config.get(
                                'ckan.datapusher.requires_validation')) and \
           resource_dict.get('validation_status', None) != 'success':
            log.debug('Skipping DataPusher submission for '
                      'resource %s because resource has not '
                      'passed validation yet.', resource_dict.get('id'))
            return
        self._submit_to_datapusher(resource_dict)

    def after_resource_update(
            self, context: Context, resource_dict: dict[str, Any]):

        if _is_validation_plugin_loaded() and \
           p.toolkit.asbool(p.toolkit.config.get(
                                'ckan.datapusher.requires_validation')) and \
           resource_dict.get('validation_status', None) != 'success':
            log.debug('Skipping DataPusher submission for '
                      'resource %s because resource has not '
                      'passed validation yet.', resource_dict.get('id'))
            return
        self._submit_to_datapusher(resource_dict)

    def _submit_to_datapusher(self, resource_dict: dict[str, Any]):
        context: Context = {
            u'ignore_auth': True,
            u'defer_commit': True
        }

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
                    'Skipping DataPusher submission for resource %s',
                    resource_dict['id'],
                )
                return
        except p.toolkit.ObjectNotFound:
            pass

        try:
            log.debug(
                'Submitting resource %s to DataPusher',
                resource_dict['id'],
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


def _is_validation_plugin_loaded():
    """
    Checks the existance of a logic action from the ckanext-validation
    plugin, thus supporting any extending of the Validation Plugin class.
    """
    try:
        p.toolkit.get_action('resource_validation_show')
    except KeyError:
        return False
    return True
