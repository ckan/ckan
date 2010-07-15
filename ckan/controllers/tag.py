from pylons.i18n import _

from ckan.lib.base import *
from ckan.lib.helpers import json, AlphaPage

class TagController(BaseController):

    def index(self):
        c.q = request.params.get('q', '')
        
        if c.q:
            query = model.Tag.search_by_name(c.q)
        else:
            query = model.Session.query(model.Tag)
           
        c.page = AlphaPage(
            collection=query,
            page=request.params.get('page', 'A'),
            alpha_attribute='name',
            other_text=_('Other'),
        )
           
        return render('tag/index.html')

    def read(self, id):
        c.tag = model.Tag.by_name(id)
        if c.tag is None:
            abort(404)
        return render('tag/read.html')

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
        return json.dumps(resultSet)

