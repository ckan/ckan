# encoding: utf-8

import logging

import ckan.logic as logic
import ckan.model as model
import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
import ckanext.datapusher.views as views
import ckanext.datapusher.helpers as helpers
import ckanext.datapusher.logic.action as action
import ckanext.datapusher.logic.auth as auth

log = logging.getLogger(__name__)
_get_or_bust = logic.get_or_bust

DEFAULT_FORMATS = [
    'csv',
    'xls',
    'xlsx',
    'tsv',
    'application/csv',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'ods',
    'application/vnd.oasis.opendocument.spreadsheet',
]


class DatastoreException(Exception):
    pass


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

    def update_config(self, config):
        templates_base = config.get('ckan.base_templates_folder')
        toolkit.add_template_directory(config, templates_base)

    def configure(self, config):
        self.config = config

        datapusher_formats = config.get('ckan.datapusher.formats',
                                        '').lower()
        self.datapusher_formats = datapusher_formats.split() or DEFAULT_FORMATS

        for config_option in (
            'ckan.site_url',
            'ckan.datapusher.url',
        ):
            if not config.get(config_option):
                raise Exception(
                    'Config option `{0}` must be set to use the DataPusher.'.
                    format(config_option)
                )

    # IResourceUrlChange

    def notify(self, resource):
        context = {
            'model': model,
            'ignore_auth': True,
        }
        resource_dict = toolkit.get_action('resource_show')(
            context, {
                'id': resource.id,
            }
        )
        self._submit_to_datapusher(resource_dict)

    # IResourceController

    def after_create(self, context, resource_dict):

        self._submit_to_datapusher(resource_dict)

    def _submit_to_datapusher(self, resource_dict):
        context = {
            'model': model,
            'ignore_auth': True,
            'defer_commit': True
        }

        resource_format = resource_dict.get('format')

        submit = (
            resource_format
            and resource_format.lower() in self.datapusher_formats
            and resource_dict.get('url_type') != 'datapusher'
        )

        if not submit:
            return

        try:
            task = toolkit.get_action('task_status_show')(
                context, {
                    'entity_id': resource_dict['id'],
                    'task_type': 'datapusher',
                    'key': 'datapusher'
                }
            )

            if task.get('state') in ('pending', 'submitting'):
                # There already is a pending DataPusher submission,
                # skip this one ...
                log.debug(
                    'Skipping DataPusher submission for '
                    'resource {0}'.format(resource_dict['id'])
                )
                return
        except toolkit.ObjectNotFound:
            pass

        try:
            log.debug(
                'Submitting resource {0}'.format(resource_dict['id']) +
                ' to DataPusher'
            )
            toolkit.get_action('datapusher_submit')(
                context, {
                    'resource_id': resource_dict['id']
                }
            )
        except toolkit.ValidationError as e:
            # If datapusher is offline want to catch error instead
            # of raising otherwise resource save will fail with 500
            log.critical(e)
            pass

    def get_actions(self):
        return {
            'datapusher_submit': action.datapusher_submit,
            'datapusher_hook': action.datapusher_hook,
            'datapusher_status': action.datapusher_status
        }

    def get_auth_functions(self):
        return {
            'datapusher_submit': auth.datapusher_submit,
            'datapusher_status': auth.datapusher_status
        }

    def get_helpers(self):
        return {
            'datapusher_status': helpers.datapusher_status,
            'datapusher_status_description': helpers.
            datapusher_status_description,
        }

    # IBlueprint

    def get_blueprint(self):
        return views.get_blueprints()
