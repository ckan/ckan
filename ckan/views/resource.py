# encoding: utf-8
import cgi
import json
import logging

import flask
from flask.views import MethodView

import six
import ckan.lib.base as base
import ckan.lib.datapreview as lib_datapreview
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.lib.uploader as uploader
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as plugins
from ckan.common import _, g, request
from ckan.views.home import CACHE_PARAMETERS
from ckan.views.dataset import (
    _get_pkg_template, _get_package_type, _setup_template_variables
)

Blueprint = flask.Blueprint
NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
check_access = logic.check_access
get_action = logic.get_action
tuplize_dict = logic.tuplize_dict
clean_dict = logic.clean_dict
parse_params = logic.parse_params
flatten_to_string_key = logic.flatten_to_string_key

log = logging.getLogger(__name__)

resource = Blueprint(
    u'dataset_resource',
    __name__,
    url_prefix=u'/dataset/<id>/resource',
    url_defaults={u'package_type': u'dataset'}
)
prefixed_resource = Blueprint(
    u'resource',
    __name__,
    url_prefix=u'/dataset/<id>/resource',
    url_defaults={u'package_type': u'dataset'}
)


def read(package_type, id, resource_id):
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj,
        u'for_view': True
    }

    try:
        package = get_action(u'package_show')(context, {u'id': id})
    except (NotFound, NotAuthorized):
        return base.abort(404, _(u'Dataset not found'))
    activity_id = request.params.get(u'activity_id')
    if activity_id:
        # view an 'old' version of the package, as recorded in the
        # activity stream
        current_pkg = package
        try:
            package = context['session'].query(model.Activity).get(
                activity_id
            ).data['package']
        except AttributeError:
            base.abort(404, _(u'Dataset not found'))

        if package['id'] != current_pkg['id']:
            log.info(u'Mismatch between pkg id in activity and URL {} {}'
                     .format(package['id'], current_pkg['id']))
            # the activity is not for the package in the URL - don't allow
            # misleading URLs as could be malicious
            base.abort(404, _(u'Activity not found'))
        # The name is used lots in the template for links, so fix it to be
        # the current one. It's not displayed to the user anyway.
        package['name'] = current_pkg['name']

        # Don't crash on old (unmigrated) activity records, which do not
        # include resources or extras.
        package.setdefault(u'resources', [])

    resource = None
    for res in package.get(u'resources', []):
        if res[u'id'] == resource_id:
            resource = res
            break
    if not resource:
        return base.abort(404, _(u'Resource not found'))

    # get package license info
    license_id = package.get(u'license_id')
    try:
        package[u'isopen'] = model.Package.get_license_register()[license_id
                                                                  ].isopen()
    except KeyError:
        package[u'isopen'] = False

    resource_views = get_action(u'resource_view_list')(
        context, {
            u'id': resource_id
        }
    )
    resource[u'has_views'] = len(resource_views) > 0

    current_resource_view = None
    view_id = request.args.get(u'view_id')
    if resource[u'has_views']:
        if view_id:
            current_resource_view = [
                rv for rv in resource_views if rv[u'id'] == view_id
            ]
            if len(current_resource_view) == 1:
                current_resource_view = current_resource_view[0]
            else:
                return base.abort(404, _(u'Resource view not found'))
        else:
            current_resource_view = resource_views[0]

    # required for nav menu
    pkg = context[u'package']
    dataset_type = pkg.type or package_type

    # TODO: remove
    g.package = package
    g.resource = resource
    g.pkg = pkg
    g.pkg_dict = package

    extra_vars = {
        u'resource_views': resource_views,
        u'current_resource_view': current_resource_view,
        u'dataset_type': dataset_type,
        u'pkg_dict': package,
        u'package': package,
        u'resource': resource,
        u'pkg': pkg,  # NB it is the current version of the dataset, so ignores
                      # activity_id. Still used though in resource views for
                      # backward compatibility
        u'is_activity_archive': bool(activity_id),
    }

    template = _get_pkg_template(u'resource_template', dataset_type)
    return base.render(template, extra_vars)


