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
    'dataset_resource',
    __name__,
    url_prefix='/dataset/<id>/resource',
    url_defaults={'package_type': 'dataset'}
)
prefixed_resource = Blueprint(
    'resource',
    __name__,
    url_prefix='/dataset/<id>/resource',
    url_defaults={'package_type': 'dataset'}
)


def read(package_type, id, resource_id):
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'auth_user_obj': g.userobj,
        'for_view': True
    }

    try:
        package = get_action('package_show')(context, {'id': id})
    except (NotFound, NotAuthorized):
        return base.abort(404, _('Dataset not found'))
    activity_id = request.params.get('activity_id')
    if activity_id:
        # view an 'old' version of the package, as recorded in the
        # activity stream
        current_pkg = package
        try:
            package = context['session'].query(model.Activity).get(
                activity_id
            ).data['package']
        except AttributeError:
            base.abort(404, _('Dataset not found'))

        if package['id'] != current_pkg['id']:
            log.info('Mismatch between pkg id in activity and URL {} {}'
                     .format(package['id'], current_pkg['id']))
            # the activity is not for the package in the URL - don't allow
            # misleading URLs as could be malicious
            base.abort(404, _('Activity not found'))
        # The name is used lots in the template for links, so fix it to be
        # the current one. It's not displayed to the user anyway.
        package['name'] = current_pkg['name']

        # Don't crash on old (unmigrated) activity records, which do not
        # include resources or extras.
        package.setdefault('resources', [])

    resource = None
    for res in package.get('resources', []):
        if res['id'] == resource_id:
            resource = res
            break
    if not resource:
        return base.abort(404, _('Resource not found'))

    # get package license info
    license_id = package.get('license_id')
    try:
        package['isopen'] = model.Package.get_license_register()[license_id
                                                                  ].isopen()
    except KeyError:
        package['isopen'] = False

    resource_views = get_action('resource_view_list')(
        context, {
            'id': resource_id
        }
    )
    resource['has_views'] = len(resource_views) > 0

    current_resource_view = None
    view_id = request.args.get('view_id')
    if resource['has_views']:
        if view_id:
            current_resource_view = [
                rv for rv in resource_views if rv['id'] == view_id
            ]
            if len(current_resource_view) == 1:
                current_resource_view = current_resource_view[0]
            else:
                return base.abort(404, _('Resource view not found'))
        else:
            current_resource_view = resource_views[0]

    # required for nav menu
    pkg = context['package']
    dataset_type = pkg.type or package_type

    # TODO: remove
    g.package = package
    g.resource = resource
    g.pkg = pkg
    g.pkg_dict = package

    extra_vars = {
        'resource_views': resource_views,
        'current_resource_view': current_resource_view,
        'dataset_type': dataset_type,
        'pkg_dict': package,
        'package': package,
        'resource': resource,
        'pkg': pkg,  # NB it is the current version of the dataset, so ignores
                      # activity_id. Still used though in resource views for
                      # backward compatibility
        'is_activity_archive': bool(activity_id),
    }

    template = _get_pkg_template('resource_template', dataset_type)
    return base.render(template, extra_vars)


def download(package_type, id, resource_id, filename=None):
    """
    Provides a direct download by either redirecting the user to the url
    stored or downloading an uploaded file directly.
    """
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'auth_user_obj': g.userobj
    }

    try:
        rsc = get_action('resource_show')(context, {'id': resource_id})
        get_action('package_show')(context, {'id': id})
    except (NotFound, NotAuthorized):
        return base.abort(404, _('Resource not found'))

    if rsc.get('url_type') == 'upload':
        upload = uploader.get_resource_uploader(rsc)
        filepath = upload.get_path(rsc['id'])
        resp = flask.send_file(filepath)
        if rsc.get('mimetype'):
            resp.headers['Content-Type'] = rsc['mimetype']
        plugins.toolkit.signals.resource_download.send(resource_id)
        return resp

    elif 'url' not in rsc:
        return base.abort(404, _('No download is available'))
    return h.redirect_to(rsc['url'])


