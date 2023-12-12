# encoding: utf-8
from __future__ import annotations

import logging
import inspect
from collections import OrderedDict
from functools import partial
from typing_extensions import TypeAlias
from urllib.parse import urlencode
from typing import Any, Iterable, Optional, Union, cast

from flask import Blueprint
from flask.views import MethodView
from jinja2.exceptions import TemplateNotFound
from werkzeug.datastructures import MultiDict
from ckan.common import asbool, current_user

import ckan.lib.base as base
from ckan.lib.helpers import helper_functions as h
from ckan.lib.helpers import Page
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as plugins
import ckan.authz as authz
from ckan.common import _, config, g, request
from ckan.views.home import CACHE_PARAMETERS
from ckan.lib.plugins import lookup_package_plugin
from ckan.lib.search import SearchError, SearchQueryError, SearchIndexError
from ckan.types import Context, Response


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

dataset = Blueprint(
    u'dataset',
    __name__,
    url_prefix=u'/dataset',
    url_defaults={u'package_type': u'dataset'}
)


def _setup_template_variables(context: Context,
                              data_dict: dict[str, Any],
                              package_type: Optional[str] = None) -> None:
    return lookup_package_plugin(package_type).setup_template_variables(
        context, data_dict
    )


def _get_pkg_template(template_type: str,
                      package_type: Optional[str] = None) -> str:
    pkg_plugin = lookup_package_plugin(package_type)
    method = getattr(pkg_plugin, template_type)
    signature = inspect.signature(method)
    if len(signature.parameters):
        return method(package_type)
    else:
        return method()


def _encode_params(params: Iterable[tuple[str, Any]]):
    return [(k, v.encode(u'utf-8') if isinstance(v, str) else str(v))
            for k, v in params]


Params: TypeAlias = "list[tuple[str, Any]]"


def url_with_params(url: str, params: Params) -> str:
    params = _encode_params(params)
    return url + u'?' + urlencode(params)


def search_url(params: Params, package_type: Optional[str] = None) -> str:
    if not package_type:
        package_type = u'dataset'
    url = h.url_for(u'{0}.search'.format(package_type))
    return url_with_params(url, params)


def remove_field(package_type: Optional[str],
                 key: str,
                 value: Optional[str] = None,
                 replace: Optional[str] = None):
    if not package_type:
        package_type = u'dataset'
    url = h.url_for(u'{0}.search'.format(package_type))
    return h.remove_url_param(
        key,
        value=value,
        replace=replace,
        alternative_url=url
    )


def _sort_by(params_nosort: Params, package_type: str,
             fields: Iterable[tuple[str, str]]) -> str:
    """Sort by the given list of fields.

    Each entry in the list is a 2-tuple: (fieldname, sort_order)
    eg - [(u'metadata_modified', u'desc'), (u'name', u'asc')]
    If fields is empty, then the default ordering is used.
    """
    params = params_nosort[:]

    if fields:
        sort_string = u', '.join(u'%s %s' % f for f in fields)
        params.append((u'sort', sort_string))
    return search_url(params, package_type)


def _pager_url(params_nopage: Params,
               package_type: str,
               q: Any = None,  # noqa
               page: Optional[int] = None) -> str:
    params = list(params_nopage)
    params.append((u'page', page))
    return search_url(params, package_type)


def _tag_string_to_list(tag_string: str) -> list[dict[str, str]]:
    """This is used to change tags from a sting to a list of dicts.
    """
    out: list[dict[str, str]] = []
    for tag in tag_string.split(u','):
        tag = tag.strip()
        if tag:
            out.append({u'name': tag, u'state': u'active'})
    return out


def _form_save_redirect(pkg_name: str,
                        action: str,
                        package_type: Optional[str] = None) -> Response:
    """This redirects the user to the CKAN package/read page,
    unless there is request parameter giving an alternate location,
    perhaps an external website.
    @param pkg_name - Name of the package just edited
    @param action - What the action of the edit was
    """
    assert action in (u'new', u'edit')
    url = request.args.get(u'return_to') or config.get(
        u'package_%s_return_url' % action
    )
    if url:
        url = url.replace(u'<NAME>', pkg_name)
    else:
        if not package_type:
            package_type = u'dataset'
        url = h.url_for(u'{0}.read'.format(package_type), id=pkg_name)
    return h.redirect_to(url)


def _get_package_type(id: str) -> str:
    """
    Given the id of a package this method will return the type of the
    package, or 'dataset' if no type is currently set
    """
    pkg = model.Package.get(id)
    if pkg:
        return pkg.type or u'dataset'
    return u'dataset'


