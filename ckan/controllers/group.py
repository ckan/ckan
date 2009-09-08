from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController
from simplejson import dumps

class GroupController(CkanBaseController):

    def index(self):
        h.redirect_to(action='list')

    def list(self, id):
        return self._paginate_list('group', id, 'group/list', ['name', 'title'])

    def read(self, id):
        c.group = model.Group.by_name(id)
        if c.group is None:
            abort(404)
        return render('group/read')

    def autocomplete(self):
        incomplete = request.params.get('incomplete', '')
        if incomplete:
            groups = list(model.Group.search_by_name(incomplete))
            groupNames = [t.name for t in groups]
        else:
            groupNames = []
        resultSet = {
            "ResultSet": {
                "Result": []
            }
        }
        for groupName in groupNames[:10]:
            result = {
                "Name": groupName
            }
            resultSet["ResultSet"]["Result"].append(result)
        return dumps(resultSet)

