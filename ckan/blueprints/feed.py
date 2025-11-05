# encoding: utf-8

"""Feed blueprint - replaces ckan.controllers.feed"""

from flask import Blueprint, Response, g, abort
import ckan.logic as logic
import ckan.model as model
from ckan.common import config

feed = Blueprint('feed', __name__)


def _create_atom_feed(title, link, description, items):
    """Generate Atom feed XML"""
    from datetime import datetime

    xml = '<?xml version="1.0" encoding="utf-8"?>\n'
    xml += '<feed xmlns="http://www.w3.org/2005/Atom">\n'
    xml += '  <title>%s</title>\n' % title
    xml += '  <link href="%s"/>\n' % link
    xml += '  <updated>%s</updated>\n' % datetime.utcnow().isoformat()
    xml += '  <id>%s</id>\n' % link

    for item in items:
        xml += '  <entry>\n'
        xml += '    <title>%s</title>\n' % item.get('title', '')
        xml += '    <link href="%s"/>\n' % item.get('link', '')
        xml += '    <id>%s</id>\n' % item.get('id', '')
        xml += '    <updated>%s</updated>\n' % item.get('updated', '')
        if item.get('content'):
            xml += '    <content type="html">%s</content>\n' % item.get('content')
        xml += '  </entry>\n'

    xml += '</feed>'
    return xml


@feed.route('/group/<id>.atom')
def group(id):
    """Group activity feed"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        group_dict = logic.get_action('group_show')(context, {'id': id})
        activities = logic.get_action('group_activity_list')(
            context, {'id': id, 'limit': 20}
        )

        items = []
        for activity in activities:
            items.append({
                'title': activity.get('activity_type', ''),
                'link': config.get('ckan.site_url') + '/group/' + id,
                'id': activity.get('id', ''),
                'updated': activity.get('timestamp', ''),
                'content': str(activity.get('data', {}))
            })

        xml = _create_atom_feed(
            title='%s - Activity Feed' % group_dict['display_name'],
            link=config.get('ckan.site_url') + '/group/' + id,
            description='Recent activity in %s' % group_dict['display_name'],
            items=items
        )

        return Response(xml, mimetype='application/atom+xml')
    except logic.NotFound:
        abort(404)


@feed.route('/organization/<id>.atom')
def organization(id):
    """Organization activity feed"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        org_dict = logic.get_action('organization_show')(context, {'id': id})
        activities = logic.get_action('organization_activity_list')(
            context, {'id': id, 'limit': 20}
        )

        items = []
        for activity in activities:
            items.append({
                'title': activity.get('activity_type', ''),
                'link': config.get('ckan.site_url') + '/organization/' + id,
                'id': activity.get('id', ''),
                'updated': activity.get('timestamp', ''),
                'content': str(activity.get('data', {}))
            })

        xml = _create_atom_feed(
            title='%s - Activity Feed' % org_dict['display_name'],
            link=config.get('ckan.site_url') + '/organization/' + id,
            description='Recent activity in %s' % org_dict['display_name'],
            items=items
        )

        return Response(xml, mimetype='application/atom+xml')
    except logic.NotFound:
        abort(404)


@feed.route('/dataset.atom')
def general():
    """General dataset feed"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        packages = logic.get_action('package_search')(
            context, {'rows': 20, 'sort': 'metadata_modified desc'}
        )

        items = []
        for pkg in packages['results']:
            items.append({
                'title': pkg.get('title', ''),
                'link': config.get('ckan.site_url') + '/dataset/' + pkg['name'],
                'id': pkg.get('id', ''),
                'updated': pkg.get('metadata_modified', ''),
                'content': pkg.get('notes', '')
            })

        xml = _create_atom_feed(
            title='Recent Datasets',
            link=config.get('ckan.site_url') + '/dataset',
            description='Recently updated datasets',
            items=items
        )

        return Response(xml, mimetype='application/atom+xml')
    except Exception:
        abort(500)


@feed.route('/tag/<id>.atom')
def tag(id):
    """Tag feed"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        packages = logic.get_action('package_search')(
            context, {'fq': 'tags:' + id, 'rows': 20, 'sort': 'metadata_modified desc'}
        )

        items = []
        for pkg in packages['results']:
            items.append({
                'title': pkg.get('title', ''),
                'link': config.get('ckan.site_url') + '/dataset/' + pkg['name'],
                'id': pkg.get('id', ''),
                'updated': pkg.get('metadata_modified', ''),
                'content': pkg.get('notes', '')
            })

        xml = _create_atom_feed(
            title='Tag: %s' % id,
            link=config.get('ckan.site_url') + '/tag/' + id,
            description='Datasets tagged with %s' % id,
            items=items
        )

        return Response(xml, mimetype='application/atom+xml')
    except Exception:
        abort(500)


@feed.route('/custom.atom')
def custom():
    """Custom feed"""
    # This would allow custom queries for feeds
    return general()