def download(package_type, id, resource_id, filename=None):
    """
    Provides a direct download by either redirecting the user to the url
    stored or downloading an uploaded file directly.
    """
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj
    }

    try:
        rsc = get_action(u'resource_show')(context, {u'id': resource_id})
        get_action(u'package_show')(context, {u'id': id})
    except (NotFound, NotAuthorized):
        return base.abort(404, _(u'Resource not found'))

    if rsc.get(u'url_type') == u'upload':
        upload = uploader.get_resource_uploader(rsc)
        filepath = upload.get_path(rsc[u'id'])
        return flask.send_file(filepath)
    elif u'url' not in rsc:
        return base.abort(404, _(u'No download is available'))
    return h.redirect_to(rsc[u'url'])


class CreateView(MethodView):
    def post(self, package_type, id):
        save_action = request.form.get(u'save')
        data = clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
        )
        data.update(clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.files)))
        ))

        # we don't want to include save as it is part of the form
        del data[u'save']
        resource_id = data.pop(u'id')

        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }

        # see if we have any data that we are trying to save
        data_provided = False
        for key, value in six.iteritems(data):
            if (
                    (value or isinstance(value, cgi.FieldStorage))
                    and key != u'resource_type'):
                data_provided = True
                break

        if not data_provided and save_action != u"go-dataset-complete":
            if save_action == u'go-dataset':
                # go to final stage of adddataset
                return h.redirect_to(u'{}.edit'.format(package_type), id=id)
            # see if we have added any resources
            try:
                data_dict = get_action(u'package_show')(context, {u'id': id})
            except NotAuthorized:
                return base.abort(403, _(u'Unauthorized to update dataset'))
            except NotFound:
                return base.abort(
                    404,
                    _(u'The dataset {id} could not be found.').format(id=id)
                )
            if not len(data_dict[u'resources']):
                # no data so keep on page
                msg = _(u'You must add at least one data resource')
                # On new templates do not use flash message

                errors = {}
                error_summary = {_(u'Error'): msg}
                return self.get(package_type, id, data, errors, error_summary)

            # XXX race condition if another user edits/deletes
            data_dict = get_action(u'package_show')(context, {u'id': id})
            get_action(u'package_update')(
                dict(context, allow_state_change=True),
                dict(data_dict, state=u'active')
            )
            return h.redirect_to(u'{}.read'.format(package_type), id=id)

        data[u'package_id'] = id
        try:
            if resource_id:
                data[u'id'] = resource_id
                get_action(u'resource_update')(context, data)
            else:
                get_action(u'resource_create')(context, data)
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            if data.get(u'url_type') == u'upload' and data.get(u'url'):
                data[u'url'] = u''
                data[u'url_type'] = u''
                data[u'previous_upload'] = True
            return self.get(package_type, id, data, errors, error_summary)
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized to create a resource'))
        except NotFound:
            return base.abort(
                404, _(u'The dataset {id} could not be found.').format(id=id)
            )
        if save_action == u'go-metadata':
            # XXX race condition if another user edits/deletes
            data_dict = get_action(u'package_show')(context, {u'id': id})
            get_action(u'package_update')(
                dict(context, allow_state_change=True),
                dict(data_dict, state=u'active')
            )
            return h.redirect_to(u'{}.read'.format(package_type), id=id)
        elif save_action == u'go-dataset':
            # go to first stage of add dataset
            return h.redirect_to(u'{}.edit'.format(package_type), id=id)
        elif save_action == u'go-dataset-complete':

            return h.redirect_to(u'{}.read'.format(package_type), id=id)
        else:
            # add more resources
            return h.redirect_to(
                u'{}_resource.new'.format(package_type),
                id=id
            )

    def get(
        self, package_type, id, data=None, errors=None, error_summary=None
    ):
        # get resources for sidebar
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        try:
            pkg_dict = get_action(u'package_show')(context, {u'id': id})
        except NotFound:
            return base.abort(
                404, _(u'The dataset {id} could not be found.').format(id=id)
            )
        try:
            check_access(
                u'resource_create', context, {u"package_id": pkg_dict["id"]}
            )
        except NotAuthorized:
            return base.abort(
                403, _(u'Unauthorized to create a resource for this package')
            )

        package_type = pkg_dict[u'type'] or package_type

        errors = errors or {}
        error_summary = error_summary or {}
        extra_vars = {
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary,
            u'action': u'new',
            u'resource_form_snippet': _get_pkg_template(
                u'resource_form', package_type
            ),
            u'dataset_type': package_type,
            u'pkg_name': id,
            u'pkg_dict': pkg_dict
        }
        template = u'package/new_resource_not_draft.html'
        if pkg_dict[u'state'].startswith(u'draft'):
            extra_vars[u'stage'] = ['complete', u'active']
            template = u'package/new_resource.html'
        return base.render(template, extra_vars)


