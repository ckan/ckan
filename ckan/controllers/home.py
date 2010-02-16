import random

from pylons import cache

from ckan.lib.base import *
import ckan.lib.stats

class HomeController(BaseController):
    repo = model.repo

    def index(self):
        c.package_count = model.Session.query(model.Package).count()
        c.revisions = model.Session.query(model.Revision).limit(10).all()
        def tag_counts():
            '''Top 50 tags (by package counts) in random order (to make cloud
            look nice).
            '''
            # More efficient alternative to get working:
            # sql: select tag.name, count(*) from tag join package_tag on tag.id =
            # package_tag.tag_id where pacakge_tag.state = 'active'
            # c.tags = model.Session.query(model.Tag).join('package_tag').order_by(func.count('*')).limit(100)
            tags = model.Session.query(model.Tag).all()
            # we take the name as dbm cache does not like Tag objects - get:
            # Error: can't pickle function objects
            tag_counts = [ (len(tag.packages), tag.name) for tag in tags ]
            tag_counts.sort()
            num_tags = 50
            tag_counts = tag_counts[-1:-1-num_tags:-1]
            random.shuffle(tag_counts)
            return tag_counts
        mycache = cache.get_cache('tag_counts', type='dbm')
        # 3600=hourly, 86400=daily
        c.tag_counts = mycache.get_value(key='tag_counts_home_page',
                createfunc=tag_counts, expiretime=86400)
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

    def stats(self):
        stats = ckan.lib.stats.Stats()
        c.top_rated_packages = stats.top_rated_packages()
        c.most_edited_packages = stats.most_edited_packages()
        c.largest_groups = stats.largest_groups()
        return render('home/stats')
