

import ckan.model as model
import ckan.logic as logic
import ckan.lib.base as base
import ckan.lib.helpers as h
import urllib

c = base.c
_get_action=logic.get_action


class RelatedController(base.BaseController):

    def dashboard(self):
        """ List all related items regardless of dataset """
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'for_view': True}
        data_dict = {
            'type_filter': base.request.params.get('type', ''),
            'sort': base.request.params.get('sort', ''),
            'featured': base.request.params.get('featured', '')
        }

        params_nopage = [(k, v) for k,v in base.request.params.items()
                         if k != 'page']
        try:
            page = int(base.request.params.get('page', 1))
        except ValueError, e:
            base.abort(400, ('"page" parameter must be an integer'))

        # Update ordering in the context
        query = logic.get_action('related_list')(context,data_dict)

        def search_url(params):
            url = h.url_for(controller='related', action='dashboard')
            params = [(k, v.encode('utf-8')
                      if isinstance(v, basestring) else str(v))
                      for k, v in params]
            return url + u'?' + urllib.urlencode(params)

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params)


        c.page = h.Page(
            collection=query.all(),
            page=page,
            url=pager_url,
            item_count=query.count(),
            items_per_page=8
        )

        c.filters = dict(params_nopage)

        return base.render( "related/dashboard.html")

    def read(self, id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'for_view': True}
        data_dict = {'id': id}

        try:
            logic.check_access('related_show', context, data_dict)
        except logic.NotAuthorized:
            base.abort(401, _('Not authorized to see this page'))

        related = model.Session.query(model.Related).\
                    filter(model.Related.id == id).first()
        if not related:
            base.abort(404, _('The requested related item was not found'))

        related.view_count = model.Related.view_count + 1

        model.Session.add(related)
        model.Session.commit()

        base.redirect(related.url)


    def list(self, id):
        """ List all related items for a specific dataset """
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'for_view': True}
        data_dict = {'id': id}

        try:
            logic.check_access('package_show', context, data_dict)
        except logic.NotFound:
            base.abort(404, base._('Dataset not found'))
        except logic.NotAuthorized:
            base.abort(401, base._('Not authorized to see this page'))

        try:
            c.pkg_dict = logic.get_action('package_show')(context, data_dict)
            c.pkg = context['package']
            c.resources_json = h.json.dumps(c.pkg_dict.get('resources', []))
        except logic.NotFound:
            base.abort(404, base._('Dataset not found'))
        except logic.NotAuthorized:
            base.abort(401, base._('Unauthorized to read package %s') % id)

        c.action = 'related'
        c.related_count = c.pkg.related_count
        c.num_followers = _get_action('dataset_follower_count')(context,
                {'id':c.pkg.id})
        return base.render( "related/related_list.html")
