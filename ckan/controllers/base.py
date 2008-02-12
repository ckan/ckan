from ckan.lib.base import *

class CkanBaseController(BaseController):

    def __before__(self, action, **params):
        # what is different between session['user'] and environ['REMOTE_USER']
        c.user = request.environ.get('REMOTE_USER', None)
        c.remote_addr = request.environ.get('REMOTE_ADDR', 'Unknown IP Address')
        if c.remote_addr == 'localhost' or c.remote_addr == '127.0.0.1':
            # see if it was proxied
            c.remote_addr = request.environ.get('HTTP_X_FORWARDED_FOR',
                    '127.0.0.1')
        if c.user:
            c.author = c.user
        else:
            c.author = c.remote_addr
        c.has_paginate = False
        c.has_autocomplete = False

    def _paginate_list(self, register_name, id, template_path):
        c.has_paginate = True
        try:
            current_page = int(id)
        except:
            current_page = 0
        rev = self.repo.youngest_revision()
        register = getattr(rev.model, register_name)
        import paginate
        collection = register.list()
        item_count = len(collection)
        c.page = paginate.Page(
            collection=collection,
            current_page=current_page,
            items_per_page=50,
            item_count=item_count,
        )
        c.register_name = register_name
        if 'paginatedlist' in request.params:
            template_path = 'paginated_list_contents'
        return render(template_path)


