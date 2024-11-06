# encoding: utf-8

import logging

from ckan import plugins
from ckan.plugins import toolkit

from ckan.model.domain_object import DomainObjectOperation
from ckan.model.resource import Resource
from ckan.model.package import Package

from . import action, auth, helpers as xloader_helpers, utils
from ckanext.xloader.utils import XLoaderFormats

try:
    config_declarations = toolkit.blanket.config_declarations
except AttributeError:
    # CKAN 2.9 does not have config_declarations.
    # Remove when dropping support.
    def config_declarations(cls):
        return cls

log = logging.getLogger(__name__)


@config_declarations
class xloaderPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IDomainObjectModification)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.IClick)
    plugins.implements(plugins.IBlueprint)

    # IClick
    def get_commands(self):
        from ckanext.xloader.cli import get_commands

        return get_commands()

    # IBlueprint
    def get_blueprint(self):
        from ckanext.xloader.views import get_blueprints

        return get_blueprints()

    # IConfigurer

    def update_config(self, config):
        toolkit.add_template_directory(config, 'templates')
        toolkit.add_resource(u'webassets', 'ckanext-xloader')

    # IConfigurable

    def configure(self, config_):
        if config_.get("ckanext.xloader.ignore_hash") in ["True", "TRUE", "1", True, 1]:
            self.ignore_hash = True
        else:
            self.ignore_hash = False

        for config_option in ("ckan.site_url",):
            if not config_.get(config_option):
                raise Exception(
                    "Config option `{0}` must be set to use ckanext-xloader.".format(
                        config_option
                    )
                )

    # IDomainObjectModification

    def notify(self, entity, operation):
        # type: (Package|Resource, DomainObjectOperation) -> None
        """
        Runs before_commit to database for Packages and Resources.
        We only want to check for changed Resources for this.
        We want to check if values have changed, namely the url and the format.
        See: ckan/model/modification.py.DomainObjectModificationExtension
        """
        if operation != DomainObjectOperation.changed \
                or not isinstance(entity, Resource):
            return

        context = {
            "ignore_auth": True,
        }
        resource_dict = toolkit.get_action("resource_show")(
            context,
            {
                "id": entity.id,
            },
        )

        if _should_remove_unsupported_resource_from_datastore(resource_dict):
            toolkit.enqueue_job(fn=_remove_unsupported_resource_from_datastore, args=[entity.id])

        if not getattr(entity, 'url_changed', False):
            # do not submit to xloader if the url has not changed.
            return

        self._submit_to_xloader(resource_dict)

    # IResourceController

    def after_resource_create(self, context, resource_dict):
        self._submit_to_xloader(resource_dict)

    def before_resource_show(self, resource_dict):
        resource_dict[
            "datastore_contains_all_records_of_source_file"
        ] = toolkit.asbool(
            resource_dict.get("datastore_contains_all_records_of_source_file")
        )

    def after_resource_update(self, context, resource_dict):
        """ Check whether the datastore is out of sync with the
        'datastore_active' flag. This can occur due to race conditions
        like https://github.com/ckan/ckan/issues/4663
        """
        datastore_active = resource_dict.get('datastore_active', False)
        try:
            context = {'ignore_auth': True}
            if toolkit.get_action('datastore_info')(
                    context=context, data_dict={'id': resource_dict['id']}):
                datastore_exists = True
            else:
                datastore_exists = False
        except toolkit.ObjectNotFound:
            datastore_exists = False

        if datastore_active != datastore_exists:
            # flag is out of sync with datastore; update it
            utils.set_resource_metadata(
                {'resource_id': resource_dict['id'],
                 'datastore_active': datastore_exists})

    if not toolkit.check_ckan_version("2.10"):

        def after_create(self, context, resource_dict):
            self.after_resource_create(context, resource_dict)

        def before_show(self, resource_dict):
            self.before_resource_show(resource_dict)

        def after_update(self, context, resource_dict):
            self.after_resource_update(context, resource_dict)

    def _submit_to_xloader(self, resource_dict):
        context = {"ignore_auth": True, "defer_commit": True}
        resource_format = resource_dict.get("format")
        if not XLoaderFormats.is_it_an_xloader_format(resource_format):
            log.debug(
                f"Skipping xloading resource {resource_dict['id']} because "
                f'format "{resource_format}" is not configured to be '
                "xloadered"
            )
            return
        if resource_dict["url_type"] in ("datapusher", "xloader"):
            log.debug(
                "Skipping xloading resource {id} because "
                'url_type "{url_type}" means resource.url '
                "points to the datastore already, so loading "
                "would be circular.".format(**resource_dict)
            )
            return

        try:
            log.debug(
                "Submitting resource %s to be xloadered", resource_dict["id"]
            )
            toolkit.get_action("xloader_submit")(
                context,
                {
                    "resource_id": resource_dict["id"],
                    "ignore_hash": self.ignore_hash,
                },
            )
        except toolkit.ValidationError as e:
            # If xloader is offline, we want to catch error instead
            # of raising otherwise resource save will fail with 500
            log.critical(e)
            pass

    # IActions

    def get_actions(self):
        return {
            "xloader_submit": action.xloader_submit,
            "xloader_hook": action.xloader_hook,
            "xloader_status": action.xloader_status,
        }

    # IAuthFunctions

    def get_auth_functions(self):
        return {
            "xloader_submit": auth.xloader_submit,
            "xloader_status": auth.xloader_status,
        }

    # ITemplateHelpers

    def get_helpers(self):
        return {
            "xloader_status": xloader_helpers.xloader_status,
            "xloader_status_description": xloader_helpers.xloader_status_description,
            "is_resource_supported_by_xloader": xloader_helpers.is_resource_supported_by_xloader,
            "xloader_badge": xloader_helpers.xloader_badge,
        }


def _should_remove_unsupported_resource_from_datastore(res_dict):
    if not toolkit.asbool(toolkit.config.get('ckanext.xloader.clean_datastore_tables', False)):
        return False
    return (not XLoaderFormats.is_it_an_xloader_format(res_dict.get('format', u''))
            and (res_dict.get('url_type') == 'upload'
                 or not res_dict.get('url_type'))
            and (toolkit.asbool(res_dict.get('datastore_active', False))
                 or toolkit.asbool(res_dict.get('extras', {}).get('datastore_active', False))))


def _remove_unsupported_resource_from_datastore(resource_id):
    """
    Callback to remove unsupported datastore tables.
    Controlled by config value: ckanext.xloader.clean_datastore_tables.
    Double check the resource format. Only supported Xloader formats should have datastore tables.
    If the resource format is not supported, we should delete the datastore tables.
    """
    context = {"ignore_auth": True}
    try:
        res = toolkit.get_action('resource_show')(context, {"id": resource_id})
    except toolkit.ObjectNotFound:
        log.error('Resource %s does not exist.', resource_id)
        return

    if _should_remove_unsupported_resource_from_datastore(res):
        log.info('Unsupported resource format "%s". Deleting datastore tables for resource %s',
                 res.get(u'format', u''), res['id'])
        try:
            toolkit.get_action('datastore_delete')(context, {
                "resource_id": res['id'],
                "force": True})
            log.info('Datastore table dropped for resource %s', res['id'])
        except toolkit.ObjectNotFound:
            log.error('Datastore table for resource %s does not exist', res['id'])