class CreateView(MethodView):
    def post(self, package_type, id):
        save_action = request.form.get('save')
        data = clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
        )
        data.update(clean_dict(
            dict_fns.unflatten(tuplize_dict(parse_params(request.files)))
        ))

        # we don't want to include save as it is part of the form
        del data['save']
        resource_id = data.pop('id')

        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'auth_user_obj': g.userobj
        }

        # see if we have any data that we are trying to save
        data_provided = False
        for key, value in six.iteritems(data):
            if (
                    (value or isinstance(value, cgi.FieldStorage))
                    and key != 'resource_type'):
                data_provided = True
                break

        if not data_provided and save_action != "go-dataset-complete":
            if save_action == 'go-dataset':
                # go to final stage of adddataset
                return h.redirect_to('{}.edit'.format(package_type), id=id)
            # see if we have added any resources
            try:
                data_dict = get_action('package_show')(context, {'id': id})
            except NotAuthorized:
                return base.abort(403, _('Unauthorized to update dataset'))
            except NotFound:
                return base.abort(
                    404,
                    _('The dataset {id} could not be found.').format(id=id)
                )
            if not len(data_dict['resources']):
                # no data so keep on page
                msg = _('You must add at least one data resource')
                # On new templates do not use flash message

                errors = {}
                error_summary = {_('Error'): msg}
                return self.get(package_type, id, data, errors, error_summary)

            # XXX race condition if another user edits/deletes
            data_dict = get_action('package_show')(context, {'id': id})
            get_action('package_update')(
                dict(context, allow_state_change=True),
                dict(data_dict, state='active')
            )
            return h.redirect_to('{}.read'.format(package_type), id=id)

        data['package_id'] = id
        try:
            if resource_id:
                data['id'] = resource_id
                get_action('resource_update')(context, data)
            else:
                get_action('resource_create')(context, data)
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            if data.get('url_type') == 'upload' and data.get('url'):
                data['url'] = ''
                data['url_type'] = ''
                data['previous_upload'] = True
            return self.get(package_type, id, data, errors, error_summary)
        except NotAuthorized:
            return base.abort(403, _('Unauthorized to create a resource'))
        except NotFound:
            return base.abort(
                404, _('The dataset {id} could not be found.').format(id=id)
            )
        if save_action == 'go-metadata':
            # XXX race condition if another user edits/deletes
            data_dict = get_action('package_show')(context, {'id': id})
            get_action('package_update')(
                dict(context, allow_state_change=True),
                dict(data_dict, state='active')
            )
            return h.redirect_to('{}.read'.format(package_type), id=id)
        elif save_action == 'go-dataset':
            # go to first stage of add dataset
            return h.redirect_to('{}.edit'.format(package_type), id=id)
        elif save_action == 'go-dataset-complete':

            return h.redirect_to('{}.read'.format(package_type), id=id)
        else:
            # add more resources
            return h.redirect_to(
                '{}_resource.new'.format(package_type),
                id=id
            )

    def get(
        self, package_type, id, data=None, errors=None, error_summary=None
    ):
        # get resources for sidebar
        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'auth_user_obj': g.userobj
        }
        try:
            pkg_dict = get_action('package_show')(context, {'id': id})
        except NotFound:
            return base.abort(
                404, _('The dataset {id} could not be found.').format(id=id)
            )
        try:
            check_access(
                'resource_create', context, {"package_id": pkg_dict["id"]}
            )
        except NotAuthorized:
            return base.abort(
                403, _('Unauthorized to create a resource for this package')
            )

        package_type = pkg_dict['type'] or package_type

        errors = errors or {}
        error_summary = error_summary or {}
        extra_vars = {
            'data': data,
            'errors': errors,
            'error_summary': error_summary,
            'action': 'new',
            'resource_form_snippet': _get_pkg_template(
                'resource_form', package_type
            ),
            'dataset_type': package_type,
            'pkg_name': id,
            'pkg_dict': pkg_dict
        }
        template = 'package/new_resource_not_draft.html'
        if pkg_dict['state'].startswith('draft'):
            extra_vars['stage'] = ['complete', 'active']
            template = 'package/new_resource.html'
        return base.render(template, extra_vars)