def _get_search_details() -> dict[str, Any]:
    fq = u''

    # fields_grouped will contain a dict of params containing
    # a list of values eg {u'tags':[u'tag1', u'tag2']}

    fields = []
    fields_grouped = {}
    search_extras: 'MultiDict[str, Any]' = MultiDict()

    for (param, value) in request.args.items(multi=True):
        if param not in [u'q', u'page', u'sort'] \
                and len(value) and not param.startswith(u'_'):
            if not param.startswith(u'ext_'):
                fields.append((param, value))
                fq += u' %s:"%s"' % (param, value)
                if param not in fields_grouped:
                    fields_grouped[param] = [value]
                else:
                    fields_grouped[param].append(value)
            else:
                search_extras.update({param: value})

    extras = dict([
        (k, v[0]) if len(v) == 1 else (k, v)
        for k, v in search_extras.lists()
    ])
    return {
        u'fields': fields,
        u'fields_grouped': fields_grouped,
        u'fq': fq,
        u'search_extras': extras,
    }


def search(package_type: str) -> str:
    extra_vars: dict[str, Any] = {}

    try:
        context = cast(Context, {
            u'model': model,
            u'user': current_user.name,
            u'auth_user_obj': current_user
        })
        check_access(u'site_read', context)
    except NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    # unicode format (decoded from utf8)
    extra_vars[u'q'] = q = request.args.get(u'q', u'')

    extra_vars['query_error'] = False
    page = h.get_page_number(request.args)

    limit = config.get(u'ckan.datasets_per_page')

    # most search operations should reset the page counter:
    params_nopage = [(k, v) for k, v in request.args.items(multi=True)
                     if k != u'page']

    extra_vars[u'remove_field'] = partial(remove_field, package_type)

    sort_by = request.args.get(u'sort', None)
    params_nosort = [(k, v) for k, v in params_nopage if k != u'sort']

    extra_vars[u'sort_by'] = partial(_sort_by, params_nosort, package_type)

    if not sort_by:
        sort_by_fields = []
    else:
        sort_by_fields = [field.split()[0] for field in sort_by.split(u',')]
    extra_vars[u'sort_by_fields'] = sort_by_fields

    pager_url = partial(_pager_url, params_nopage, package_type)

    details = _get_search_details()
    extra_vars[u'fields'] = details[u'fields']
    extra_vars[u'fields_grouped'] = details[u'fields_grouped']
    fq = details[u'fq']
    search_extras = details[u'search_extras']

    context = cast(Context, {
        u'model': model,
        u'session': model.Session,
        u'user': current_user.name,
        u'for_view': True,
        u'auth_user_obj': current_user
    })

    # Unless changed via config options, don't show other dataset
    # types any search page. Potential alternatives are do show them
    # on the default search page (dataset) or on one other search page
    search_all_type = config.get(u'ckan.search.show_all_types')
    search_all = False

    try:
        # If the "type" is set to True or False, convert to bool
        # and we know that no type was specified, so use traditional
        # behaviour of applying this only to dataset type
        search_all = asbool(search_all_type)
        search_all_type = u'dataset'
    # Otherwise we treat as a string representing a type
    except ValueError:
        search_all = True

    if not search_all or package_type != search_all_type:
        # Only show datasets of this particular type
        fq += u' +dataset_type:{type}'.format(type=package_type)

    facets: dict[str, str] = OrderedDict()

    org_label = h.humanize_entity_type(
        u'organization',
        h.default_group_type(u'organization'),
        u'facet label') or _(u'Organizations')

    group_label = h.humanize_entity_type(
        u'group',
        h.default_group_type(u'group'),
        u'facet label') or _(u'Groups')

    default_facet_titles = {
        u'organization': org_label,
        u'groups': group_label,
        u'tags': _(u'Tags'),
        u'res_format': _(u'Formats'),
        u'license_id': _(u'Licenses'),
    }

    for facet in h.facets():
        if facet in default_facet_titles:
            facets[facet] = default_facet_titles[facet]
        else:
            facets[facet] = facet

    # Facet titles
    for plugin in plugins.PluginImplementations(plugins.IFacets):
        facets = plugin.dataset_facets(facets, package_type)

    extra_vars[u'facet_titles'] = facets
    data_dict: dict[str, Any] = {
        u'q': q,
        u'fq': fq.strip(),
        u'facet.field': list(facets.keys()),
        u'rows': limit,
        u'start': (page - 1) * limit,
        u'sort': sort_by,
        u'extras': search_extras,
        u'include_private': config.get(
            u'ckan.search.default_include_private'),
    }
    try:
        query = get_action(u'package_search')(context, data_dict)

        extra_vars[u'sort_by_selected'] = query[u'sort']

        extra_vars[u'page'] = Page(
            collection=query[u'results'],
            page=page,
            url=pager_url,
            item_count=query[u'count'],
            items_per_page=limit
        )
        extra_vars[u'search_facets'] = query[u'search_facets']
        extra_vars[u'page'].items = query[u'results']
    except SearchQueryError as se:
        # User's search parameters are invalid, in such a way that is not
        # achievable with the web interface, so return a proper error to
        # discourage spiders which are the main cause of this.
        log.info(u'Dataset search query rejected: %r', se.args)
        base.abort(
            400,
            _(u'Invalid search query: {error_message}')
            .format(error_message=str(se))
        )
    except SearchError as se:
        # May be bad input from the user, but may also be more serious like
        # bad code causing a SOLR syntax error, or a problem connecting to
        # SOLR
        log.error(u'Dataset search error: %r', se.args)
        extra_vars[u'query_error'] = True
        extra_vars[u'search_facets'] = {}
        extra_vars[u'page'] = Page(collection=[])

    # FIXME: try to avoid using global variables
    g.search_facets_limits = {}
    default_limit: int = config.get(u'search.facets.default')
    for facet in cast(Iterable[str], extra_vars[u'search_facets'].keys()):
        try:
            limit = int(
                request.args.get(
                    u'_%s_limit' % facet,
                    default_limit
                )
            )
        except ValueError:
            base.abort(
                400,
                _(u'Parameter u"{parameter_name}" is not '
                  u'an integer').format(parameter_name=u'_%s_limit' % facet)
            )

        g.search_facets_limits[facet] = limit

    _setup_template_variables(context, {}, package_type=package_type)

    extra_vars[u'dataset_type'] = package_type

    # TODO: remove
    for key, value in extra_vars.items():
        setattr(g, key, value)

    return base.render(
        _get_pkg_template(u'search_template', package_type), extra_vars
    )


