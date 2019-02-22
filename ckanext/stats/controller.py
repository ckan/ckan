# encoding: utf-8

import ckan.plugins as p
from ckan.lib.base import BaseController
import stats as stats_lib
import ckan.lib.helpers as h


class StatsController(BaseController):

    def index(self):
        c = p.toolkit.c
        stats = stats_lib.Stats()
        rev_stats = stats_lib.RevisionStats()
        c.top_rated_packages = stats.top_rated_packages()
        c.largest_groups = stats.largest_groups()
        c.top_tags = stats.top_tags()
        c.top_package_creators = stats.top_package_creators()

        return p.toolkit.render('ckanext/stats/index.html')
