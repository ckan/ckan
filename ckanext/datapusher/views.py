# encoding: utf-8

from flask import Blueprint
from flask.views import MethodView

import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
import ckan.lib.helpers as core_helpers
import ckan.lib.base as base
from ckan.types import Context, Response

from ckan.common import _

datapusher = Blueprint(u'datapusher', __name__)


def get_blueprints():
    return [datapusher]


class ResourceDataView(MethodView):

    def post(self, id: str, resource_id: str):
        try:
            toolkit.get_action(u'datapusher_submit')(
                {}, {
                    u'resource_id': resource_id
                }
            )
        except logic.ValidationError:
            pass

        return core_helpers.redirect_to(
            u'datapusher.resource_data', id=id, resource_id=resource_id
        )

    def get(self, id: str, resource_id: str):
        try:
            pkg_dict = toolkit.get_action(u'package_show')({}, {u'id': id})
            resource = toolkit.get_action(u'resource_show'
                                          )({}, {
                                              u'id': resource_id
                                          })

            # backward compatibility with old templates
            toolkit.g.pkg_dict = pkg_dict
            toolkit.g.resource = resource

        except (logic.NotFound, logic.NotAuthorized):
            base.abort(404, _(u'Resource not found'))

        try:
            datapusher_status = toolkit.get_action(u'datapusher_status')(
                {}, {
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


@datapusher.route(
    "/dataset/<id>/delete-datastore/<resource_id>",
    methods=["POST"]
)
def delete_datastore_table(id: str, resource_id: str) -> Response:
    context: Context = {"user": toolkit.current_user.name}

    try:
        toolkit.get_action('datastore_delete')(
            context, {'resource_id': resource_id, 'force': True})
    except toolkit.NotAuthorized:
        return toolkit.abort(
            403, _('Unauthorized to delete resource {resource_id}').format(resource_id=resource_id))
    except toolkit.ObjectNotFound:
        return toolkit.abort(
            404, _('Resource not found in datastore {resource_id}').format(resource_id=resource_id))

    toolkit.h.flash_notice(
        _('DataStore and Data Dictionary '
            'deleted for resource {resource_id}').format(resource_id=resource_id))

    return toolkit.h.redirect_to(
        'datapusher.resource_data',
        id=id,
        resource_id=resource_id
    )