def resources(package_type: str, id: str) -> Union[Response, str]:
    context = cast(Context, {
        u'model': model,
        u'session': model.Session,
        u'user': current_user.name,
        u'for_view': True,
        u'auth_user_obj': current_user
    })
    data_dict: dict[str, Any] = {u'id': id, u'include_tracking': True}

    try:
        check_access(u'package_update', context, data_dict)
    except NotFound:
        return base.abort(404, _(u'Dataset not found'))
    except NotAuthorized:
        return base.abort(
            403,
            _(u'User %r not authorized to edit %s') % (current_user.name, id)
        )
    # check if package exists
    try:
        pkg_dict = get_action(u'package_show')(context, data_dict)
        pkg = context[u'package']
    except (NotFound, NotAuthorized):
        return base.abort(404, _(u'Dataset not found'))

    package_type = pkg_dict[u'type'] or u'dataset'
    _setup_template_variables(context, {u'id': id}, package_type=package_type)

    # TODO: remove
    g.pkg_dict = pkg_dict
    g.pkg = pkg

    return base.render(
        u'package/resources.html', {
            u'dataset_type': package_type,
            u'pkg_dict': pkg_dict,
            u'pkg': pkg
        }
    )


def read(package_type: str, id: str) -> Union[Response, str]:
    context = cast(Context, {
        u'model': model,
        u'session': model.Session,
        u'user': current_user.name,
        u'for_view': True,
        u'auth_user_obj': current_user
    })
    data_dict = {u'id': id, u'include_tracking': True}

    # check if package exists
    try:
        pkg_dict = get_action(u'package_show')(context, data_dict)
        pkg = context[u'package']
    except NotFound:
        return base.abort(
            404,
            _(u'Dataset not found or you have no permission to view it')
        )
    except NotAuthorized:
        if config.get(u'ckan.auth.reveal_private_datasets'):
            if current_user.is_authenticated:
                return base.abort(
                    403, _(u'Unauthorized to read package %s') % id)
            else:
                return h.redirect_to(
                    "user.login",
                    came_from=h.url_for('{}.read'.format(package_type), id=id)
                )
        return base.abort(
            404,
            _(u'Dataset not found or you have no permission to view it')
        )

    g.pkg_dict = pkg_dict
    g.pkg = pkg

    if plugins.plugin_loaded("activity"):
        activity_id = request.args.get("activity_id")
        if activity_id:
            return h.redirect_to(
                "activity.package_history",
                id=id, activity_id=activity_id
            )

    # if the user specified a package id, redirect to the package name
    if data_dict['id'] == pkg_dict['id'] and \
            data_dict['id'] != pkg_dict['name']:
        return h.redirect_to(u'{}.read'.format(package_type),
                             id=pkg_dict['name'])

    # can the resources be previewed?
    for resource in pkg_dict[u'resources']:
        resource_views = get_action(u'resource_view_list')(
            context, {
                u'id': resource[u'id']
            }
        )
        resource[u'has_views'] = len(resource_views) > 0

    package_type = pkg_dict[u'type'] or package_type
    _setup_template_variables(context, {u'id': id}, package_type=package_type)

    template = _get_pkg_template(u'read_template', package_type)
    try:
        return base.render(
            template, {
                u'dataset_type': package_type,
                u'pkg_dict': pkg_dict,
                u'pkg': pkg,
            }
        )
    except TemplateNotFound as e:
        msg = _(
            u"Viewing datasets of type \"{package_type}\" is "
            u"not supported ({file_!r}).".format(
                package_type=package_type, file_=e.message
            )
        )
        return base.abort(404, msg)


