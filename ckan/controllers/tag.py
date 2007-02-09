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

