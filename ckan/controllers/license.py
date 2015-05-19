from pylons import config

import logging
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.model as model
import ckan.logic as logic
import ckan.plugins.toolkit as toolkit
get_action = logic.get_action
ValidationError = logic.ValidationError
NotFound = logic.NotFound

c = base.c
request = base.request
_ = base._

log = logging.getLogger(__name__)


class LicenseController(base.BaseController):
    def __before__(self, action, **params):
        super(LicenseController, self).__before__(action, **params)
        context = {'model': model,
                   'user': c.user, 'auth_user_obj': c.userobj}
        try:
            logic.check_access('sysadmin', context, {})
        except logic.NotAuthorized:
            base.abort(401, _('Need to be system administrator to administer'))

    def new(self, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj,
                   'save': 'save' in request.params}
        if context['save'] and not data:
            return self._save(context, action='new')

        errors = errors or {}
        error_summary = error_summary or {}
        if data and not errors:
            h.flash_success('License successfully added.')
            toolkit.redirect_to(controller='license', action='list')
        form_vars = {'data': data, 'errors': errors,
                     'error_summary': error_summary,
                     'update_action': False}
        return base.render('license/new.html', {'form_vars': form_vars})

    def _save(self, context, action):
        data_dict = {}
        for k, v in request.params.items():
            if k in model.license_table.columns:
                data_dict[k] = v
        errors = {}
        error_summary = {}
        if action == 'new':
            try:
                get_action('license_create')(context, data_dict)
            except ValidationError, e:
                errors = e.error_dict
                error_summary = e.error_summary

            return self.new(data_dict, errors, error_summary)
        elif action == 'update':
            try:
                get_action('license_update')(context, data_dict)
            except ValidationError, e:
                errors = e.error_dict
                error_summary = e.error_summary

            return self.update(data_dict['id'], data_dict,
                               errors, error_summary)

    def update(self, id, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj,
                   'save': 'save' in request.params}

        if context['save'] and not data:
            return self._save(context, action='update')

        try:
            license = get_action('license_item')(context, {'id': id})
        except NotFound:
            base.abort(404)

        errors = errors or {}
        error_summary = error_summary or {}
        if data and not errors:
            h.flash_success('License successfully updated.')
        data = data or license
        form_vars = {'data': data, 'errors': errors,
                     'error_summary': error_summary,
                     'update_action': True}
        return base.render('license/update.html', {'form_vars': form_vars})

    def delete(self, id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj,
                   'save': 'save' in request.params}
        try:
            get_action('license_delete')(context, {'id': id})
        except NotFound:
            base.abort(404)
        h.flash_success('License removed')
        return toolkit.redirect_to(controller='license', action='list')

    def reinstate(self, id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj,
                   'save': 'save' in request.params}
        try:
            get_action('license_reinstate')(context, {'id': id})
        except NotFound:
            base.abort(404)
        h.flash_success('License reinstated')
        return toolkit.redirect_to(controller='license', action='list')

    def list(self):
        if config.get('licenses_group_url'):
            return base.abort(404)
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj,
                   'api_version': 3, 'for_edit': True}
        license_list = toolkit.get_action('license_list')(context,
                                                          {'all': True})
        return base.render('license/list.html', {'license_list': license_list})