class CreateView(MethodView):
    def _is_save(self) -> bool:
        return u'save' in request.form

    def _prepare(self) -> Context:  # noqa

        context = cast(Context, {
            u'model': model,
            u'session': model.Session,
            u'user': current_user.name,
            u'auth_user_obj': current_user,
            u'save': self._is_save()
        })
        try:
            check_access(u'package_create', context)
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized to create a package'))
        return context

    def post(self, package_type: str) -> Union[Response, str]:
        # The staged add dataset used the new functionality when the dataset is
        # partially created so we need to know if we actually are updating or
        # this is a real new.
        context = self._prepare()
        is_an_update = False
        ckan_phase = request.form.get(u'_ckan_phase')
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
            )
        except dict_fns.DataError:
            return base.abort(400, _(u'Integrity Error'))
        try:
            if ckan_phase:
                # prevent clearing of groups etc
                context[u'allow_partial_update'] = True
                # sort the tags
                if u'tag_string' in data_dict:
                    data_dict[u'tags'] = _tag_string_to_list(
                        data_dict[u'tag_string']
                    )
                if data_dict.get(u'pkg_name'):
                    is_an_update = True
                    # This is actually an update not a save
                    data_dict[u'id'] = data_dict[u'pkg_name']
                    del data_dict[u'pkg_name']
                    # don't change the dataset state
                    data_dict[u'state'] = u'draft'
                    # this is actually an edit not a save
                    pkg_dict = get_action(u'package_update')(
                        context, data_dict
                    )

                    # redirect to add dataset resources
                    url = h.url_for(
                        u'{}_resource.new'.format(package_type),
                        id=pkg_dict[u'name']
                    )
                    return h.redirect_to(url)
                # Make sure we don't index this dataset
                if request.form[u'save'] not in [
                    u'go-resource', u'go-metadata'
                ]:
                    data_dict[u'state'] = u'draft'
                # allow the state to be changed
                context[u'allow_state_change'] = True

            data_dict[u'type'] = package_type
            pkg_dict = get_action(u'package_create')(context, data_dict)

            create_on_ui_requires_resources = config.get(
                'ckan.dataset.create_on_ui_requires_resources'
            )
            if ckan_phase:
                if create_on_ui_requires_resources:
                    # redirect to add dataset resources if
                    # create_on_ui_requires_resources is set to true
                    url = h.url_for(
                        u'{}_resource.new'.format(package_type),
                        id=pkg_dict[u'name']
                    )
                    return h.redirect_to(url)

                get_action(u'package_update')(
                    cast(Context, dict(context, allow_state_change=True)),
                    dict(pkg_dict, state=u'active')
                )
                return h.redirect_to(
                    u'{}.read'.format(package_type),
                    id=pkg_dict["id"]
                )

            return _form_save_redirect(
                pkg_dict[u'name'], u'new', package_type=package_type
            )
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized to read package'))
        except NotFound:
            return base.abort(404, _(u'Dataset not found'))
        except SearchIndexError as e:
            try:
                exc_str = str(repr(e.args))
            except Exception:  # We don't like bare excepts
                exc_str = str(str(e))
            return base.abort(
                500,
                _(u'Unable to add package to search index.') + exc_str
            )
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            if is_an_update:
                # we need to get the state of the dataset to show the stage we
                # are on.
                pkg_dict = get_action(u'package_show')(context, data_dict)
                data_dict[u'state'] = pkg_dict[u'state']
                return EditView().get(
                    package_type,
                    data_dict[u'id'],
                    data_dict,
                    errors,
                    error_summary
                )
            data_dict[u'state'] = u'none'
            return self.get(package_type, data_dict, errors, error_summary)

    def get(self,
            package_type: str,
            data: Optional[dict[str, Any]] = None,
            errors: Optional[dict[str, Any]] = None,
            error_summary: Optional[dict[str, Any]] = None) -> str:
        context = self._prepare()
        if data and u'type' in data:
            package_type = data[u'type']

        data = data or clean_dict(
            dict_fns.unflatten(
                tuplize_dict(
                    parse_params(request.args, ignore_keys=CACHE_PARAMETERS)
                )
            )
        )
        resources_json = h.dump_json(data.get(u'resources', []))
        # convert tags if not supplied in data
        if data and not data.get(u'tag_string'):
            data[u'tag_string'] = u', '.join(
                h.dict_list_reduce(data.get(u'tags', {}), u'name')
            )

        errors = errors or {}
        error_summary = error_summary or {}
        # in the phased add dataset we need to know that
        # we have already completed stage 1
        stage = [u'active']
        if data.get(u'state', u'').startswith(u'draft'):
            stage = [u'active', u'complete']

        # if we are creating from a group then this allows the group to be
        # set automatically
        data[
            u'group_id'
        ] = request.args.get(u'group') or request.args.get(u'groups__0__id')

        form_snippet = _get_pkg_template(
            u'package_form', package_type=package_type
        )
        form_vars: dict[str, Any] = {
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary,
            u'action': u'new',
            u'stage': stage,
            u'dataset_type': package_type,
            u'form_style': u'new'
        }
        errors_json = h.dump_json(errors)

        # TODO: remove
        g.resources_json = resources_json
        g.errors_json = errors_json

        _setup_template_variables(context, {}, package_type=package_type)

        new_template = _get_pkg_template(u'new_template', package_type)
        return base.render(
            new_template,
            extra_vars={
                u'form_vars': form_vars,
                u'form_snippet': form_snippet,
                u'dataset_type': package_type,
                u'resources_json': resources_json,
                u'form_snippet': form_snippet,
                u'errors_json': errors_json
            }
        )


