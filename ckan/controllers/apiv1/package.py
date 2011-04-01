import copy

from ckan.controllers.rest import RestController
from ckan.lib.base import _, request, response, c
from ckan.lib.cache import ckan_cache
from ckan.lib.helpers import json
import ckan.model as model
import ckan
from ckan.plugins import PluginImplementations, IPackageController

log = __import__("logging").getLogger(__name__)

readonly_keys = ('id', 'revision_id',
                 'relationships',
                 'license',
                 'ratings_average', 'ratings_count',
                 'ckan_url',
                 'metadata_modified',
                 'metadata_created',
                 'notes_rendered')

class PackageController(RestController):

    extensions = PluginImplementations(IPackageController)

    @ckan_cache(test=model.Package.last_modified, query_args=True)
    def list(self):
        """
        Return a list of all packages
        """
        query = ckan.authz.Authorizer().authorized_query(c.user, model.Package)
        packages = query.all()
        response_data = self._list_package_refs(packages)
        return self._finish_ok(response_data)

    def _last_modified(self, id):
        """
        Return most recent timestamp for this package
        """
        return model.Package.last_modified(model.package_table.c.name == id)

    @ckan_cache(test=_last_modified, query_args=True)
    def show(self, id):
        """
        Return the specified package
        """
        pkg = self._get_pkg(id)
        if pkg is None:
            response_args = {'status_int': 404,
                             'content_type': 'json',
                             'response_data': _('Not found')}
        elif not self._check_access(pkg, model.Action.READ):
            response_args = {'status_int': 403,
                             'content_type': 'json',
                             'response_data': _('Access denied')}
        else:
            response_data = self._represent_package(pkg)
            response_args = {'status_int': 200,
                             'content_type': 'json',
                             'response_data': response_data}
        for item in self.extensions:
            item.read(pkg)
        return self._finish(**response_args)
    
    def create(self):
        if not self._check_access(model.System(), model.Action.PACKAGE_CREATE):
            return self._finish_not_authz()

        # Create a Package.
        fs = self._get_standard_package_fieldset()
        try:
            request_data = self._get_request_data()
            request_data = self._strip_readonly_keys(request_data)
            request_fa_dict = ckan.forms.edit_package_dict(ckan.forms.get_package_dict(fs=fs), request_data)
            fs = fs.bind(model.Package, data=request_fa_dict, session=model.Session)
            log.debug('Created object %s' % str(fs.name.value))
            obj = fs.model
            
            # Validate the fieldset.
            validation = fs.validate()
            if not validation:
                # Complain about validation errors.
                log.error('Validation error: %r' % repr(fs.errors))
                response.write(self._finish(409, repr(fs.errors),
                                            content_type='json'))
            else:
                try:
                    # Construct new revision.
                    rev = model.repo.new_revision()
                    rev.author = self.rest_api_user
                    rev.message = _(u'REST API: Create object %s') % str(fs.name.value)
                    # Construct catalogue entity.
                    fs.sync()
                    # Construct access control entities.
                    if self.rest_api_user:
                        admins = [model.User.by_name(self.rest_api_user.decode('utf8'))]
                    else:
                        admins = []
                    model.setup_default_user_roles(fs.model, admins)
                    for item in self.extensions:
                        item.create(fs.model)
                    # Commit
                    model.repo.commit()        
                    # Set location header with new ID.
                    location = str('%s/%s' % (request.path, obj.id))
                    response.headers['Location'] = location
                    log.debug('Response headers: %r' % (response.headers))
                    response.write(self._finish_ok(
                        obj.as_dict(),
                        newly_created_resource_location=location))
                except Exception, inst:
                    log.exception(inst)
                    model.Session.rollback()
                    log.error('Exception creating object %s: %r' % (str(fs.name.value), inst))
                    raise
        except ValueError, inst:
            response.status_int = 400
            response.write(_(u'JSON Error: %s') % str(inst))
        except ckan.forms.PackageDictFormatError, inst:
            log.error('Package format incorrect: %s' % str(inst))
            response.status_int = 400
            response.write(_(u'Package format incorrect: %s') % str(inst))
        return response
    
    def update(self, id):
        entity = self._get_pkg(id)
        if entity is not None and not self._check_access(entity, model.Action.EDIT):
            return self._finish_not_authz()
        
        if entity is None:
            response.status_int = 404
            response.write(_('Package was not found.'))
        else:
            fs = self._get_standard_package_fieldset()
            orig_entity_dict = ckan.forms.get_package_dict(pkg=entity, fs=fs)
            try:
                request_data = self._get_request_data()
                request_data = self._strip_readonly_keys(request_data,
                                                         entity.as_dict())
                request_fa_dict = ckan.forms.edit_package_dict(orig_entity_dict, request_data, id=entity.id)
                fs = fs.bind(entity, data=request_fa_dict)
                validation = fs.validate()
                if not validation:
                    response.write(self._finish(409, repr(fs.errors),
                                                content_type='json'))
                else:
                    try:
                        rev = model.repo.new_revision()
                        rev.author = self.rest_api_user
                        rev.message = _(u'REST API: Update object %s') % str(fs.name.value)
                        fs.sync()
                        for item in self.extensions:
                            item.edit(fs.model)
                        model.repo.commit()        
                    except Exception, inst:
                        log.exception(inst)
                        model.Session.rollback()
                        if inst.__class__.__name__ == 'IntegrityError':
                            response.status_int = 409
                            response.write(_(u'Integrity Error'))
                        else:
                            raise
                    obj = fs.model
                    response.write(self._finish_ok(obj.as_dict()))
            except ValueError, inst:
                response.status_int = 400
                response.write(_('JSON Error: %s') % str(inst))
            except ckan.forms.PackageDictFormatError, inst:
                response.status_int = 400
                response.write(_(u'Package format incorrect: %s') % str(inst))
        return response

    def delete(self, id):
        entity = self._get_pkg(id)
        if entity is None:
            response.status_int = 404
            return _(u'Package was not found.')
        
        if not self._check_access(entity, model.Action.PURGE):
            return self._finish_not_authz()
        
        rev = model.repo.new_revision()
        rev.author = self.rest_api_user
        rev.message = _(u'REST API: Delete Package: %s') % entity.name
        try:
            for item in self.extensions:
                item.delete(entity)
            entity.delete()
            model.repo.commit()        
        except Exception, inst:
            log.exception(inst)
            raise
        return self._finish_ok()

    def _strip_readonly_keys(self, request_dict, existing_pkg_dict=None):
        '''Removes keys that are readonly. If there is an existing package,
        the values of the keys are checked against to see if they have
        been inadvertantly edited - if so, raise an error.
        '''
        stripped_package_dict = copy.deepcopy(request_dict)
        for key in readonly_keys:
            if request_dict.has_key(key):
                if existing_pkg_dict:
                    if request_dict[key] != existing_pkg_dict.get(key):
                        raise ckan.forms.PackageDictFormatError(
                            'Cannot change value of key %r from %r to %r. This key is read-only.' % (key, existing_pkg_dict.get(key), request_dict[key]))
                else:
                    raise ckan.forms.PackageDictFormatError(
                        'Key %r is read-only - do not include in the '
                        'package.' % key)                    
                del stripped_package_dict[key]# = request_dict[key]
        return stripped_package_dict
