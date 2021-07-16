# encoding: utf-8

from flask import Blueprint
from flask.views import MethodView

import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
import ckan.lib.helpers as core_helpers
import ckan.lib.base as base

from ckan.common import _

datapusher = Blueprint('datapusher', __name__)


def get_blueprints():
    return [datapusher]


class ResourceDataView(MethodView):

    def post(self, id, resource_id):
        try:
            toolkit.get_action('datapusher_submit')(
                None, {
                    'resource_id': resource_id
                }
            )
        except logic.ValidationError:
            pass

        return core_helpers.redirect_to(
            'datapusher.resource_data', id=id, resource_id=resource_id
        )

    def get(self, id, resource_id):
        try:
            pkg_dict = toolkit.get_action('package_show')(None, {'id': id})
            resource = toolkit.get_action('resource_show'
                                          )(None, {
                                              'id': resource_id
                                          })

            # backward compatibility with old templates
            toolkit.c.pkg_dict = pkg_dict
            toolkit.c.resource = resource

        except (logic.NotFound, logic.NotAuthorized):
            base.abort(404, _('Resource not found'))

        try:
            datapusher_status = toolkit.get_action('datapusher_status')(
                None, {
                    'resource_id': resource_id
                }
            )
        except logic.NotFound:
            datapusher_status = {}
        except logic.NotAuthorized:
            base.abort(403, _('Not authorized to see this page'))

        return base.render(
            'datapusher/resource_data.html',
            extra_vars={
                'status': datapusher_status,
                'pkg_dict': pkg_dict,
                'resource': resource,
            }
        )


datapusher.add_url_rule(
    '/dataset/<id>/resource_data/<resource_id>',
    view_func=ResourceDataView.as_view(str('resource_data'))
)