class EditView(MethodView):
    def _prepare(self) -> Context:
        context = cast(Context, {
            u'model': model,
            u'session': model.Session,
            u'user': current_user.name,
            u'auth_user_obj': current_user,
            u'save': u'save' in request.form
        })
        return context

    def post(self, package_type: str, id: str) -> Union[Response, str]:
        context = self._prepare()
        package_type = _get_package_type(id) or package_type
        log.debug(u'Package save request name: %s POST: %r', id, request.form)
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
            )
        except dict_fns.DataError:
            return base.abort(400, _(u'Integrity Error'))
        try:
            if u'_ckan_phase' in data_dict:
                # we allow partial updates to not destroy existing resources
                context[u'allow_partial_update'] = True
                if u'tag_string' in data_dict:
                    data_dict[u'tags'] = _tag_string_to_list(
                        data_dict[u'tag_string']
                    )
                del data_dict[u'_ckan_phase']
                del data_dict[u'save']
            data_dict['id'] = id
            pkg_dict = get_action(u'package_update')(context, data_dict)

            return _form_save_redirect(
                pkg_dict[u'name'], u'edit', package_type=package_type
            )
        except NotAuthorized:
            return base.abort(403, _(u'Unauthorized to read package %s') % id)
        except NotFound:
            return base.abort(404, _(u'Dataset not found'))
        except SearchIndexError as e:
            try:
                exc_str = str(repr(e.args))
            except Exception:  # We don't like bare excepts
                exc_str = str(str(e))
            return base.abort(
                500,
                _(u'Unable to update search index.') + exc_str
            )
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(package_type, id, data_dict, errors, error_summary)

    def get(self,
            package_type: str,
            id: str,
            data: Optional[dict[str, Any]] = None,
            errors: Optional[dict[str, Any]] = None,
            error_summary: Optional[dict[str, Any]] = None
            ) -> Union[Response, str]:
        context = self._prepare()
        package_type = _get_package_type(id) or package_type
        try:
            view_context = context.copy()
            view_context['for_view'] = True
            pkg_dict = get_action(u'package_show')(
                view_context, {u'id': id})
            context[u'for_edit'] = True
            old_data = get_action(u'package_show')(context, {u'id': id})
            # old data is from the database and data is passed from the
            # user if there is a validation error. Use users data if there.
            if data:
                old_data.update(data)
            data = old_data
        except (NotFound, NotAuthorized):
            return base.abort(404, _(u'Dataset not found'))
        assert data is not None
        # are we doing a multiphase add?
        if data.get(u'state', u'').startswith(u'draft'):
            g.form_action = h.url_for(u'{}.new'.format(package_type))
            g.form_style = u'new'

            return CreateView().get(
                package_type,
                data=data,
                errors=errors,
                error_summary=error_summary
            )

        pkg = context.get(u"package")
        resources_json = h.dump_json(data.get(u'resources', []))
        user = current_user.name
        try:
            check_access(u'package_update', context)
        except NotAuthorized:
            return base.abort(
                403,
                _(u'User %r not authorized to edit %s') % (user, id)
            )
        # convert tags if not supplied in data
        if data and not data.get(u'tag_string'):
            data[u'tag_string'] = u', '.join(
                h.dict_list_reduce(pkg_dict.get(u'tags', {}), u'name')
            )
        errors = errors or {}
        form_snippet = _get_pkg_template(
            u'package_form', package_type=package_type
        )
        form_vars: dict[str, Any] = {
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary,
            u'action': u'edit',
            u'dataset_type': package_type,
            u'form_style': u'edit'
        }
        errors_json = h.dump_json(errors)

        # TODO: remove
        g.pkg = pkg
        g.resources_json = resources_json
        g.errors_json = errors_json

        _setup_template_variables(
            context, {u'id': id}, package_type=package_type
        )

        # we have already completed stage 1
        form_vars[u'stage'] = [u'active']
        if data.get(u'state', u'').startswith(u'draft'):
            form_vars[u'stage'] = [u'active', u'complete']

        edit_template = _get_pkg_template(u'edit_template', package_type)
        return base.render(
            edit_template,
            extra_vars={
                u'form_vars': form_vars,
                u'form_snippet': form_snippet,
                u'dataset_type': package_type,
                u'pkg_dict': pkg_dict,
                u'pkg': pkg,
                u'resources_json': resources_json,
                u'form_snippet': form_snippet,
                u'errors_json': errors_json
            }
        )


