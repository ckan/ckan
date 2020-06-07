# encoding: utf-8

from flask import Blueprint
from flask.views import MethodView

import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
import ckan.lib.helpers as core_helpers
import ckan.lib.base as base

from ckan.common import _

datapusher = Blueprint(u'datapusher', __name__)


class ResourceDataView(MethodView):

    def post(self, id, resource_id):
        try:
            toolkit.get_action(u'datapusher_submit')(
                None, {
                    u'resource_id': resource_id
                }
            )
        except logic.ValidationError:
            pass

        return core_helpers.redirect_to(
            u'datapusher.resource_data', id=id, resource_id=resource_id
        )

    def get(self, id, resource_id):
        try:
            pkg_dict = toolkit.get_action(u'package_show')(None, {u'id': id})
            resource = toolkit.get_action(u'resource_show'
                                          )(None, {
                                              u'id': resource_id
                                          })

            # backward compatibility with old templates
            toolkit.c.pkg_dict = pkg_dict
            toolkit.c.resource = resource

        except (logic.NotFound, logic.NotAuthorized):
            base.abort(404, _(u'Resource not found'))

        try:
            datapusher_status = toolkit.get_action(u'datapusher_status')(
                None, {
                    u'resource_id': resource_id
                }
            )
        except logic.NotFound:
            datapusher_status = {}
        except logic.NotAuthorized:
            base.abort(403, _(u'Not authorized to see this page'))

        return base.render(
            u'datapusher/resource_data.html',
            extra_vars={
                u'status': datapusher_status,
                u'pkg_dict': pkg_dict,
                u'resource': resource,
            }
        )


datapusher.add_url_rule(
    u'/dataset/<id>/resource_data/<resource_id>',
    view_func=ResourceDataView.as_view(str(u'resource_data'))
)
