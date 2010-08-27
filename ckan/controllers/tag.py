from pylons.i18n import _

from ckan.lib.base import *
from sqlalchemy.orm import eagerload_all
from ckan.lib.search import query_for
from ckan.lib.helpers import json, AlphaPage, Page

LIMIT = 25

class TagController(BaseController):

    def index(self):
        c.q = request.params.get('q', '')
        
        if c.q:
            page = int(request.params.get('page', 1))
            query = query_for('tag', backend='sql')
            query.run(query=c.q,
                      limit=LIMIT,
                      offset=(page-1)*LIMIT,
                      return_objects=True,
                      username=c.user)
            c.page = h.Page(
                            collection=query.results,
                            page=page,
                            item_count=query.count,
                            items_per_page=LIMIT
                            )
            c.page.items = query.results
        else:
            query = model.Tag.all()
            c.page = AlphaPage(
                collection=query,
                page=request.params.get('page', 'A'),
                alpha_attribute='name',
                other_text=_('Other'),
            )
           
        return render('tag/index.html')

    def read(self, id):
        query = model.Session.query(model.Tag)
        query = query.filter(model.Tag.name==id)
        query = query.options(eagerload_all('package_tags.package'))
        query = query.options(eagerload_all('package_tags.package.package_tags.tag'))
        query = query.options(eagerload_all('package_tags.package.package_resources_all'))
        c.tag = query.first()
        if c.tag is None:
            abort(404)
        return render('tag/read.html')

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
        return json.dumps(resultSet)

