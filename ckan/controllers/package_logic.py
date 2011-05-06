import logging

from ckan.lib.base import BaseController, render, c, model, abort, request
from ckan.lib.base import redirect, _, config, h
import ckan.logic.action.create as create
import ckan.logic.action.update as update
import ckan.logic.action.get as get
from ckan.lib.navl.dictization_functions import DataError, flatten_dict, unflatten
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import tuplize_dict, untuplize_dict, clean_dict
from ckan.logic.schema import package_form_schema
from ckan.lib.package_saver import PackageSaver
from ckan.authz import Authorizer

log = logging.getLogger(__name__)

class PackageLogicController(BaseController):


    def new(self, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'preview': 'preview' in request.params,
                   'save': 'save' in request.params,
                   'schema': package_form_schema()}

        auth_for_create = Authorizer().am_authorized(c, model.Action.PACKAGE_CREATE, model.System())
        if not auth_for_create:
            abort(401, _('Unauthorized to create a package'))

        if (context['save'] or context['preview']) and not data:
            return self._save_new(context)

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        self._setup_template_variables(context)
        c.form = render('package/new_package_form.html', extra_vars=vars)
        return render('package/new.html')

    def edit(self, id, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'preview': 'preview' in request.params,
                   'save': 'save' in request.params,
                   'schema': package_form_schema(),
                   'id': id}

        if (context['save'] or context['preview']) and not data:
            return self._save_edit(id, context)

        try:
            old_data = get.package_show(context)
            data = data or old_data
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % '')

        c.pkg = context.get("package")

        am_authz = self.authorizer.am_authorized(c, model.Action.EDIT, c.pkg)
        if not am_authz:
            abort(401, _('User %r not authorized to edit %s') % (c.user, id))

        errors = errors or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        self._setup_template_variables(context)
        c.form = render('package/new_package_form.html', extra_vars=vars)
        return render('package/edit.html')

    def _save_new(self, context):
        try:
            data_dict = clean_dict(unflatten(tuplize_dict(dict(request.params))))
            self._check_data_dict(data_dict)
            context['message'] = data_dict.get('log_message', '')
            pkg = create.package_create(data_dict, context)

            if context['preview']:
                PackageSaver().render_package(context['package'])
                c.is_preview = True
                c.preview = render('package/read_core.html')
                return self.new(data_dict)

            self._form_save_redirect(pkg['name'], 'new')
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % '')
        except NotFound, e:
            abort(404, _('Package not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.new(data_dict, errors, error_summary)

    def _save_edit(self, id, context):
        try:
            data_dict = clean_dict(unflatten(tuplize_dict(dict(request.params))))
            self._check_data_dict(data_dict)
            context['message'] = data_dict.get('log_message', '')
            pkg = update.package_update(data_dict, context)
            c.pkg = context['package']

            if context['preview']:
                c.is_preview = True
                PackageSaver().render_package(context['package'])
                c.preview = render('package/read_core.html')
                return self.edit(id, data_dict)

            self._form_save_redirect(pkg['name'], 'edit')
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % id)
        except NotFound, e:
            abort(404, _('Package not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(id, data_dict, errors, error_summary)

    def _check_data_dict(self, data_dict):
        '''Check if the return data is correct'''

        surplus_keys_schema = ['__extras', '__junk', 'state', 'groups',
                               'extras_validation', 'save', 'preview',
                               'return_to']

        schema_keys = package_form_schema().keys()
        keys_in_schema = set(schema_keys) - set(surplus_keys_schema)

        if keys_in_schema - set(data_dict.keys()):
            log.info('incorrect form fields posted')
            raise DataError(data_dict)

    def _setup_template_variables(self, context):
        c.groups = get.group_list_availible(context)
        c.groups_authz = get.group_list_authz(context)
        c.licences = [('', '')] + model.Package.get_license_options()
        c.is_sysadmin = Authorizer().is_sysadmin(c.user)
        c.resource_columns = model.Resource.get_columns()

        ## This is messy as auths take domain object not data_dict
        pkg = context.get('package') or c.pkg
        if pkg:
            c.auth_for_change_state = Authorizer().am_authorized(
                c, model.Action.CHANGE_STATE, pkg)
    

    def _form_save_redirect(self, pkgname, action):
        '''This redirects the user to the CKAN package/read page,
        unless there is request parameter giving an alternate location,
        perhaps an external website.
        @param pkgname - Name of the package just edited
        @param action - What the action of the edit was
        '''
        assert action in ('new', 'edit')
        url = request.params.get('return_to') or \
              config.get('package_%s_return_url' % action)
        if url:
            url = url.replace('<NAME>', pkgname)
        else:
            url = h.url_for(controller='package', action='read', id=pkgname)
        redirect(url)        
