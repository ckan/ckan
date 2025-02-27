# encoding: utf-8
from __future__ import annotations

import random

from flask import Blueprint
from flask.views import MethodView

from ckan import model
from ckan.plugins.toolkit import NotAuthorized, abort, h, get_action, _


resource_first = Blueprint('resource_first', __name__)


class _ResourceFirst(MethodView):
    def post(self):
        while True:
            idx = random.randrange(10**4, 10**5)
            name = f'dataset{idx}'
            if not model.Package.get(name):
                break
        try:
            pkg = get_action('package_create')(
                None, {'name': name, 'state': 'draft'})
        except NotAuthorized:
            return abort(403, _('Unauthorized to create a package'))

        return h.redirect_to('dataset_resource.new', id=pkg['id'])


resource_first.add_url_rule(
    '/resource-first/new',
    view_func=_ResourceFirst.as_view('new'),
)
