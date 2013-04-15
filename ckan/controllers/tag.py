from pylons import config

import ckan.logic as logic
import ckan.model as model
import ckan.lib.base as base
import ckan.lib.helpers as h

from ckan.common import _, request, c


LIMIT = 25


class TagController(base.BaseController):

    def __before__(self, action, **env):
        base.BaseController.__before__(self, action, **env)
        try:
            context = {'model': model, 'user': c.user or c.author}
            logic.check_access('site_read', context)
        except logic.NotAuthorized:
            base.abort(401, _('Not authorized to see this page'))

    def index(self):
        c.q = request.params.get('q', '')

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}

        data_dict = {'all_fields': True}

        if c.q:
            page = int(request.params.get('page', 1))
            data_dict['q'] = c.q
            data_dict['limit'] = LIMIT
            data_dict['offset'] = (page - 1) * LIMIT
            data_dict['return_objects'] = True

        results = logic.get_action('tag_list')(context, data_dict)

        if c.q:
            c.page = h.Page(
                collection=results,
                page=page,
                item_count=len(results),
                items_per_page=LIMIT
            )
            c.page.items = results
        else:
            c.page = h.AlphaPage(
                collection=results,
                page=request.params.get('page', 'A'),
                alpha_attribute='name',
                other_text=_('Other'),
            )

        return base.render('tag/index.html')

    def read(self, id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True}

        data_dict = {'id': id}
        try:
            c.tag = logic.get_action('tag_show')(context, data_dict)
        except logic.NotFound:
            base.abort(404, _('Tag not found'))

        if h.asbool(config.get('ckan.legacy_templates', False)):
            return base.render('tag/read.html')
        else:
            h.redirect_to(controller='package', action='search',
                          tags=c.tag.get('name'))
