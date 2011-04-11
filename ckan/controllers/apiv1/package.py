import copy

from ckan.controllers.rest import RestController, ApiVersion1, ApiVersion2
from ckan.lib.base import _, request, response, c
from ckan.lib.cache import ckan_cache
from ckan.lib.helpers import json
import ckan.model as model
import ckan
from ckan.plugins import PluginImplementations, IPackageController
from ckan.lib.dictization.model_dictize import package_to_api1, package_to_api2
from ckan.lib.dictization.model_save import (package_api_to_dict,
                                             package_dict_save)
from ckan.lib.dictization.model_schema import (default_create_package_schema,
                                               default_update_package_schema)
from ckan.lib.navl.dictization_functions import validate, DataError

log = __import__("logging").getLogger(__name__)

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
            status_int = 404
            response_data = _('Not found')
        elif not self._check_access(pkg, model.Action.READ):
            status_int = 403
            response_data = _('Access denied')
        else:
            status_int = 200
            context = {'model': model,
                       'session': model.Session}
            if isinstance(self, ApiVersion1):
                response_data = package_to_api1(pkg, context)
            else:
                response_data = package_to_api2(pkg, context)

        for item in self.extensions:
            item.read(pkg)

        return self._finish(status_int=status_int,
                            response_data=response_data,
                            content_type='json'
                            )
    
    def create(self):
        if not self._check_access(model.System(), model.Action.PACKAGE_CREATE):
            return self._finish_not_authz()

        try:
            request_data = self._get_request_data()
        except ValueError, inst:
            response.status_int = 400
            response.write(_(u'JSON Error: %s') % str(inst))
            return response

        context = {'model': model, 'session': model.Session}
        dictized_package = package_api_to_dict(request_data, context)
        try:
            data, errors = validate(dictized_package,
                                    default_create_package_schema(),
                                    context)
        except DataError:
            log.error('Package format incorrect: %s' % request_data)
            response.status_int = 400
            response.write(_(u'Package format incorrect: %s') % request_data)
            return response

        if errors:
            log.error('Validation error: %r' % str(errors))
            response.write(self._finish(409, errors,
                                        content_type='json'))
            return response
        
        try:
            rev = model.repo.new_revision()
            rev.author = self.rest_api_user
            rev.message = _(u'REST API: Create object %s') % data["name"]

            pkg = package_dict_save(data, context)

            if self.rest_api_user:
                admins = [model.User.by_name(self.rest_api_user.decode('utf8'))]
            else:
                admins = []
            model.setup_default_user_roles(pkg, admins)
            for item in self.extensions:
                item.create(pkg)
            # Commit
            model.repo.commit()        
            # Set location header with new ID.
            location = str('%s/%s' % (request.path, pkg.id))
            response.headers['Location'] = location
            log.debug('Response headers: %r' % (response.headers))
            response.write(
                self._finish_ok(data, newly_created_resource_location=location)
            )
            
            return response
        except Exception, inst:
            log.exception(inst)
            model.Session.rollback()
            log.error('Exception creating object %s: %r' % (str(pkg), inst))
            raise

    
    def update(self, id):
        pkg = self._get_pkg(id)
        if pkg is not None and not self._check_access(pkg, model.Action.EDIT):
            return self._finish_not_authz()
        
        if pkg is None:
            response.status_int = 404
            response.write(_('Package was not found.'))
            return response

        try:
            request_data = self._get_request_data()
        except ValueError, inst:
            response.status_int = 400
            response.write(_(u'JSON Error: %s') % str(inst))
            return response

        context = {'model': model, 'session': model.Session, 'package' : pkg}
        dictized_package = package_api_to_dict(request_data, context)

        try:
            data, errors = validate(dictized_package,
                                    default_update_package_schema(),
                                    context)
        except DataError, e:
            log.error('Package format incorrect: %s' % request_data)
            response.status_int = 400
            response.write(_(u'Package format incorrect: %s') % request_data)
            return response

        if errors:
            log.error('Validation error: %s' % errors)
            response.write(self._finish(409, repr(errors),
                                        content_type='json'))
            return response

        try:
            rev = model.repo.new_revision()
            rev.author = self.rest_api_user
            rev.message = _(u'REST API: Update object %s') % pkg.name

            pkg = package_dict_save(data, context)
            for item in self.extensions:
                item.edit(pkg)
            model.repo.commit()        
            data["name"] = pkg.name
            response.write(self._finish_ok(data))

        except Exception, inst:
            log.exception(inst)
            model.Session.rollback()
            if inst.__class__.__name__ == 'IntegrityError':
                response.status_int = 409
                response.write(_(u'Integrity Error'))
            else:
                raise
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

