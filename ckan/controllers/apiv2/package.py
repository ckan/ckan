from sqlalchemy.sql import select, and_
from ckan.lib.base import _, request, response, c
from ckan.lib.cache import ckan_cache
from ckan.lib.helpers import json
from ckan.lib.munge import munge_title_to_name
import ckan.model as model
import ckan

from ckan.controllers.apiv1.package import PackageController as _PackageV1Controller

log = __import__("logging").getLogger(__name__)

# For form name auto-generation
from ckan.forms.common import package_exists
from ckan.lib.helpers import json
from ckan.lib.search import query_for

class Rest2Controller(object):
    api_version = '2'
    ref_package_by = 'id'
    ref_group_by = 'id'

    def _represent_package(self, package):
        return package.as_dict(ref_package_by=self.ref_package_by, ref_group_by=self.ref_group_by)
    
class PackageController(Rest2Controller, _PackageV1Controller):
    def _last_modified(self, id):
        """
        Return most recent timestamp for this package
        """
        return model.Package.last_modified(model.package_table.c.id == id)

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

    def create_slug(self):
        title = request.params.get('title') or ''
        name = munge_title_to_name(title)
        if package_exists(name):
            valid = False
        else:
            valid = True
        #response.content_type = 'application/javascript'
        response_data = dict(name=name.replace('_', '-'), valid=valid)
        return self._finish_ok(response_data)

    def autocomplete(self):
        incomplete = request.params.get('incomplete', '')
        if incomplete:
            query = query_for('tag', backend='sql')
            query.run(query=incomplete,
                      return_objects=True,
                      limit=10,
                      username=c.user)
            tagNames = [t.name for t in query.results]
        else:
            tagNames = []
        resultSet = {
            "ResultSet": {
                "Result": []
            }
        }
        for tagName in tagNames[:10]:
            result = {
                "Name": tagName
            }
            resultSet["ResultSet"]["Result"].append(result)
        return self._finish_ok(resultSet)