class EditView(MethodView):
    def _prepare(self, id):
        context = {
            'model': model,
            'session': model.Session,
            'api_version': 3,
            'for_edit': True,
            'user': g.user,
            'auth_user_obj': g.userobj
        }
        try:
            check_access('package_update', context, {'id': id})
        except NotAuthorized:
            return base.abort(
                403,
                _('User %r not authorized to edit %s') % (g.user, id)
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
        del data['save']

        data['package_id'] = id
        try:
            if resource_id:
                data['id'] = resource_id
                get_action('resource_update')(context, data)
            else:
                get_action('resource_create')(context, data)
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(
                package_type, id, resource_id, data, errors, error_summary
            )
        except NotAuthorized:
            return base.abort(403, _('Unauthorized to edit this resource'))
        return h.redirect_to(
            '{}_resource.read'.format(package_type),
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
        pkg_dict = get_action('package_show')(context, {'id': id})

        try:
            resource_dict = get_action('resource_show')(
                context, {
                    'id': resource_id
                }
            )
        except NotFound:
            return base.abort(404, _('Resource not found'))

        if pkg_dict['state'].startswith('draft'):
            return CreateView().get(package_type, id, data=resource_dict)

        # resource is fully created
        resource = resource_dict
        # set the form action
        form_action = h.url_for(
            '{}_resource.edit'.format(package_type),
            resource_id=resource_id, id=id
        )
        if not data:
            data = resource_dict

        package_type = pkg_dict['type'] or package_type

        errors = errors or {}
        error_summary = error_summary or {}
        extra_vars = {
            'data': data,
            'errors': errors,
            'error_summary': error_summary,
            'action': 'edit',
            'resource_form_snippet': _get_pkg_template(
                'resource_form', package_type
            ),
            'dataset_type': package_type,
            'resource': resource,
            'pkg_dict': pkg_dict,
            'form_action': form_action
        }
        return base.render('package/resource_edit.html', extra_vars)


class DeleteView(MethodView):
    def _prepare(self, id):
        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'auth_user_obj': g.userobj
        }
        try:
            check_access('package_delete', context, {'id': id})
        except NotAuthorized:
            return base.abort(
                403,
                _('Unauthorized to delete package %s') % ''
            )
        return context

    def post(self, package_type, id, resource_id):
        if 'cancel' in request.form:
            return h.redirect_to(
                '{}_resource.edit'.format(package_type),
                resource_id=resource_id, id=id
            )
        context = self._prepare(id)

        try:
            get_action('resource_delete')(context, {'id': resource_id})
            h.flash_notice(_('Resource has been deleted.'))
            pkg_dict = get_action('package_show')(None, {'id': id})
            if pkg_dict['state'].startswith('draft'):
                return h.redirect_to(
                    '{}_resource.new'.format(package_type),
                    id=id
                )
            else:
                return h.redirect_to('{}.read'.format(package_type), id=id)
        except NotAuthorized:
            return base.abort(
                403,
                _('Unauthorized to delete resource %s') % ''
            )
        except NotFound:
            return base.abort(404, _('Resource not found'))

    def get(self, package_type, id, resource_id):
        context = self._prepare(id)
        try:
            resource_dict = get_action('resource_show')(
                context, {
                    'id': resource_id
                }
            )
            pkg_id = id
        except NotAuthorized:
            return base.abort(
                403,
                _('Unauthorized to delete resource %s') % ''
            )
        except NotFound:
            return base.abort(404, _('Resource not found'))

        # TODO: remove
        g.resource_dict = resource_dict
        g.pkg_id = pkg_id

        return base.render(
            'package/confirm_delete_resource.html', {
                'dataset_type': _get_package_type(id),
                'resource_dict': resource_dict,
                'pkg_id': pkg_id
            }
        )


def views(package_type, id, resource_id):
    package_type = _get_package_type(id)
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'for_view': True,
        'auth_user_obj': g.userobj
    }
    data_dict = {'id': id}

    try:
        check_access('package_update', context, data_dict)
    except NotAuthorized:
        return base.abort(
            403,
            _('User %r not authorized to edit %s') % (g.user, id)
        )
    # check if package exists
    try:
        pkg_dict = get_action('package_show')(context, data_dict)
        pkg = context['package']
    except (NotFound, NotAuthorized):
        return base.abort(404, _('Dataset not found'))

    try:
        resource = get_action('resource_show')(context, {'id': resource_id})
        views = get_action('resource_view_list')(
            context, {
                'id': resource_id
            }
        )

    except NotFound:
        return base.abort(404, _('Resource not found'))
    except NotAuthorized:
        return base.abort(403, _('Unauthorized to read resource %s') % id)

    _setup_template_variables(context, {'id': id}, package_type=package_type)

    # TODO: remove
    g.pkg_dict = pkg_dict
    g.pkg = pkg
    g.resource = resource
    g.views = views

    return base.render(
        'package/resource_views.html', {
            'pkg_dict': pkg_dict,
            'pkg': pkg,
            'resource': resource,
            'views': views
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
        'model': model,
        'session': model.Session,
        'user': g.user,
        'auth_user_obj': g.userobj
    }

    try:
        package = get_action('package_show')(context, {'id': id})
    except (NotFound, NotAuthorized):
        return base.abort(404, _('Dataset not found'))

    try:
        resource = get_action('resource_show')(context, {'id': resource_id})
    except (NotFound, NotAuthorized):
        return base.abort(404, _('Resource not found'))

    view = None
    if request.params.get('resource_view', ''):
        try:
            view = json.loads(request.params.get('resource_view', ''))
        except ValueError:
            return base.abort(409, _('Bad resource view data'))
    elif view_id:
        try:
            view = get_action('resource_view_show')(context, {'id': view_id})
        except (NotFound, NotAuthorized):
            return base.abort(404, _('Resource view not found'))

    if not view or not isinstance(view, dict):
        return base.abort(404, _('Resource view not supplied'))

    return h.rendered_resource_view(view, resource, package, embed=True)


# FIXME: could anyone think about better name?
class EditResourceViewView(MethodView):
    def _prepare(self, id, resource_id):
        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'for_view': True,
            'auth_user_obj': g.userobj
        }

        # update resource should tell us early if the user has privilages.
        try:
            check_access('resource_update', context, {'id': resource_id})
        except NotAuthorized:
            return base.abort(
                403,
                _('User %r not authorized to edit %s') % (g.user, id)
            )

        # get resource and package data
        try:
            pkg_dict = get_action('package_show')(context, {'id': id})
            pkg = context['package']
        except (NotFound, NotAuthorized):
            return base.abort(404, _('Dataset not found'))
        try:
            resource = get_action('resource_show')(
                context, {
                    'id': resource_id
                }
            )
        except (NotFound, NotAuthorized):
            return base.abort(404, _('Resource not found'))

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
        data.pop('save', None)

        to_preview = data.pop('preview', False)
        if to_preview:
            context['preview'] = True
        to_delete = data.pop('delete', None)
        data['resource_id'] = resource_id
        data['view_type'] = request.args.get('view_type')

        try:
            if to_delete:
                data['id'] = view_id
                get_action('resource_view_delete')(context, data)
            elif view_id:
                data['id'] = view_id
                data = get_action('resource_view_update')(context, data)
            else:
                data = get_action('resource_view_create')(context, data)
        except ValidationError as e:
            # Could break preview if validation error
            to_preview = False
            extra_vars['errors'] = e.error_dict,
            extra_vars['error_summary'] = e.error_summary
        except NotAuthorized:
            # This should never happen unless the user maliciously changed
            # the resource_id in the url.
            return base.abort(403, _('Unauthorized to edit resource'))
        else:
            if not to_preview:
                return h.redirect_to(
                    '{}_resource.views'.format(package_type),
                    id=id, resource_id=resource_id
                )
        extra_vars['data'] = data
        extra_vars['to_preview'] = to_preview
        return self.get(package_type, id, resource_id, view_id, extra_vars)

    def get(
        self, package_type, id, resource_id, view_id=None, post_extra=None
    ):
        context, extra_vars = self._prepare(id, resource_id)
        to_preview = extra_vars['to_preview']
        if post_extra:
            extra_vars.update(post_extra)

        package_type = _get_package_type(id)
        data = extra_vars['data'] if 'data' in extra_vars else None
        if data and 'view_type' in data:
            view_type = data.get('view_type')
        else:
            view_type = request.args.get('view_type')

        # view_id exists only when updating
        if view_id:
            if not data or not view_type:
                try:
                    view_data = get_action('resource_view_show')(
                        context, {
                            'id': view_id
                        }
                    )
                    view_type = view_data['view_type']
                    if data:
                        data.update(view_data)
                    else:
                        data = view_data
                except (NotFound, NotAuthorized):
                    return base.abort(404, _('View not found'))

            # might as well preview when loading good existing view
            if not extra_vars['errors']:
                to_preview = True

        data['view_type'] = view_type
        view_plugin = lib_datapreview.get_view_plugin(view_type)
        if not view_plugin:
            return base.abort(404, _('View Type Not found'))

        _setup_template_variables(
            context, {'id': id}, package_type=package_type
        )

        data_dict = {
            'package': extra_vars['pkg_dict'],
            'resource': extra_vars['resource'],
            'resource_view': data
        }

        view_template = view_plugin.view_template(context, data_dict)
        form_template = view_plugin.form_template(context, data_dict)

        extra_vars.update({
            'form_template': form_template,
            'view_template': view_template,
            'data': data,
            'to_preview': to_preview,
            'datastore_available': plugins.plugin_loaded('datastore')
        })
        extra_vars.update(
            view_plugin.setup_template_variables(context, data_dict) or {}
        )
        extra_vars.update(data_dict)

        if view_id:
            return base.render('package/edit_view.html', extra_vars)

        return base.render('package/new_view.html', extra_vars)


