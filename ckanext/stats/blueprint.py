# encoding: utf-8

from flask import Blueprint

from ckan.plugins.toolkit import c, render
import ckanext.stats.stats as stats_lib
import ckan.lib.helpers as h

stats = Blueprint(u'stats', __name__)


def index():
    stats = stats_lib.Stats()
    rev_stats = stats_lib.RevisionStats()
    c.top_rated_packages = stats.top_rated_packages()
    c.most_edited_packages = stats.most_edited_packages()
    c.largest_groups = stats.largest_groups()
    c.top_tags = stats.top_tags()
    c.top_package_creators = stats.top_package_creators()
    c.new_packages_by_week = rev_stats.get_by_week(u'new_packages')
    c.deleted_packages_by_week = rev_stats.get_by_week(u'deleted_packages')
    c.num_packages_by_week = rev_stats.get_num_packages_by_week()
    c.package_revisions_by_week = rev_stats.get_by_week(u'package_revisions')

    c.raw_packages_by_week = []
    for (
        week_date, num_packages, cumulative_num_packages
    ) in c.num_packages_by_week:
        c.raw_packages_by_week.append({
            u'date': h.date_str_to_datetime(week_date),
            u'total_packages': cumulative_num_packages
        })

    c.all_package_revisions = []
    c.raw_all_package_revisions = []
    for (
        week_date, revs, num_revisions, cumulative_num_revisions
    ) in c.package_revisions_by_week:
        c.all_package_revisions.append(
            u'[new Date(%s), %s]' %
            (week_date.replace(u'-', u','), num_revisions)
        )
        c.raw_all_package_revisions.append({
            u'date': h.date_str_to_datetime(week_date),
            u'total_revisions': num_revisions
        })

    c.new_datasets = []
    c.raw_new_datasets = []
    for (
        week_date, pkgs, num_packages, cumulative_num_packages
    ) in c.new_packages_by_week:
        c.new_datasets.append(
            u'[new Date(%s), %s]' %
            (week_date.replace(u'-', u','), num_packages)
        )
        c.raw_new_datasets.append({
            u'date': h.date_str_to_datetime(week_date),
            u'new_packages': num_packages
        })

    return render(u'ckanext/stats/index.html')


stats.add_url_rule(u'/stats', view_func=index)
