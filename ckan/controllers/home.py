import random

from pylons import cache

from ckan.lib.base import *

class HomeController(BaseController):
    repo = model.repo

    def index(self):
        c.package_count = model.Session.query(model.Package).count()
        c.revisions = model.Session.query(model.Revision).limit(10).all()
        def tag_counts():
            # More efficient alternative to get working:
            # sql: select tag.name, count(*) from tag join package_tag on tag.id =
            # package_tag.tag_id where pacakge_tag.state = 'active'
            # c.tags = model.Session.query(model.Tag).join('package_tag').order_by(func.count('*')).limit(100)
            tags = model.Session.query(model.Tag).all()
            tag_counts = [ (len(tag.packages), tag) for tag in tags ]
            tag_counts.sort()
            num_tags = 50
            tag_counts = tag_counts[-1:-1-num_tags:-1]
            random.shuffle(tag_counts)
            return tag_counts
        mycache = cache.get_cache('tag_counts', type="memory")
        c.tag_counts = mycache.get_value(key=None, createfunc=tag_counts,
                                         expiretime=3600) # 3600 = every hour
        return render('home/index')

    def license(self):
        return render('home/license')
    
    def guide(self):
        ckan_pkg = model.Package.by_name(u'ckan')
        if ckan_pkg:
            c.info = ckan_pkg.notes
        else:
            c.info = ''
        return render('home/guide')

    def about(self):
        return render('home/about')