def _parse_recline_state(params):
    state_version = int(request.args.get('state_version', '1'))
    if state_version != 1:
        return None

    recline_state = {}
    for k, v in request.args.items():
        try:
            v = h.json.loads(v)
        except ValueError:
            pass
        recline_state[k] = v

    recline_state.pop('width', None)
    recline_state.pop('height', None)
    recline_state['readOnly'] = True

    # previous versions of recline setup used elasticsearch_url attribute
    # for data api url - see http://trac.ckan.org/ticket/2639
    # fix by relocating this to url attribute which is the default location
    if 'dataset' in recline_state and 'elasticsearch_url' in recline_state[
        'dataset'
    ]:
        recline_state['dataset']['url'] = recline_state['dataset'][
            'elasticsearch_url'
        ]

    # Ensure only the currentView is available
    # default to grid view if none specified
    if not recline_state.get('currentView', None):
        recline_state['currentView'] = 'grid'
    for k in recline_state.keys():
        if k.startswith('view-') and \
                not k.endswith(recline_state['currentView']):
            recline_state.pop(k)
    return recline_state


def embedded_dataviewer(package_type, id, resource_id, width=500, height=500):
    """
    Embedded page for a read-only resource dataview. Allows
    for width and height to be specified as part of the
    querystring (as well as accepting them via routes).
    """
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'auth_user_obj': g.userobj
    }

    try:
        resource = get_action('resource_show')(context, {'id': resource_id})
        package = get_action('package_show')(context, {'id': id})
        resource_json = h.json.dumps(resource)

        # double check that the resource belongs to the specified package
        if not resource['id'] in [r['id'] for r in package['resources']]:
            raise NotFound
        dataset_type = package['type'] or package_type

    except (NotFound, NotAuthorized):
        return base.abort(404, _('Resource not found'))

    # Construct the recline state
    state_version = int(request.args.get('state_version', '1'))
    recline_state = _parse_recline_state(request.args)
    if recline_state is None:
        return base.abort(
            400, (
                '"state" parameter must be a valid recline '
                'state (version %d)' % state_version
            )
        )

    recline_state = h.json.dumps(recline_state)

    width = max(int(request.args.get('width', width)), 100)
    height = max(int(request.args.get('height', height)), 100)
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
        'package/resource_embedded_dataviewer.html', {
            'dataset_type': dataset_type,
            'resource': resource,
            'package': package,
            'resource_json': resource_json,
            'width': width,
            'height': height,
            'embedded': embedded,
            'recline_state': recline_state
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
        'model': model,
        'session': model.Session,
        'user': g.user,
        'auth_user_obj': g.userobj
    }

    try:
        resource = get_action('resource_show')(context, {'id': resource_id})
        package = get_action('package_show')(context, {'id': id})

        data_dict = {'resource': resource, 'package': package}

        preview_plugin = lib_datapreview.get_preview_plugin(data_dict)

        if preview_plugin is None:
            return base.abort(409, _('No preview has been defined.'))

        preview_plugin.setup_template_variables(context, data_dict)
        resource_json = json.dumps(resource)
        dataset_type = package['type'] or package_type

        # TODO: remove
        g.resource = resource
        g.package = package
        g.resource_json = resource_json

    except (NotFound, NotAuthorized):
        return base.abort(404, _('Resource not found'))
    else:
        return base.render(
            preview_plugin.preview_template(context, data_dict), {
                'dataset_type': dataset_type,
                'resource': resource,
                'package': package,
                'resource_json': resource_json
            }
        )


