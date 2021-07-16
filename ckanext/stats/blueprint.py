# encoding: utf-8

from flask import Blueprint

from ckan.plugins.toolkit import render
import ckanext.stats.stats as stats_lib


stats = Blueprint('stats', __name__)


@stats.route('/stats')
def index():
    stats = stats_lib.Stats()
    extra_vars = {
        'largest_groups': stats.largest_groups(),
        'top_tags': stats.top_tags(),
        'top_package_creators': stats.top_package_creators(),
    }
    return render('ckanext/stats/index.html', extra_vars)
