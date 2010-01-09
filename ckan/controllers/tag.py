from ckan.lib.base import *
from simplejson import dumps

class TagController(BaseController):

    def index(self):
        from ckan.lib.helpers import Page
        
        c.q = request.params.get('q', '')
        
        if c.q:
            query = model.Tag.search_by_name(c.q)
        else:
            query = model.Session.query(model.Tag)
           
        c.page = Page(
            collection=query,
            page=request.params.get('page', 1),
            items_per_page=100
        )
           
        return render('tag/index')

    def read(self, id):
        c.tag = model.Tag.by_name(id)
        if c.tag is None:
            abort(404)
        return render('tag/read')

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

