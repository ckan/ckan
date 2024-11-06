from flask import Blueprint

from ckan.plugins.toolkit import _, h, g, render, request, abort, NotAuthorized, get_action, ObjectNotFound

import ckanext.xloader.utils as utils


xloader = Blueprint("xloader", __name__)


def get_blueprints():
    return [xloader]


@xloader.route("/dataset/<id>/resource_data/<resource_id>", methods=("GET", "POST"))
def resource_data(id, resource_id):
    rows = request.args.get('rows')
    if rows:
        try:
            rows = int(rows)
            if rows < 0:
                rows = None
        except ValueError:
            rows = None
    return utils.resource_data(id, resource_id, rows)


@xloader.route("/dataset/<id>/delete-datastore/<resource_id>", methods=("GET", "POST"))
def delete_datastore_table(id, resource_id):
    if u'cancel' in request.form:
        return h.redirect_to(u'xloader.resource_data', id=id, resource_id=resource_id)

    context = {"user": g.user}

    try:
        res_dict = get_action('resource_show')(context, {"id": resource_id})
        if res_dict.get('package_id') != id:
            raise ObjectNotFound
    except ObjectNotFound:
        return abort(404, _(u'Resource not found'))

    if request.method == 'POST':
        try:
            get_action('datastore_delete')(context, {
                "resource_id": resource_id,
                "force": True})
        except NotAuthorized:
            return abort(403, _(u'Unauthorized to delete resource %s') % resource_id)

        h.flash_notice(_(u'DataStore and Data Dictionary deleted for resource %s') % resource_id)

        return h.redirect_to(
            'xloader.resource_data',
            id=id,
            resource_id=resource_id
        )
    else:
        g.resource_id = resource_id
        g.package_id = id

        extra_vars = {
            u"resource_id": resource_id,
            u"package_id": id
        }
        return render(u'xloader/confirm_datastore_delete.html', extra_vars)