class DeleteView(MethodView):
    def _prepare(self) -> Context:
        context = cast(Context, {
            u'model': model,
            u'session': model.Session,
            u'user': current_user.name,
            u'auth_user_obj': current_user
        })
        return context

    def post(self, package_type: str, id: str) -> Response:
        if u'cancel' in request.form:
            return h.redirect_to(u'{}.edit'.format(package_type), id=id)
        context = self._prepare()
        try:
            get_action(u'package_delete')(context, {u'id': id})
        except NotFound:
            return base.abort(404, _(u'Dataset not found'))
        except NotAuthorized:
            return base.abort(
                403,
                _(u'Unauthorized to delete package %s') % u''
            )

        h.flash_notice(_(u'Dataset has been deleted.'))
        return h.redirect_to(package_type + u'.search')

    def get(self, package_type: str, id: str) -> Union[Response, str]:
        context = self._prepare()
        try:
            pkg_dict = get_action(u'package_show')(context, {u'id': id})
        except NotFound:
            return base.abort(404, _(u'Dataset not found'))
        except NotAuthorized:
            return base.abort(
                403,
                _(u'Unauthorized to delete package %s') % u''
            )

        dataset_type = pkg_dict[u'type'] or package_type

        # TODO: remove
        g.pkg_dict = pkg_dict

        return base.render(
            u'package/confirm_delete.html', {
                u'pkg_dict': pkg_dict,
                u'dataset_type': dataset_type
            }
        )


def follow(package_type: str, id: str) -> Response:
    """Start following this dataset.
    """
    context = cast(Context, {
        u'model': model,
        u'session': model.Session,
        u'user': current_user.name,
        u'auth_user_obj': current_user
    })
    data_dict = {u'id': id}
    try:
        get_action(u'follow_dataset')(context, data_dict)
        package_dict = get_action(u'package_show')(context, data_dict)
        id = package_dict['name']
    except ValidationError as e:
        error_message = (e.message or e.error_summary or e.error_dict)
        h.flash_error(error_message)
    except NotAuthorized as e:
        h.flash_error(e.message)
    else:
        h.flash_success(
            _(u"You are now following {0}").format(package_dict[u'title'])
        )

    return h.redirect_to(u'{}.read'.format(package_type), id=id)


def unfollow(package_type: str, id: str) -> Union[Response, str]:
    """Stop following this dataset.
    """
    context = cast(Context, {
        u'model': model,
        u'session': model.Session,
        u'user': current_user.name,
        u'auth_user_obj': current_user
    })
    data_dict = {u'id': id}
    try:
        get_action(u'unfollow_dataset')(context, data_dict)
        package_dict = get_action(u'package_show')(context, data_dict)
        id = package_dict['name']
    except ValidationError as e:
        error_message = (e.message or e.error_summary or e.error_dict)
        h.flash_error(error_message)
    except NotFound as e:
        error_message = e.message or ''
        base.abort(404, _(error_message))
    except NotAuthorized as e:
        error_message = e.message or ''
        base.abort(403, _(error_message))
    else:
        h.flash_success(
            _(u"You are no longer following {0}").format(
                package_dict[u'title']
            )
        )

    return h.redirect_to(u'{}.read'.format(package_type), id=id)


def followers(package_type: str,
              id: Optional[str] = None) -> Union[Response, str]:
    context = cast(Context, {
        u'model': model,
        u'session': model.Session,
        u'user': current_user.name,
        u'for_view': True,
        u'auth_user_obj': current_user
    })

    data_dict = {u'id': id}
    try:
        pkg_dict = get_action(u'package_show')(context, data_dict)
        pkg = context[u'package']
        followers = get_action(u'dataset_follower_list')(
            context, {
                u'id': pkg_dict[u'id']
            }
        )

        dataset_type = pkg.type or package_type
    except NotFound:
        return base.abort(404, _(u'Dataset not found'))
    except NotAuthorized:
        return base.abort(403, _(u'Unauthorized to read package %s') % id)

    # TODO: remove
    g.pkg_dict = pkg_dict
    g.pkg = pkg
    g.followers = followers

    return base.render(
        u'package/followers.html', {
            u'dataset_type': dataset_type,
            u'pkg_dict': pkg_dict,
            u'pkg': pkg,
            u'followers': followers
        }
    )


