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
            tag_counts = ckan.lib.stats.Stats().top_tags(limit=50,
                                            returned_tag_info='name')
            tag_counts = [ tuple(row) for row in tag_counts ]
            random.shuffle(tag_counts)
            return tag_counts
        mycache = cache.get_cache('tag_counts', type='dbm')
        # 3600=hourly, 86400=daily
        c.tag_counts = mycache.get_value(key='tag_counts_home_page',
                createfunc=tag_counts, expiretime=86400)
        return render('home/index')

    def license(self):
        return render('home/license')

    def about(self):
        return render('home/about')

    def stats(self):
        def stats_html():
            stats = ckan.lib.stats.Stats()
            rev_stats = ckan.lib.stats.RevisionStats()
            c.top_rated_packages = stats.top_rated_packages()
            c.most_edited_packages = stats.most_edited_packages()
            c.largest_groups = stats.largest_groups()
            c.top_tags = stats.top_tags()
            c.top_package_owners = stats.top_package_owners()
            c.new_packages_by_week = rev_stats.get_by_week('new_packages')
            c.package_revisions_by_week = rev_stats.get_by_week('package_revisions')
            return render('home/stats')
        if not c.user:
            mycache = cache.get_cache('stats', type='dbm')
            # 3600=hourly, 86400=daily
            stats_html = mycache.get_value(key='stats_html',
                createfunc=stats_html, expiretime=86400)
        else:
            stats_html = stats_html()
        return stats_html
            

    def cache(self, id):
        '''Manual way to clear the caches'''
        if id == 'clear':
            wui_caches = ['tag_counts', 'search_results', 'stats']
            for cache_name in wui_caches:
                cache_ = cache.get_cache(cache_name, type='dbm')
                cache_.clear()
            return 'Cleared caches: %s' % ', '.join(wui_caches)
