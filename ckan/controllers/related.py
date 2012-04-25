

import ckan.model as model
import ckan.logic as logic
import ckan.lib.base as base
import ckan.lib.helpers as h

c = base.c

class RelatedController(base.BaseController):

    def list(self, id):

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'extras_as_string': True,
                   'for_view': True}
        data_dict = {'id': id}

        try:
            logic.check_access('package_show', context, data_dict)
        except logic.NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        try:
            c.pkg_dict = logic.get_action('package_show')(context, data_dict)
            c.pkg = context['package']
            c.resources_json = h.json.dumps(c.pkg_dict.get('resources',[]))
        except logic.NotFound:
            abort(404, _('Dataset not found'))
        except logic.NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % id)

        c.related_count = len(c.pkg.related)

        return base.render( "package/related_list.html")

