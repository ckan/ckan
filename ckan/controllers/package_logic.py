import logging

from ckan.lib.base import BaseController, render, c, model, abort, request
from ckan.lib.base import redirect, _, config, h
import ckan.logic.action.create as create
import ckan.logic.action.update as update
import ckan.logic.action.get as get
from ckan.lib.navl.dictization_functions import DataError, flatten_dict, unflatten
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import tuplize_dict, untuplize_dict, clean_dict

log = logging.getLogger(__name__)

class PackageLogicController(BaseController):

    def new(self, data=None, errors=None):
        data = data or {}
        errors = errors or {}
        vars = {'data': data, 'errors': errors}
        c.licences = [('', None)] + model.Package.get_license_options()
        c.form = render('package/new_package_form.html', extra_vars=vars)
        return render('package/new.html')

    def edit(self, id, data=None, errors=None):
        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'id': id, 'extras_as_string': True}

        data = data or get.package_show(context)
        errors = errors or {}
        vars = {'data': data, 'errors': errors}

        c.licences = [('', None)] + model.Package.get_license_options()
        c.form = render('package/new_package_form.html', extra_vars=vars)
        return render('package/edit.html')


    def save(self, id=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'id': id}
        data_dict = unflatten(tuplize_dict(clean_dict(dict(request.params))))
        context['message'] = data_dict.pop(('log_message',), '')

        try:
            if id:
                pkg = update.package_update(data_dict, context)
            else:
                pkg = create.package_create(data_dict, context)
            self._form_save_redirect(pkg['name'], 'new')
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % id)
            return
        except NotFound, e:
            abort(404, _('Package not found'))
            return
        except ValidationError, e:
            errors = e.error_dict
            if id:
                return self.edit(id, data_dict, errors)
            else:
                return self.new(data_dict, errors)

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