class EditView(MethodView):
    def _prepare(self, id):
        context = {
            u'model': model,
            u'session': model.Session,
            u'api_version': 3,
            u'for_edit': True,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        try:
            check_access(u'package_update', context, {u'id': id})
        except NotAuthorized:
            return base.abort(
                403,
                _(u'User %r not authorized to edit %s') % (g.user, id)
            )
        return context

    def post(self, package_type, id, resource_id):
        context = self._prepare(id)
        data = clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
        )
        data.update(clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.files)))
        ))

        # we don't want to include save as it is part of the form
        del data[u'save']

        data[u'package_id'] = id
        try:
            if resource_id:
                data[u'id'] = resource_id
                get_action(u'resource_update')(context, data)
            else:
                get_action(u'resource_create')(context, data)
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(
                package_type, id, resource_id, data, errors, error_summary
            )
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized to edit this resource'))
        return h.redirect_to(
            u'{}_resource.read'.format(package_type),
            id=id, resource_id=resource_id
        )

    def get(
        self,
        package_type,
        id,
        resource_id,
        data=None,
        errors=None,
        error_summary=None
    ):
        context = self._prepare(id)
        pkg_dict = get_action(u'package_show')(context, {u'id': id})

        try:
            resource_dict = get_action(u'resource_show')(
                context, {
                    u'id': resource_id
                }
            )
        except NotFound:
            return base.abort(404, _(u'Resource not found'))

        if pkg_dict[u'state'].startswith(u'draft'):
            return CreateView().get(package_type, id, data=resource_dict)

        # resource is fully created
        resource = resource_dict
        # set the form action
        form_action = h.url_for(
            u'{}_resource.edit'.format(package_type),
            resource_id=resource_id, id=id
        )
        if not data:
            data = resource_dict

        package_type = pkg_dict[u'type'] or package_type

        errors = errors or {}
        error_summary = error_summary or {}
        extra_vars = {
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary,
            u'action': u'edit',
            u'resource_form_snippet': _get_pkg_template(
                u'resource_form', package_type
            ),
            u'dataset_type': package_type,
            u'resource': resource,
            u'pkg_dict': pkg_dict,
            u'form_action': form_action
        }
        return base.render(u'package/resource_edit.html', extra_vars)


class DeleteView(MethodView):
    def _prepare(self, id):
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        try:
            check_access(u'package_delete', context, {u'id': id})
        except NotAuthorized:
            return base.abort(
                403,
                _(u'Unauthorized to delete package %s') % u''
            )
        return context

    def post(self, package_type, id, resource_id):
        if u'cancel' in request.form:
            return h.redirect_to(
                u'{}_resource.edit'.format(package_type),
                resource_id=resource_id, id=id
            )
        context = self._prepare(id)

        try:
            get_action(u'resource_delete')(context, {u'id': resource_id})
            h.flash_notice(_(u'Resource has been deleted.'))
            pkg_dict = get_action(u'package_show')(None, {u'id': id})
            if pkg_dict[u'state'].startswith(u'draft'):
                return h.redirect_to(
                    u'{}_resource.new'.format(package_type),
                    id=id
                )
            else:
                return h.redirect_to(u'{}.read'.format(package_type), id=id)
        except NotAuthorized:
            return base.abort(
                403,
                _(u'Unauthorized to delete resource %s') % u''
            )
        except NotFound:
            return base.abort(404, _(u'Resource not found'))

    def get(self, package_type, id, resource_id):
        context = self._prepare(id)
        try:
            resource_dict = get_action(u'resource_show')(
                context, {
                    u'id': resource_id
                }
            )
            pkg_id = id
        except NotAuthorized:
            return base.abort(
                403,
                _(u'Unauthorized to delete resource %s') % u''
            )
        except NotFound:
            return base.abort(404, _(u'Resource not found'))

        # TODO: remove
        g.resource_dict = resource_dict
        g.pkg_id = pkg_id

        return base.render(
            u'package/confirm_delete_resource.html', {
                u'dataset_type': _get_package_type(id),
                u'resource_dict': resource_dict,
                u'pkg_id': pkg_id
            }
        )