class GroupView(MethodView):
    def _prepare(self, id: str) -> tuple[Context, dict[str, Any]]:
        context = cast(Context, {
            u'model': model,
            u'session': model.Session,
            u'user': current_user.name,
            u'for_view': True,
            u'auth_user_obj': current_user,
            u'use_cache': False
        })

        try:
            pkg_dict = get_action(u'package_show')(context, {u'id': id})
        except (NotFound, NotAuthorized):
            return base.abort(404, _(u'Dataset not found'))
        return context, pkg_dict

    def post(self, package_type: str, id: str) -> Response:
        context = self._prepare(id)[0]
        new_group = request.form.get(u'group_added')
        if new_group:
            data_dict = {
                u"id": new_group,
                u"object": id,
                u"object_type": u'package',
                u"capacity": u'public'
            }
            try:
                get_action(u'member_create')(context, data_dict)
            except NotFound:
                return base.abort(404, _(u'Group not found'))

        removed_group = None
        for param in request.form:
            if param.startswith(u'group_remove'):
                removed_group = param.split(u'.')[-1]
                break
        if removed_group:
            data_dict = {
                u"id": removed_group,
                u"object": id,
                u"object_type": u'package'
            }

            try:
                get_action(u'member_delete')(context, data_dict)
            except NotFound:
                return base.abort(404, _(u'Group not found'))
        return h.redirect_to(u'{}.groups'.format(package_type), id=id)

    def get(self, package_type: str, id: str) -> str:
        context, pkg_dict = self._prepare(id)
        dataset_type = pkg_dict[u'type'] or package_type
        context[u'is_member'] = True
        users_groups = get_action(u'group_list_authz')(context, {u'id': id})

        pkg_group_ids = set(
            group[u'id'] for group in pkg_dict.get(u'groups', [])
        )

        user_group_ids = set(group[u'id'] for group in users_groups)

        group_dropdown = [[group[u'id'], group[u'display_name']]
                          for group in users_groups
                          if group[u'id'] not in pkg_group_ids]

        for group in pkg_dict.get(u'groups', []):
            group[u'user_member'] = (group[u'id'] in user_group_ids)

        # TODO: remove
        g.pkg_dict = pkg_dict
        g.group_dropdown = group_dropdown

        return base.render(
            u'package/group_list.html', {
                u'dataset_type': dataset_type,
                u'pkg_dict': pkg_dict,
                u'group_dropdown': group_dropdown
            }
        )


def collaborators_read(package_type: str, id: str) -> Union[Response, str]:  # noqa
    context = cast(Context, {u'model': model, u'user': current_user.name})
    data_dict = {u'id': id}

    try:
        check_access(u'package_collaborator_list', context, data_dict)
        # needed to ckan_extend package/edit_base.html
        pkg_dict = get_action(u'package_show')(context, data_dict)
    except NotAuthorized:
        message = _(u'Unauthorized to read collaborators {}').format(id)
        return base.abort(401, message)
    except NotFound:
        return base.abort(404, _(u'Dataset not found'))

    return base.render(u'package/collaborators/collaborators.html', {
        u'pkg_dict': pkg_dict})


def collaborator_delete(package_type: str,
                        id: str, user_id: str) -> Union[Response, str]:  # noqa
    context: Context = {'user': current_user.name}

    if u'cancel' in request.form:
        return h.redirect_to(u'{}.collaborators_read'
                             .format(package_type), id=id)

    try:
        if request.method == u'POST':
            get_action(u'package_collaborator_delete')(context, {
                u'id': id,
                u'user_id': user_id
            })
        user_dict = logic.get_action(u'user_show')(context, {u'id': user_id})
    except NotAuthorized:
        message = _(u'Unauthorized to delete collaborators {}').format(id)
        return base.abort(401, _(message))
    except NotFound as e:
        return base.abort(404, _(e.message))

    if request.method == u'POST':
        h.flash_success(_(u'User removed from collaborators'))

        return h.redirect_to(u'dataset.collaborators_read', id=id)

    # TODO: Remove
    # ckan 2.9: Adding variables that were removed from c object for
    # compatibility with templates in existing extensions
    g.user_dict = user_dict
    g.user_id = user_id
    g.package_id = id

    extra_vars = {
        u"user_id": user_id,
        u"user_dict": user_dict,
        u"package_id": id,
        u"package_type": package_type
    }
    return base.render(
        u'package/collaborators/confirm_delete.html', extra_vars)