def register_dataset_plugin_rules(blueprint):
    blueprint.add_url_rule('/new', view_func=CreateView.as_view(str('new')))
    blueprint.add_url_rule(
        '/<resource_id>', view_func=read, strict_slashes=False)
    blueprint.add_url_rule(
        '/<resource_id>/edit', view_func=EditView.as_view(str('edit'))
    )
    blueprint.add_url_rule(
        '/<resource_id>/delete', view_func=DeleteView.as_view(str('delete'))
    )

    blueprint.add_url_rule('/<resource_id>/download', view_func=download)
    blueprint.add_url_rule('/<resource_id>/views', view_func=views)
    blueprint.add_url_rule('/<resource_id>/view', view_func=view)
    blueprint.add_url_rule('/<resource_id>/view/<view_id>', view_func=view)
    blueprint.add_url_rule(
        '/<resource_id>/download/<filename>', view_func=download
    )

    _edit_view = EditResourceViewView.as_view(str('edit_view'))
    blueprint.add_url_rule('/<resource_id>/new_view', view_func=_edit_view)
    blueprint.add_url_rule(
        '/<resource_id>/edit_view/<view_id>', view_func=_edit_view
    )
    blueprint.add_url_rule(
        '/<resource_id>/embed', view_func=embedded_dataviewer)
    blueprint.add_url_rule(
        '/<resource_id>/viewer',
        view_func=embedded_dataviewer,
        defaults={
            'width': "960",
            'height': "800"
        }
    )
    blueprint.add_url_rule('/<resource_id>/preview', view_func=datapreview)


register_dataset_plugin_rules(resource)
register_dataset_plugin_rules(prefixed_resource)
