from ckan.lib.base import *

class TagController(BaseController):

    def index(self):
        return render_response('tag/index')

    def read(self, id):
        try:
            c.tag = model.Tag.byName(id)
        except:
            abort(404)
        return render_response('tag/read')

    def list(self):
        tags = list(model.Tag.select())
        c.tag_count = len(tags)
        c.tags = tags
        return render_response('tag/list')