def views(package_type, id, resource_id):
    package_type = _get_package_type(id)
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'for_view': True,
        u'auth_user_obj': g.userobj
    }
    data_dict = {u'id': id}

    try:
        check_access(u'package_update', context, data_dict)
    except NotAuthorized:
        return base.abort(
            403,
            _(u'User %r not authorized to edit %s') % (g.user, id)
        )
    # check if package exists
    try:
        pkg_dict = get_action(u'package_show')(context, data_dict)
        pkg = context[u'package']
    except (NotFound, NotAuthorized):
        return base.abort(404, _(u'Dataset not found'))

    try:
        resource = get_action(u'resource_show')(context, {u'id': resource_id})
        views = get_action(u'resource_view_list')(
            context, {
                u'id': resource_id
            }
        )

    except NotFound:
        return base.abort(404, _(u'Resource not found'))
    except NotAuthorized:
        return base.abort(403, _(u'Unauthorized to read resource %s') % id)

    _setup_template_variables(context, {u'id': id}, package_type=package_type)

    # TODO: remove
    g.pkg_dict = pkg_dict
    g.pkg = pkg
    g.resource = resource
    g.views = views

    return base.render(
        u'package/resource_views.html', {
            u'pkg_dict': pkg_dict,
            u'pkg': pkg,
            u'resource': resource,
            u'views': views
        }
    )


def view(package_type, id, resource_id, view_id=None):
    """
    Embedded page for a resource view.

    Depending on the type, different views are loaded. This could be an
    img tag where the image is loaded directly or an iframe that embeds a
    webpage or a recline preview.
    """
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj
    }

    try:
        package = get_action(u'package_show')(context, {u'id': id})
    except (NotFound, NotAuthorized):
        return base.abort(404, _(u'Dataset not found'))

    try:
        resource = get_action(u'resource_show')(context, {u'id': resource_id})
    except (NotFound, NotAuthorized):
        return base.abort(404, _(u'Resource not found'))

    view = None
    if request.params.get(u'resource_view', u''):
        try:
            view = json.loads(request.params.get(u'resource_view', u''))
        except ValueError:
            return base.abort(409, _(u'Bad resource view data'))
    elif view_id:
        try:
            view = get_action(u'resource_view_show')(context, {u'id': view_id})
        except (NotFound, NotAuthorized):
            return base.abort(404, _(u'Resource view not found'))

    if not view or not isinstance(view, dict):
        return base.abort(404, _(u'Resource view not supplied'))

    return h.rendered_resource_view(view, resource, package, embed=True)


