# encoding: utf-8

from flask import Blueprint

from ckan.plugins.toolkit import c, render
import ckanext.stats.stats as stats_lib
import ckan.lib.helpers as h

stats = Blueprint(u'stats', __name__)


@stats.route(u'/stats')
def index():
    stats = stats_lib.Stats()
    extra_vars = {
        u'largest_groups': stats.largest_groups(),
        u'top_tags': stats.top_tags(),
        u'top_package_creators': stats.top_package_creators(),
    }
    return render(u'ckanext/stats/index.html', extra_vars)
