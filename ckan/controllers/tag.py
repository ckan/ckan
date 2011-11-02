from pylons.i18n import _
from pylons import config
from sqlalchemy.orm import eagerload_all

from ckan.lib.base import *
from ckan.lib.search import query_for
from ckan.lib.helpers import AlphaPage, Page

from ckan.logic import NotFound, NotAuthorized
from ckan.logic import check_access, get_action

LIMIT = 25

class TagController(BaseController):

    def __before__(self, action, **env):
        BaseController.__before__(self, action, **env)
        try:
            context = {'model':model,'user': c.user or c.author}
            check_access('site_read',context)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

    def index(self):
        c.q = request.params.get('q', '')

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}

        data_dict = {}

        if c.q:
            page = int(request.params.get('page', 1))
            data_dict['q'] = c.q
            data_dict['limit'] = LIMIT
            data_dict['offset'] = (page-1)*LIMIT
            data_dict['return_objects'] = True
               
        results = get_action('tag_list')(context,data_dict)
         
        if c.q:
            c.page = h.Page(
                            collection=results,
                            page=page,
                            item_count=len(results),
                            items_per_page=LIMIT
                            )
            c.page.items = results
        else:
            c.page = AlphaPage(
                collection=results,
                page=request.params.get('page', 'A'),
                alpha_attribute='name',
                other_text=_('Other'),
            )
           
        return render('tag/index.html')

    def read(self, id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        
        data_dict = {'id':id}
        try:
            c.tag = get_action('tag_show')(context,data_dict)
        except NotFound:
            abort(404, _('Tag not found'))

        return render('tag/read.html')