# FIXME: could anyone think about better name?
class EditResourceViewView(MethodView):
    def _prepare(self, id, resource_id):
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'for_view': True,
            u'auth_user_obj': g.userobj
        }

        # update resource should tell us early if the user has privilages.
        try:
            check_access(u'resource_update', context, {u'id': resource_id})
        except NotAuthorized:
            return base.abort(
                403,
                _(u'User %r not authorized to edit %s') % (g.user, id)
            )

        # get resource and package data
        try:
            pkg_dict = get_action(u'package_show')(context, {u'id': id})
            pkg = context[u'package']
        except (NotFound, NotAuthorized):
            return base.abort(404, _(u'Dataset not found'))
        try:
            resource = get_action(u'resource_show')(
                context, {
                    u'id': resource_id
                }
            )
        except (NotFound, NotAuthorized):
            return base.abort(404, _(u'Resource not found'))

        # TODO: remove
        g.pkg_dict = pkg_dict
        g.pkg = pkg
        g.resource = resource

        extra_vars = dict(
            data={},
            errors={},
            error_summary={},
            view_type=None,
            to_preview=False,
            pkg_dict=pkg_dict,
            pkg=pkg,
            resource=resource
        )
        return context, extra_vars

    def post(self, package_type, id, resource_id, view_id=None):
        context, extra_vars = self._prepare(id, resource_id)
        data = clean_dict(
            dict_fns.unflatten(
                tuplize_dict(
                    parse_params(request.form, ignore_keys=CACHE_PARAMETERS)
                )
            )
        )
        data.pop(u'save', None)

        to_preview = data.pop(u'preview', False)
        if to_preview:
            context[u'preview'] = True
        to_delete = data.pop(u'delete', None)
        data[u'resource_id'] = resource_id
        data[u'view_type'] = request.args.get(u'view_type')

        try:
            if to_delete:
                data[u'id'] = view_id
                get_action(u'resource_view_delete')(context, data)
            elif view_id:
                data[u'id'] = view_id
                data = get_action(u'resource_view_update')(context, data)
            else:
                data = get_action(u'resource_view_create')(context, data)
        except ValidationError as e:
            # Could break preview if validation error
            to_preview = False
            extra_vars[u'errors'] = e.error_dict,
            extra_vars[u'error_summary'] = e.error_summary
        except NotAuthorized:
            # This should never happen unless the user maliciously changed
            # the resource_id in the url.
            return base.abort(403, _(u'Unauthorized to edit resource'))
        else:
            if not to_preview:
                return h.redirect_to(
                    u'{}_resource.views'.format(package_type),
                    id=id, resource_id=resource_id
                )
        extra_vars[u'data'] = data
        extra_vars[u'to_preview'] = to_preview
        return self.get(package_type, id, resource_id, view_id, extra_vars)

    def get(
        self, package_type, id, resource_id, view_id=None, post_extra=None
    ):
        context, extra_vars = self._prepare(id, resource_id)
        to_preview = extra_vars[u'to_preview']
        if post_extra:
            extra_vars.update(post_extra)

        package_type = _get_package_type(id)
        data = extra_vars[u'data'] if u'data' in extra_vars else None
        if data and u'view_type' in data:
            view_type = data.get(u'view_type')
        else:
            view_type = request.args.get(u'view_type')

        # view_id exists only when updating
        if view_id:
            if not data or not view_type:
                try:
                    view_data = get_action(u'resource_view_show')(
                        context, {
                            u'id': view_id
                        }
                    )
                    view_type = view_data[u'view_type']
                    if data:
                        data.update(view_data)
                    else:
                        data = view_data
                except (NotFound, NotAuthorized):
                    return base.abort(404, _(u'View not found'))

            # might as well preview when loading good existing view
            if not extra_vars[u'errors']:
                to_preview = True

        data[u'view_type'] = view_type
        view_plugin = lib_datapreview.get_view_plugin(view_type)
        if not view_plugin:
            return base.abort(404, _(u'View Type Not found'))

        _setup_template_variables(
            context, {u'id': id}, package_type=package_type
        )

        data_dict = {
            u'package': extra_vars[u'pkg_dict'],
            u'resource': extra_vars[u'resource'],
            u'resource_view': data
        }

        view_template = view_plugin.view_template(context, data_dict)
        form_template = view_plugin.form_template(context, data_dict)

        extra_vars.update({
            u'form_template': form_template,
            u'view_template': view_template,
            u'data': data,
            u'to_preview': to_preview,
            u'datastore_available': plugins.plugin_loaded(u'datastore')
        })
        extra_vars.update(
            view_plugin.setup_template_variables(context, data_dict) or {}
        )
        extra_vars.update(data_dict)

        if view_id:
            return base.render(u'package/edit_view.html', extra_vars)

        return base.render(u'package/new_view.html', extra_vars)


def _parse_recline_state(params):
    state_version = int(request.args.get(u'state_version', u'1'))
    if state_version != 1:
        return None

    recline_state = {}
    for k, v in request.args.items():
        try:
            v = h.json.loads(v)
        except ValueError:
            pass
        recline_state[k] = v

    recline_state.pop(u'width', None)
    recline_state.pop(u'height', None)
    recline_state[u'readOnly'] = True

    # previous versions of recline setup used elasticsearch_url attribute
    # for data api url - see http://trac.ckan.org/ticket/2639
    # fix by relocating this to url attribute which is the default location
    if u'dataset' in recline_state and u'elasticsearch_url' in recline_state[
        u'dataset'
    ]:
        recline_state[u'dataset'][u'url'] = recline_state[u'dataset'][
            u'elasticsearch_url'
        ]

    # Ensure only the currentView is available
    # default to grid view if none specified
    if not recline_state.get(u'currentView', None):
        recline_state[u'currentView'] = u'grid'
    for k in recline_state.keys():
        if k.startswith(u'view-') and \
                not k.endswith(recline_state[u'currentView']):
            recline_state.pop(k)
    return recline_state


