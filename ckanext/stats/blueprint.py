# encoding: utf-8
from __future__ import annotations
from typing import Any
from flask import Blueprint
from ckan import plugins as p
from ckan.plugins.toolkit import render, h
import ckanext.stats.stats as stats_lib


stats = Blueprint(u'stats', __name__)


@stats.route(u'/stats')
def index():
    stats = stats_lib.Stats()
    # Public stats
    extra_vars: dict[str, Any] = {
        'largest_groups': stats.largest_groups(),
        'top_tags': stats.top_tags(),
        'most_edited_packages': stats.most_edited_packages(),
        'new_packages_by_week': stats.get_by_week('new_packages'),
        'deleted_packages_by_week': stats.get_by_week('deleted_packages'),
        'num_packages_by_week': stats.get_num_packages_by_week(),
        'package_revisions_by_week': stats.get_by_week('package_revisions'),
        'top_package_creators': stats.top_package_creators(),
    }

    extra_vars['raw_packages_by_week'] = []
    for week_date, num_packages, cumulative_num_packages\
            in stats.get_num_packages_by_week():
        extra_vars['raw_packages_by_week'].append(
            {'date': h.date_str_to_datetime(week_date),
             'total_packages': cumulative_num_packages})

    extra_vars['raw_all_package_revisions'] = []
    for week_date, _revs, num_revisions, _cumulative_num_revisions\
            in stats.get_by_week('package_revisions'):
        extra_vars['raw_all_package_revisions'].append(
            {'date': h.date_str_to_datetime(week_date),
             'total_revisions': num_revisions})

    extra_vars['raw_new_datasets'] = []
    for week_date, _pkgs, num_packages, _cumulative_num_revisions\
            in stats.get_by_week('new_packages'):
        extra_vars['raw_new_datasets'].append(
            {'date': h.date_str_to_datetime(week_date),
             'new_packages': num_packages})

    extra_vars['raw_deleted_datasets'] = []
    for week_date, _pkgs, num_packages, cumulative_num_packages\
            in stats.get_by_week('deleted_packages'):
        extra_vars['raw_deleted_datasets'].append(
            {'date': h.date_str_to_datetime(
                week_date), 'deleted_packages': num_packages})

    base_templates = 'ckanext/stats/'
    templates = {
        'raw_packages_by_week': base_templates + 'raw_packages_by_week.html',
        'raw_all_package_revisions': base_templates + 'raw_all_package_revisions.html',
    }
    extra_vars['templates'] = templates
    # Allow IStats interface to modify the stats
    for item in p.PluginImplementations(p.IStats):
        item.after_stats(extra_vars)

    return render(u'ckanext/stats/index.html', extra_vars)