class CollaboratorEditView(MethodView):

    def post(self, package_type: str, id: str) -> Response:  # noqa
        context = cast(Context, {u'model': model, u'user': current_user.name})

        try:
            form_dict = logic.clean_dict(
                dict_fns.unflatten(
                    logic.tuplize_dict(
                        logic.parse_params(request.form))))

            user = get_action(u'user_show')(
                context, {u'id': form_dict[u'username']}
            )

            data_dict: dict[str, Any] = {
                u'id': id,
                u'user_id': user[u'id'],
                u'capacity': form_dict[u'capacity']
            }

            get_action(u'package_collaborator_create')(
                context, data_dict)

        except dict_fns.DataError:
            return base.abort(400, _(u'Integrity Error'))
        except NotAuthorized:
            message = _(u'Unauthorized to edit collaborators {}').format(id)
            return base.abort(401, _(message))
        except NotFound:
            h.flash_error(_('User not found'))
            return h.redirect_to(u'dataset.new_collaborator', id=id)
        except ValidationError as e:
            h.flash_error(e.error_summary)
            return h.redirect_to(u'dataset.new_collaborator', id=id)
        else:
            h.flash_success(_(u'User added to collaborators'))

        return h.redirect_to(u'dataset.collaborators_read', id=id)

    def get(self, package_type: str, id: str) -> Union[Response, str]:  # noqa
        context = cast(Context, {u'model': model, u'user': current_user.name})
        data_dict = {u'id': id}

        try:
            check_access(u'package_collaborator_list', context, data_dict)
            # needed to ckan_extend package/edit_base.html
            pkg_dict = get_action(u'package_show')(context, data_dict)
        except NotAuthorized:
            message = u'Unauthorized to read collaborators {}'.format(id)
            return base.abort(401, _(message))
        except NotFound:
            return base.abort(404, _(u'Resource not found'))

        user = request.args.get(u'user_id')
        user_capacity = u'member'

        if user:
            collaborators = get_action(u'package_collaborator_list')(
                context, data_dict)
            for c in collaborators:
                if c[u'user_id'] == user:
                    user_capacity = c[u'capacity']
            user = get_action(u'user_show')(context, {u'id': user})

        capacities: list[dict[str, str]] = []
        if authz.check_config_permission(u'allow_admin_collaborators'):
            capacities.append({u'name': u'admin', u'value': u'admin'})
        capacities.extend([
            {u'name': u'editor', u'value': u'editor'},
            {u'name': u'member', u'value': u'member'}
        ])

        extra_vars: dict[str, Any] = {
            u'capacities': capacities,
            u'user_capacity': user_capacity,
            u'user': user,
            u'pkg_dict': pkg_dict,
        }

        return base.render(
            u'package/collaborators/collaborator_new.html', extra_vars)


def register_dataset_plugin_rules(blueprint: Blueprint):
    blueprint.add_url_rule(u'/', view_func=search, strict_slashes=False)
    blueprint.add_url_rule(u'/new', view_func=CreateView.as_view(str(u'new')))
    blueprint.add_url_rule(u'/<id>', view_func=read)
    blueprint.add_url_rule(u'/resources/<id>', view_func=resources)
    blueprint.add_url_rule(
        u'/edit/<id>', view_func=EditView.as_view(str(u'edit'))
    )
    blueprint.add_url_rule(
        u'/delete/<id>', view_func=DeleteView.as_view(str(u'delete'))
    )
    blueprint.add_url_rule(
        u'/follow/<id>', view_func=follow, methods=(u'POST', )
    )
    blueprint.add_url_rule(
        u'/unfollow/<id>', view_func=unfollow, methods=(u'POST', )
    )
    blueprint.add_url_rule(u'/followers/<id>', view_func=followers)
    blueprint.add_url_rule(
        u'/groups/<id>', view_func=GroupView.as_view(str(u'groups'))
    )

    if authz.check_config_permission(u'allow_dataset_collaborators'):
        blueprint.add_url_rule(
            rule=u'/collaborators/<id>',
            view_func=collaborators_read,
            methods=['GET', ]
        )

        blueprint.add_url_rule(
            rule=u'/collaborators/<id>/new',
            view_func=CollaboratorEditView.as_view(str(u'new_collaborator')),
            methods=[u'GET', u'POST', ]
        )

        blueprint.add_url_rule(
            rule=u'/collaborators/<id>/delete/<user_id>',
            view_func=collaborator_delete, methods=['POST', 'GET']
        )


register_dataset_plugin_rules(dataset)
# remove this when we improve blueprint registration to be explicit:
dataset.auto_register = False  # type: ignore
