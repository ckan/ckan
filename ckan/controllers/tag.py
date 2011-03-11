from pylons.i18n import _
from pylons import config
from sqlalchemy.orm import eagerload_all

from ckan.lib.base import *
from ckan.lib.search import query_for
from ckan.lib.cache import proxy_cache
from ckan.lib.helpers import AlphaPage, Page

LIMIT = 25

class TagController(BaseController):

    def __before__(self, action, **env):
        BaseController.__before__(self, action, **env)
        if not self.authorizer.am_authorized(c, model.Action.SITE_READ, model.System):
            abort(401, _('Not authorized to see this page'))

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

    @proxy_cache()
    def read(self, id):
        query = model.Session.query(model.Tag)
        query = query.filter(model.Tag.name==id)
        query = query.options(eagerload_all('package_tags.package'))
        query = query.options(eagerload_all('package_tags.package.package_tags.tag'))
        query = query.options(eagerload_all('package_tags.package.resource_groups_all.resources_all'))
        c.tag = query.first()
        if c.tag is None:
            abort(404)
        return render('tag/read.html')

