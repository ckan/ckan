# encoding: utf-8

"""Tag blueprint - replaces ckan.controllers.tag"""

from flask import Blueprint, render_template, g, abort
import ckan.logic as logic
import ckan.model as model

tag = Blueprint('tag', __name__)


@tag.route('/')
def index():
    """List all tags"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        tags = logic.get_action('tag_list')(
            context, {'all_fields': True}
        )
        return render_template('tag/index.html', tags=tags)
    except logic.NotAuthorized:
        abort(403)


@tag.route('/<id>')
def read(id):
    """View tag"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        tag_dict = logic.get_action('tag_show')(context, {'id': id})
        # Get packages with this tag
        packages = logic.get_action('package_search')(
            context, {'fq': 'tags:' + id, 'rows': 50}
        )
        return render_template('tag/read.html',
                             tag=tag_dict,
                             packages=packages['results'],
                             count=packages['count'])
    except logic.NotFound:
        abort(404)
    except logic.NotAuthorized:
        abort(403)