def embedded_dataviewer(package_type, id, resource_id, width=500, height=500):
    """
    Embedded page for a read-only resource dataview. Allows
    for width and height to be specified as part of the
    querystring (as well as accepting them via routes).
    """
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj
    }

    try:
        resource = get_action(u'resource_show')(context, {u'id': resource_id})
        package = get_action(u'package_show')(context, {u'id': id})
        resource_json = h.json.dumps(resource)

        # double check that the resource belongs to the specified package
        if not resource[u'id'] in [r[u'id'] for r in package[u'resources']]:
            raise NotFound
        dataset_type = package[u'type'] or package_type

    except (NotFound, NotAuthorized):
        return base.abort(404, _(u'Resource not found'))

    # Construct the recline state
    state_version = int(request.args.get(u'state_version', u'1'))
    recline_state = _parse_recline_state(request.args)
    if recline_state is None:
        return base.abort(
            400, (
                u'"state" parameter must be a valid recline '
                u'state (version %d)' % state_version
            )
        )

    recline_state = h.json.dumps(recline_state)

    width = max(int(request.args.get(u'width', width)), 100)
    height = max(int(request.args.get(u'height', height)), 100)
    embedded = True

    # TODO: remove
    g.resource = resource
    g.package = package
    g.resource_json = resource_json
    g.recline_state = recline_state
    g.width = width
    g.height = height
    g.embedded = embedded

    return base.render(
        u'package/resource_embedded_dataviewer.html', {
            u'dataset_type': dataset_type,
            u'resource': resource,
            u'package': package,
            u'resource_json': resource_json,
            u'width': width,
            u'height': height,
            u'embedded': embedded,
            u'recline_state': recline_state
        }
    )


def datapreview(package_type, id, resource_id):
    """
    Embedded page for a resource data-preview.

    Depending on the type, different previews are loaded.  This could be an
    img tag where the image is loaded directly or an iframe that embeds a
    webpage, or a recline preview.
    """
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj
    }

    try:
        resource = get_action(u'resource_show')(context, {u'id': resource_id})
        package = get_action(u'package_show')(context, {u'id': id})

        data_dict = {u'resource': resource, u'package': package}

        preview_plugin = lib_datapreview.get_preview_plugin(data_dict)

        if preview_plugin is None:
            return base.abort(409, _(u'No preview has been defined.'))

        preview_plugin.setup_template_variables(context, data_dict)
        resource_json = json.dumps(resource)
        dataset_type = package[u'type'] or package_type

        # TODO: remove
        g.resource = resource
        g.package = package
        g.resource_json = resource_json

    except (NotFound, NotAuthorized):
        return base.abort(404, _(u'Resource not found'))
    else:
        return base.render(
            preview_plugin.preview_template(context, data_dict), {
                u'dataset_type': dataset_type,
                u'resource': resource,
                u'package': package,
                u'resource_json': resource_json
            }
        )


def register_dataset_plugin_rules(blueprint):
    blueprint.add_url_rule(u'/new', view_func=CreateView.as_view(str(u'new')))
    blueprint.add_url_rule(
        u'/<resource_id>', view_func=read, strict_slashes=False)
    blueprint.add_url_rule(
        u'/<resource_id>/edit', view_func=EditView.as_view(str(u'edit'))
    )
    blueprint.add_url_rule(
        u'/<resource_id>/delete', view_func=DeleteView.as_view(str(u'delete'))
    )

    blueprint.add_url_rule(u'/<resource_id>/download', view_func=download)
    blueprint.add_url_rule(u'/<resource_id>/views', view_func=views)
    blueprint.add_url_rule(u'/<resource_id>/view', view_func=view)
    blueprint.add_url_rule(u'/<resource_id>/view/<view_id>', view_func=view)
    blueprint.add_url_rule(
        u'/<resource_id>/download/<filename>', view_func=download
    )

    _edit_view = EditResourceViewView.as_view(str(u'edit_view'))
    blueprint.add_url_rule(u'/<resource_id>/new_view', view_func=_edit_view)
    blueprint.add_url_rule(
        u'/<resource_id>/edit_view/<view_id>', view_func=_edit_view
    )
    blueprint.add_url_rule(
        u'/<resource_id>/embed', view_func=embedded_dataviewer)
    blueprint.add_url_rule(
        u'/<resource_id>/viewer',
        view_func=embedded_dataviewer,
        defaults={
            u'width': u"960",
            u'height': u"800"
        }
    )
    blueprint.add_url_rule(u'/<resource_id>/preview', view_func=datapreview)


register_dataset_plugin_rules(resource)
register_dataset_plugin_rules(prefixed_resource)
