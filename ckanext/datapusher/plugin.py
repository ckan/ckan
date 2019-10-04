# encoding: utf-8

import logging

import ckan.logic as logic
import ckan.model as model
import ckan.plugins as p
import ckan.plugins.toolkit as toolkit
import ckanext.datapusher.blueprint as blueprint
import ckanext.datapusher.helpers as helpers
import ckanext.datapusher.logic.action as action
import ckanext.datapusher.logic.auth as auth

log = logging.getLogger(__name__)
_get_or_bust = logic.get_or_bust

DEFAULT_FORMATS = [
    u'csv',
    u'xls',
    u'xlsx',
    u'tsv',
    u'application/csv',
    u'application/vnd.ms-excel',
    u'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    u'ods',
    u'application/vnd.oasis.opendocument.spreadsheet',
]


class DatastoreException(Exception):
    pass


class DatapusherPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IResourceUrlChange)
    p.implements(p.IDomainObjectModification, inherit=True)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IBlueprint)

    legacy_mode = False
    resource_show_action = None

    def update_config(self, config):
        templates_base = config.get(u'ckan.base_templates_folder')
        toolkit.add_template_directory(config, templates_base)

    def configure(self, config):
        self.config = config

        datapusher_formats = config.get(u'ckan.datapusher.formats',
                                        u'').lower()
        self.datapusher_formats = datapusher_formats.split() or DEFAULT_FORMATS

        for config_option in (
            u'ckan.site_url',
            u'ckan.datapusher.url',
        ):
            if not config.get(config_option):
                raise Exception(
                    u'Config option `{0}` must be set to use the DataPusher.'.
                    format(config_option)
                )

    def notify(self, entity, operation=None):
        if isinstance(entity, model.Resource):
            if (
                operation == model.domain_object.DomainObjectOperation.new
                or not operation
            ):
                # if operation is None, resource URL has been changed, as
                # the notify function in IResourceUrlChange only takes
                # 1 parameter
                context = {
                    u'model': model,
                    u'ignore_auth': True,
                    u'defer_commit': True
                }
                if (
                    entity.format
                    and entity.format.lower() in self.datapusher_formats
                    and entity.url_type != u'datapusher'
                ):

                    try:
                        task = toolkit.get_action(u'task_status_show')(
                            context, {
                                u'entity_id': entity.id,
                                u'task_type': u'datapusher',
                                u'key': u'datapusher'
                            }
                        )
                        if task.get(u'state') == u'pending':
                            # There already is a pending DataPusher submission,
                            # skip this one ...
                            log.debug(
                                u'Skipping DataPusher submission for '
                                u'resource {0}'.format(entity.id)
                            )
                            return
                    except toolkit.ObjectNotFound:
                        pass

                    try:
                        log.debug(
                            u'Submitting resource {0}'.format(entity.id) +
                            u' to DataPusher'
                        )
                        toolkit.get_action(u'datapusher_submit')(
                            context, {
                                u'resource_id': entity.id
                            }
                        )
                    except toolkit.ValidationError as e:
                        # If datapusher is offline want to catch error instead
                        # of raising otherwise resource save will fail with 500
                        log.critical(e)
                        pass

    def get_actions(self):
        return {
            u'datapusher_submit': action.datapusher_submit,
            u'datapusher_hook': action.datapusher_hook,
            u'datapusher_status': action.datapusher_status
        }

    def get_auth_functions(self):
        return {
            u'datapusher_submit': auth.datapusher_submit,
            u'datapusher_status': auth.datapusher_status
        }

    def get_helpers(self):
        return {
            u'datapusher_status': helpers.datapusher_status,
            u'datapusher_status_description': helpers.
            datapusher_status_description,
        }

    # IBlueprint

    def get_blueprint(self):
        return blueprint.datapusher
