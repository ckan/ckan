import logging

import ckan.plugins as p
import ckanext.datapusher.logic.action as action
import ckanext.datapusher.logic.auth as auth
import ckanext.datapusher.helpers as helpers
import ckan.logic as logic
import ckan.model as model

log = logging.getLogger(__name__)
_get_or_bust = logic.get_or_bust

DEFAULT_FORMATS = []


class DatastoreException(Exception):
    pass


class DatapusherPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IResourceUrlChange)
    p.implements(p.IDomainObjectModification, inherit=True)
    p.implements(p.ITemplateHelpers)

    legacy_mode = False
    resource_show_action = None

    def configure(self, config):
        self.config = config

        datapusher_formats = config.get('ckan.datapusher.formats', '').split()
        self.datapusher_formats = datapusher_formats or DEFAULT_FORMATS

        datapusher_url = config.get('ckan.datapusher.url')
        if not datapusher_url:
            raise Exception(
                'Config option `ckan.datapusher.url` has to be set.')

    def notify(self, entity, operation=None):
        if isinstance(entity, model.Resource):
            if (operation == model.domain_object.DomainObjectOperation.new
                    or not operation):
                # if operation is None, resource URL has been changed, as
                # the notify function in IResourceUrlChange only takes
                # 1 parameter
                context = {'model': model, 'ignore_auth': True}
                package = p.toolkit.get_action('package_show')(context, {
                    'id': entity.get_package_id()
                })
                if (not package['private'] and
                        entity.format in self.datapusher_formats and
                        entity.url_type != 'datapusher'):
                    p.toolkit.get_action('datapusher_submit')(context, {
                        'resource_id': entity.id
                    })

    def get_actions(self):
        return {'datapusher_submit': action.datapusher_submit,
                'datapusher_hook': action.datapusher_hook,
                'datapusher_status': action.datapusher_status}

    def get_auth_functions(self):
        return {'datapusher_submit': auth.datapusher_submit,
                'datapusher_status': auth.datapusher_status}

    def get_helpers(self):
        return {
            'datapusher_status': helpers.datapusher_status}
