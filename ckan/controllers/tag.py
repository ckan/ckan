from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController
from simplejson import dumps

class TagController(CkanBaseController):

    def index(self):
        return render('tag/index')

    def read(self, id):
        c.tag = model.Tag.by_name(id)
        if c.tag is None:
            abort(404)
        return render('tag/read')

    def list(self, id):
        return self._paginate_list('tag', id, 'tag/list')

    def search(self):
        c.search_terms = request.params.get('search_terms', '')
        if c.search_terms:
            c.tags = list(model.Tag.search_by_name(c.search_terms))
            c.tag_count = len(c.tags)
        return render('tag/search')

    def autocomplete(self):
        incomplete = request.params.get('incomplete', '')
        if incomplete:
            tags = list(model.Tag.search_by_name(incomplete))
            tagNames = [t.name for t in tags]
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
        return dumps(resultSet)

