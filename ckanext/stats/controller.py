import ckan.plugins as p
from ckan.lib.base import BaseController, config
import stats as stats_lib

class StatsController(BaseController):

    def index(self):
        c = p.toolkit.c
        stats = stats_lib.Stats()
        rev_stats = stats_lib.RevisionStats()
        c.top_rated_packages = stats.top_rated_packages()
        c.most_edited_packages = stats.most_edited_packages()
        c.largest_groups = stats.largest_groups()
        c.top_tags = stats.top_tags()
        c.top_package_owners = stats.top_package_owners()
        c.new_packages_by_week = rev_stats.get_by_week('new_packages')
        c.deleted_packages_by_week = rev_stats.get_by_week('deleted_packages')
        c.num_packages_by_week = rev_stats.get_num_packages_by_week()
        c.package_revisions_by_week = rev_stats.get_by_week('package_revisions')
        return p.toolkit.render('ckanext/stats/index.html')

    def leaderboard(self, id=None):
        c = p.toolkit.c
        c.solr_core_url = config.get('ckanext.stats.solr_core_url',
                'http://solr.okfn.org/solr/ckan')
        return p.toolkit.render('ckanext/stats/leaderboard.html')

