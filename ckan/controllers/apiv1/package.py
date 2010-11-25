from ckan.controllers.rest import RestController
from ckan.lib.base import _, request, response
from ckan.lib.cache import ckan_cache
from ckan.lib.helpers import json
import ckan.model as model
import ckan
from ckan.plugins import ExtensionPoint, IPackageController

log = __import__("logging").getLogger(__name__)

class PackageController(RestController):

    extensions = ExtensionPoint(IPackageController)

    @ckan_cache(test=model.Package.last_modified, query_args=True)
    def list(self):
        """
        Return a list of all packages
        """
        query = ckan.authz.Authorizer().authorized_query(self._get_username(), model.Package)
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
            response.status_int = 404
            response_data = json.dumps(_('Not found'))
        elif not self._check_access(pkg, model.Action.READ):
            response.status_int = 403
            response_data = json.dumps(_('Access denied'))
        else:
            response_data = self._represent_package(pkg)
        for item in self.extensions:
            item.read(pkg)
        return self._finish_ok(response_data)
    
    def create(self):
        if not self._check_access(model.System(), model.Action.PACKAGE_CREATE):
            return json.dumps(_('Access denied'))

        # Create a Package.
        fs = self._get_standard_package_fieldset()
        try:
            request_data = self._get_request_data()
            request_fa_dict = ckan.forms.edit_package_dict(ckan.forms.get_package_dict(fs=fs), request_data)
            fs = fs.bind(model.Package, data=request_fa_dict, session=model.Session)
            log.debug('Created object %s' % str(fs.name.value))
            obj = fs.model
            
            # Validate the fieldset.
            validation = fs.validate()
            if not validation:
                # Complain about validation errors.
                log.error('Validation error: %r' % repr(fs.errors))
                response.status_int = 409
                response.write(json.dumps(repr(fs.errors)))
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
                    # Todo: Return 201, not 200.
                    response.write(self._finish_ok(obj.as_dict()))
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
            return json.dumps(_('Access denied'))
        
        if entity is None:
            response.status_int = 404
            response.write(_('Package was not found.'))
        else:
            fs = self._get_standard_package_fieldset()
            orig_entity_dict = ckan.forms.get_package_dict(pkg=entity, fs=fs)
            try:
                request_data = self._get_request_data()
                request_fa_dict = ckan.forms.edit_package_dict(orig_entity_dict, request_data, id=entity.id)
                fs = fs.bind(entity, data=request_fa_dict)
                validation = fs.validate()
                if not validation:
                    response.status_int = 409
                    response.write(json.dumps(repr(fs.errors)))
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
            #response.status_int = 401
            return json.dumps(_('Access denied'))
        
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
