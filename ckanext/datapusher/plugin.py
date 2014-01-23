import logging

import ckan.plugins as p
import ckan.lib.base as base
import ckan.lib.helpers as core_helpers
import ckanext.datapusher.logic.action as action
import ckanext.datapusher.logic.auth as auth
import ckanext.datapusher.helpers as helpers
import ckan.logic as logic
import ckan.model as model
import ckan.plugins.toolkit as toolkit

log = logging.getLogger(__name__)
_get_or_bust = logic.get_or_bust

DEFAULT_FORMATS = ['csv', 'xls', 'application/csv', 'application/vnd.ms-excel']


class DatastoreException(Exception):
    pass


class ResourceDataController(base.BaseController):

    def resource_data(self, id, resource_id):

        if toolkit.request.method == 'POST':
            try:
                toolkit.c.pkg_dict = p.toolkit.get_action('datapusher_submit')(
                    None, {'resource_id': resource_id}
                )
            except logic.ValidationError:
                pass

            base.redirect(core_helpers.url_for(
                controller='ckanext.datapusher.plugin:ResourceDataController',
                action='resource_data',
                id=id,
                resource_id=resource_id)
            )

        try:
            toolkit.c.pkg_dict = p.toolkit.get_action('package_show')(
                None, {'id': id}
            )
            toolkit.c.resource = p.toolkit.get_action('resource_show')(
                None, {'id': resource_id}
            )
        except logic.NotFound:
            base.abort(404, _('Resource not found'))
        except logic.NotAuthorized:
            base.abort(401, _('Unauthorized to edit this resource'))

        try:
            datapusher_status = p.toolkit.get_action('datapusher_status')(
                None, {'resource_id': resource_id}
            )
        except logic.NotFound:
            datapusher_status = {}

        return base.render('package/resource_data.html',
                           extra_vars={'status': datapusher_status})


class DatapusherPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurable, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IResourceUrlChange)
    p.implements(p.IDomainObjectModification, inherit=True)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IRoutes, inherit=True)

    legacy_mode = False
    resource_show_action = None

    def configure(self, config):
        self.config = config

        datapusher_formats = config.get('ckan.datapusher.formats', '').lower()
        self.datapusher_formats = datapusher_formats.split() or DEFAULT_FORMATS

        for config_option in ('ckan.site_url', 'ckan.datapusher.url',):
            if not config.get(config_option):
                raise Exception(
                    'Config option `{0}` must be set to use the DataPusher.'
                    .format(config_option))

    def notify(self, entity, operation=None):
        if isinstance(entity, model.Resource):
            if (operation == model.domain_object.DomainObjectOperation.new
                    or not operation):
                # if operation is None, resource URL has been changed, as
                # the notify function in IResourceUrlChange only takes
                # 1 parameter
                context = {'model': model, 'ignore_auth': True,
                           'defer_commit': True}
                if (entity.format and
                        entity.format.lower() in self.datapusher_formats and
                        entity.url_type != 'datapusher'):
                    try:
                        p.toolkit.get_action('datapusher_submit')(context, {
                            'resource_id': entity.id
                        })
                    except p.toolkit.ValidationError, e:
                        # If datapusher is offline want to catch error instead
                        # of raising otherwise resource save will fail with 500
                        log.critical(e)
                        pass

    def before_map(self, m):
        m.connect(
            'resource_data', '/dataset/{id}/resource_data/{resource_id}',
            controller='ckanext.datapusher.plugin:ResourceDataController',
            action='resource_data', ckan_icon='cloud-upload')
        return m

    def get_actions(self):
        return {'datapusher_submit': action.datapusher_submit,
                'datapusher_hook': action.datapusher_hook,
                'datapusher_status': action.datapusher_status}

    def get_auth_functions(self):
        return {'datapusher_submit': auth.datapusher_submit,
                'datapusher_status': auth.datapusher_status}

    def get_helpers(self):
        return {
            'datapusher_status': helpers.datapusher_status,
            'datapusher_status_description':
            helpers.datapusher_status_description,
        }
