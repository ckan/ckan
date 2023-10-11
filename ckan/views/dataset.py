# encoding: utf-8
from __future__ import annotations

import logging
import inspect
from collections import OrderedDict
from functools import partial
from typing_extensions import TypeAlias
from urllib.parse import urlencode
from typing import Any, Iterable, Optional, Union

from flask import Blueprint
from flask.views import MethodView
from jinja2.exceptions import TemplateNotFound
from werkzeug.datastructures import MultiDict
from ckan.common import asbool, current_user

import ckan.lib.base as base
import ckan.lib.helpers as h
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
    "dataset",
    __name__,
    url_prefix="/dataset",
    url_defaults={"package_type": "dataset"},
)


def _setup_template_variables(
    context: Context,
    data_dict: dict[str, Any],
    package_type: Optional[str] = None,
) -> None:
    return lookup_package_plugin(package_type).setup_template_variables(
        context, data_dict
    )


def _get_pkg_template(
    template_type: str, package_type: Optional[str] = None
) -> str:
    pkg_plugin = lookup_package_plugin(package_type)
    method = getattr(pkg_plugin, template_type)
    signature = inspect.signature(method)
    if len(signature.parameters):
        return method(package_type)
    else:
        return method()


def _encode_params(params: Iterable[tuple[str, Any]]):
    return [
        (k, v.encode("utf-8") if isinstance(v, str) else str(v))
        for k, v in params
    ]


Params: TypeAlias = "list[tuple[str, Any]]"


def url_with_params(url: str, params: Params) -> str:
    params = _encode_params(params)
    return url + "?" + urlencode(params)


def search_url(params: Params, package_type: Optional[str] = None) -> str:
    if not package_type:
        package_type = "dataset"
    url = h.url_for("{0}.search".format(package_type))
    return url_with_params(url, params)


def remove_field(
    package_type: Optional[str],
    key: str,
    value: Optional[str] = None,
    replace: Optional[str] = None,
):
    if not package_type:
        package_type = "dataset"
    url = h.url_for("{0}.search".format(package_type))
    return h.remove_url_param(
        key, value=value, replace=replace, alternative_url=url
    )


def _sort_by(
    params_nosort: Params, package_type: str, fields: Iterable[tuple[str, str]]
) -> str:
    """Sort by the given list of fields.

    Each entry in the list is a 2-tuple: (fieldname, sort_order)
    eg - [(u'metadata_modified', u'desc'), (u'name', u'asc')]
    If fields is empty, then the default ordering is used.
    """
    params = params_nosort[:]

    if fields:
        sort_string = ", ".join("%s %s" % f for f in fields)
        params.append(("sort", sort_string))
    return search_url(params, package_type)


def _pager_url(
    params_nopage: Params,
    package_type: str,
    q: Any = None,  # noqa
    page: Optional[int] = None,
) -> str:
    params = list(params_nopage)
    params.append(("page", page))
    return search_url(params, package_type)


def _tag_string_to_list(tag_string: str) -> list[dict[str, str]]:
    """This is used to change tags from a sting to a list of dicts."""
    out: list[dict[str, str]] = []
    for tag in tag_string.split(","):
        tag = tag.strip()
        if tag:
            out.append({"name": tag, "state": "active"})
    return out


def _form_save_redirect(
    pkg_name: str, action: str, package_type: Optional[str] = None
) -> Response:
    """This redirects the user to the CKAN package/read page,
    unless there is request parameter giving an alternate location,
    perhaps an external website.
    @param pkg_name - Name of the package just edited
    @param action - What the action of the edit was
    """
    assert action in ("new", "edit")
    url = request.args.get("return_to") or config.get(
        "package_%s_return_url" % action
    )
    if url:
        url = url.replace("<NAME>", pkg_name)
    else:
        if not package_type:
            package_type = "dataset"
        url = h.url_for("{0}.read".format(package_type), id=pkg_name)
    return h.redirect_to(url)


def _get_package_type(id: str) -> str:
    """
    Given the id of a package this method will return the type of the
    package, or 'dataset' if no type is currently set
    """
    pkg = model.Package.get(id)
    if pkg:
        return pkg.type or "dataset"
    return "dataset"


def _get_search_details() -> dict[str, Any]:
    fq = ""

    # fields_grouped will contain a dict of params containing
    # a list of values eg {u'tags':[u'tag1', u'tag2']}

    fields = []
    fields_grouped = {}
    search_extras: "MultiDict[str, Any]" = MultiDict()

    for param, value in request.args.items(multi=True):
        if (
            param not in ["q", "page", "sort"]
            and len(value)
            and not param.startswith("_")
        ):
            if not param.startswith("ext_"):
                fields.append((param, value))
                fq += ' %s:"%s"' % (param, value)
                if param not in fields_grouped:
                    fields_grouped[param] = [value]
                else:
                    fields_grouped[param].append(value)
            else:
                search_extras.update({param: value})

    extras = dict(
        [
            (k, v[0]) if len(v) == 1 else (k, v)
            for k, v in search_extras.lists()
        ]
    )
    return {
        "fields": fields,
        "fields_grouped": fields_grouped,
        "fq": fq,
        "search_extras": extras,
    }


def search(package_type: str) -> str:
    extra_vars: dict[str, Any] = {}

    extra_vars["q"] = q = request.args.get("q", "")

    extra_vars["query_error"] = False
    page = h.get_page_number(request.args)

    limit = config.get("ckan.datasets_per_page")

    # most search operations should reset the page counter:
    params_nopage = [
        (k, v) for k, v in request.args.items(multi=True) if k != "page"
    ]

    extra_vars["remove_field"] = partial(remove_field, package_type)

    sort_by = request.args.get("sort", None)
    params_nosort = [(k, v) for k, v in params_nopage if k != "sort"]

    extra_vars["sort_by"] = partial(_sort_by, params_nosort, package_type)

    if not sort_by:
        sort_by_fields = []
    else:
        sort_by_fields = [field.split()[0] for field in sort_by.split(",")]
    extra_vars["sort_by_fields"] = sort_by_fields

    pager_url = partial(_pager_url, params_nopage, package_type)

    details = _get_search_details()
    extra_vars["fields"] = details["fields"]
    extra_vars["fields_grouped"] = details["fields_grouped"]
    fq = details["fq"]
    search_extras = details["search_extras"]

    context: Context = {
        "user": current_user.name,
        "for_view": True,
        "auth_user_obj": current_user,
    }

    # Unless changed via config options, don't show other dataset
    # types any search page. Potential alternatives are do show them
    # on the default search page (dataset) or on one other search page
    search_all_type = config.get("ckan.search.show_all_types")
    search_all = False

    try:
        # If the "type" is set to True or False, convert to bool
        # and we know that no type was specified, so use traditional
        # behaviour of applying this only to dataset type
        search_all = asbool(search_all_type)
        search_all_type = "dataset"
    # Otherwise we treat as a string representing a type
    except ValueError:
        search_all = True

    if not search_all or package_type != search_all_type:
        # Only show datasets of this particular type
        fq += " +dataset_type:{type}".format(type=package_type)

    facets: dict[str, str] = OrderedDict()

    org_label = h.humanize_entity_type(
        "organization", h.default_group_type("organization"), "facet label"
    ) or _("Organizations")

    group_label = h.humanize_entity_type(
        "group", h.default_group_type("group"), "facet label"
    ) or _("Groups")

    default_facet_titles = {
        "organization": org_label,
        "groups": group_label,
        "tags": _("Tags"),
        "res_format": _("Formats"),
        "license_id": _("Licenses"),
    }

    for facet in h.facets():
        if facet in default_facet_titles:
            facets[facet] = default_facet_titles[facet]
        else:
            facets[facet] = facet

    # Facet titles
    for plugin in plugins.PluginImplementations(plugins.IFacets):
        facets = plugin.dataset_facets(facets, package_type)

    extra_vars["facet_titles"] = facets
    data_dict: dict[str, Any] = {
        "q": q,
        "fq": fq.strip(),
        "facet.field": list(facets.keys()),
        "rows": limit,
        "start": (page - 1) * limit,
        "sort": sort_by,
        "extras": search_extras,
        "include_private": config.get("ckan.search.default_include_private"),
    }
    try:
        query = get_action("package_search")(context, data_dict)

        extra_vars["sort_by_selected"] = query["sort"]

        extra_vars["page"] = h.Page(
            collection=query["results"],
            page=page,
            url=pager_url,
            item_count=query["count"],
            items_per_page=limit,
        )
        extra_vars["search_facets"] = query["search_facets"]
        extra_vars["page"].items = query["results"]
    except SearchQueryError as se:
        # User's search parameters are invalid, in such a way that is not
        # achievable with the web interface, so return a proper error to
        # discourage spiders which are the main cause of this.
        log.info("Dataset search query rejected: %r", se.args)
        base.abort(
            400,
            _("Invalid search query: {error_message}").format(
                error_message=str(se)
            ),
        )
    except SearchError as se:
        # May be bad input from the user, but may also be more serious like
        # bad code causing a SOLR syntax error, or a problem connecting to
        # SOLR
        log.error("Dataset search error: %r", se.args)
        extra_vars["query_error"] = True
        extra_vars["search_facets"] = {}
        extra_vars["page"] = h.Page(collection=[])

    # FIXME: try to avoid using global variables
    g.search_facets_limits = {}
    default_limit: int = config.get("search.facets.default")
    for facet in extra_vars["search_facets"].keys():
        try:
            limit = int(request.args.get("_%s_limit" % facet, default_limit))
        except ValueError:
            base.abort(
                400,
                _('Parameter u"{parameter_name}" is not an integer').format(
                    parameter_name="_%s_limit" % facet
                ),
            )

        g.search_facets_limits[facet] = limit

    _setup_template_variables(context, {}, package_type=package_type)

    extra_vars["dataset_type"] = package_type

    # TODO: remove
    for key, value in extra_vars.items():
        setattr(g, key, value)

    return base.render(
        _get_pkg_template("search_template", package_type), extra_vars
    )


def resources(package_type: str, id: str) -> Union[Response, str]:
    context: Context = {
        "user": current_user.name,
        "for_view": True,
        "auth_user_obj": current_user,
    }
    data_dict: dict[str, Any] = {"id": id, "include_tracking": True}

    try:
        check_access("package_update", context, data_dict)
    except NotFound:
        return base.abort(404, _("Dataset not found"))
    except NotAuthorized:
        return base.abort(
            403,
            _("User %r not authorized to edit %s") % (current_user.name, id),
        )
    # check if package exists
    try:
        pkg_dict = get_action("package_show")(context, data_dict)
        pkg = context["package"]
    except (NotFound, NotAuthorized):
        return base.abort(404, _("Dataset not found"))

    package_type = pkg_dict["type"] or "dataset"
    _setup_template_variables(context, {"id": id}, package_type=package_type)

    # TODO: remove
    g.pkg_dict = pkg_dict
    g.pkg = pkg

    return base.render(
        "package/resources.html",
        {"dataset_type": package_type, "pkg_dict": pkg_dict, "pkg": pkg},
    )


def read(package_type: str, id: str) -> Union[Response, str]:
    context: Context = {
        "user": current_user.name,
        "for_view": True,
        "auth_user_obj": current_user,
    }
    data_dict = {"id": id, "include_tracking": True}

    # check if package exists
    try:
        pkg_dict = get_action("package_show")(context, data_dict)
        pkg = context["package"]
    except NotFound:
        return base.abort(
            404, _("Dataset not found or you have no permission to view it")
        )
    except NotAuthorized:
        if config.get("ckan.auth.reveal_private_datasets"):
            if current_user.is_authenticated:
                return base.abort(
                    403, _("Unauthorized to read package %s") % id
                )
            else:
                return h.redirect_to(
                    "user.login",
                    came_from=h.url_for("{}.read".format(package_type), id=id),
                )
        return base.abort(
            404, _("Dataset not found or you have no permission to view it")
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
    if (
        data_dict["id"] == pkg_dict["id"]
        and data_dict["id"] != pkg_dict["name"]
    ):
        kwargs = {
            **request.args,
            "id": pkg_dict["name"],
        }

        return h.redirect_to(
            h.url_for("{}.read".format(package_type), **kwargs)
        )

    # can the resources be previewed?
    for resource in pkg_dict["resources"]:
        resource_views = get_action("resource_view_list")(
            context, {"id": resource["id"]}
        )
        resource["has_views"] = len(resource_views) > 0

    package_type = pkg_dict["type"] or package_type
    _setup_template_variables(context, {"id": id}, package_type=package_type)

    template = _get_pkg_template("read_template", package_type)
    try:
        return base.render(
            template,
            {
                "dataset_type": package_type,
                "pkg_dict": pkg_dict,
                "pkg": pkg,
            },
        )
    except TemplateNotFound as e:
        msg = _(
            'Viewing datasets of type "{package_type}" is '
            "not supported ({file_!r}).".format(
                package_type=package_type, file_=e.message
            )
        )
        return base.abort(404, msg)


class CreateView(MethodView):
    def _is_save(self) -> bool:
        return "save" in request.form

    def _prepare(self) -> Context:  # noqa
        context: Context = {
            "user": current_user.name,
            "auth_user_obj": current_user,
            "save": self._is_save(),
        }
        try:
            check_access("package_create", context)
        except NotAuthorized:
            return base.abort(403, _("Unauthorized to create a package"))
        return context

    def post(self, package_type: str) -> Union[Response, str]:
        # The staged add dataset used the new functionality when the dataset is
        # partially created so we need to know if we actually are updating or
        # this is a real new.
        context = self._prepare()
        is_an_update = False
        ckan_phase = request.form.get("_ckan_phase")
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
            )
        except dict_fns.DataError:
            return base.abort(400, _("Integrity Error"))
        try:
            if ckan_phase:
                # prevent clearing of groups etc
                context["allow_partial_update"] = True
                # sort the tags
                if "tag_string" in data_dict:
                    data_dict["tags"] = _tag_string_to_list(
                        data_dict["tag_string"]
                    )
                if data_dict.get("pkg_name"):
                    is_an_update = True
                    # This is actually an update not a save
                    data_dict["id"] = data_dict["pkg_name"]
                    del data_dict["pkg_name"]
                    # don't change the dataset state
                    data_dict["state"] = "draft"
                    # this is actually an edit not a save
                    pkg_dict = get_action("package_update")(context, data_dict)

                    # redirect to add dataset resources
                    url = h.url_for(
                        "{}_resource.new".format(package_type),
                        id=pkg_dict["name"],
                    )
                    return h.redirect_to(url)
                # Make sure we don't index this dataset
                if request.form["save"] not in ["go-resource", "go-metadata"]:
                    data_dict["state"] = "draft"
                # allow the state to be changed
                context["allow_state_change"] = True

            data_dict["type"] = package_type
            pkg_dict = get_action("package_create")(context, data_dict)

            create_on_ui_requires_resources = config.get(
                "ckan.dataset.create_on_ui_requires_resources"
            )
            if ckan_phase:
                if create_on_ui_requires_resources:
                    # redirect to add dataset resources if
                    # create_on_ui_requires_resources is set to true
                    url = h.url_for(
                        "{}_resource.new".format(package_type),
                        id=pkg_dict["name"],
                    )
                    return h.redirect_to(url)

                get_action("package_update")(
                    Context(context, allow_state_change=True),
                    dict(pkg_dict, state="active"),
                )
                return h.redirect_to(
                    "{}.read".format(package_type), id=pkg_dict["id"]
                )

            return _form_save_redirect(
                pkg_dict["name"], "new", package_type=package_type
            )
        except NotAuthorized:
            return base.abort(403, _("Unauthorized to read package"))
        except NotFound:
            return base.abort(404, _("Dataset not found"))
        except SearchIndexError as e:
            try:
                exc_str = str(repr(e.args))
            except Exception:  # We don't like bare excepts
                exc_str = str(str(e))
            return base.abort(
                500, _("Unable to add package to search index.") + exc_str
            )
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            if is_an_update:
                # we need to get the state of the dataset to show the stage we
                # are on.
                pkg_dict = get_action("package_show")(context, data_dict)
                data_dict["state"] = pkg_dict["state"]
                return EditView().get(
                    package_type,
                    data_dict["id"],
                    data_dict,
                    errors,
                    error_summary,
                )
            data_dict["state"] = "none"
            return self.get(package_type, data_dict, errors, error_summary)

    def get(
        self,
        package_type: str,
        data: Optional[dict[str, Any]] = None,
        errors: Optional[dict[str, Any]] = None,
        error_summary: Optional[dict[str, Any]] = None,
    ) -> str:
        context = self._prepare()
        if data and "type" in data:
            package_type = data["type"]

        data = data or clean_dict(
            dict_fns.unflatten(
                tuplize_dict(
                    parse_params(request.args, ignore_keys=CACHE_PARAMETERS)
                )
            )
        )
        resources_json = h.json.dumps(data.get("resources", []))
        # convert tags if not supplied in data
        if data and not data.get("tag_string"):
            data["tag_string"] = ", ".join(
                h.dict_list_reduce(data.get("tags", {}), "name")
            )

        errors = errors or {}
        error_summary = error_summary or {}
        # in the phased add dataset we need to know that
        # we have already completed stage 1
        stage = ["active"]
        if data.get("state", "").startswith("draft"):
            stage = ["active", "complete"]

        # if we are creating from a group then this allows the group to be
        # set automatically
        data["group_id"] = request.args.get("group") or request.args.get(
            "groups__0__id"
        )

        form_snippet = _get_pkg_template(
            "package_form", package_type=package_type
        )
        form_vars: dict[str, Any] = {
            "data": data,
            "errors": errors,
            "error_summary": error_summary,
            "action": "new",
            "stage": stage,
            "dataset_type": package_type,
            "form_style": "new",
        }
        errors_json = h.json.dumps(errors)

        # TODO: remove
        g.resources_json = resources_json
        g.errors_json = errors_json

        _setup_template_variables(context, {}, package_type=package_type)

        new_template = _get_pkg_template("new_template", package_type)
        return base.render(
            new_template,
            extra_vars={
                "form_vars": form_vars,
                "form_snippet": form_snippet,
                "dataset_type": package_type,
                "resources_json": resources_json,
                "form_snippet": form_snippet,
                "errors_json": errors_json,
            },
        )


class EditView(MethodView):
    def _prepare(self) -> Context:
        context: Context = {
            "user": current_user.name,
            "auth_user_obj": current_user,
            "save": "save" in request.form,
        }
        return context

    def post(self, package_type: str, id: str) -> Union[Response, str]:
        context = self._prepare()
        package_type = _get_package_type(id) or package_type
        log.debug("Package save request name: %s POST: %r", id, request.form)
        try:
            data_dict = clean_dict(
                dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
            )
        except dict_fns.DataError:
            return base.abort(400, _("Integrity Error"))
        try:
            if "_ckan_phase" in data_dict:
                # we allow partial updates to not destroy existing resources
                context["allow_partial_update"] = True
                if "tag_string" in data_dict:
                    data_dict["tags"] = _tag_string_to_list(
                        data_dict["tag_string"]
                    )
                del data_dict["_ckan_phase"]
                del data_dict["save"]
            data_dict["id"] = id
            pkg_dict = get_action("package_update")(context, data_dict)

            return _form_save_redirect(
                pkg_dict["name"], "edit", package_type=package_type
            )
        except NotAuthorized:
            return base.abort(403, _("Unauthorized to read package %s") % id)
        except NotFound:
            return base.abort(404, _("Dataset not found"))
        except SearchIndexError as e:
            try:
                exc_str = str(repr(e.args))
            except Exception:  # We don't like bare excepts
                exc_str = str(str(e))
            return base.abort(
                500, _("Unable to update search index.") + exc_str
            )
        except ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(package_type, id, data_dict, errors, error_summary)

    def get(
        self,
        package_type: str,
        id: str,
        data: Optional[dict[str, Any]] = None,
        errors: Optional[dict[str, Any]] = None,
        error_summary: Optional[dict[str, Any]] = None,
    ) -> Union[Response, str]:
        context = self._prepare()
        package_type = _get_package_type(id) or package_type
        try:
            view_context = context.copy()
            view_context["for_view"] = True
            pkg_dict = get_action("package_show")(view_context, {"id": id})
            context["for_edit"] = True
            old_data = get_action("package_show")(context, {"id": id})
            # old data is from the database and data is passed from the
            # user if there is a validation error. Use users data if there.
            if data:
                old_data.update(data)
            data = old_data
        except (NotFound, NotAuthorized):
            return base.abort(404, _("Dataset not found"))
        assert data is not None
        # are we doing a multiphase add?
        if data.get("state", "").startswith("draft"):
            g.form_action = h.url_for("{}.new".format(package_type))
            g.form_style = "new"

            return CreateView().get(
                package_type,
                data=data,
                errors=errors,
                error_summary=error_summary,
            )

        pkg = context.get("package")
        resources_json = h.json.dumps(data.get("resources", []))
        user = current_user.name
        try:
            check_access("package_update", context, {"id": pkg_dict.get("id")})
        except NotAuthorized:
            return base.abort(
                403, _("User %r not authorized to edit %s") % (user, id)
            )
        # convert tags if not supplied in data
        if data and not data.get("tag_string"):
            data["tag_string"] = ", ".join(
                h.dict_list_reduce(pkg_dict.get("tags", {}), "name")
            )
        errors = errors or {}
        form_snippet = _get_pkg_template(
            "package_form", package_type=package_type
        )
        form_vars: dict[str, Any] = {
            "data": data,
            "errors": errors,
            "error_summary": error_summary,
            "action": "edit",
            "dataset_type": package_type,
            "form_style": "edit",
        }
        errors_json = h.json.dumps(errors)

        # TODO: remove
        g.pkg = pkg
        g.resources_json = resources_json
        g.errors_json = errors_json

        _setup_template_variables(
            context, {"id": id}, package_type=package_type
        )

        # we have already completed stage 1
        form_vars["stage"] = ["active"]
        if data.get("state", "").startswith("draft"):
            form_vars["stage"] = ["active", "complete"]

        edit_template = _get_pkg_template("edit_template", package_type)
        return base.render(
            edit_template,
            extra_vars={
                "form_vars": form_vars,
                "form_snippet": form_snippet,
                "dataset_type": package_type,
                "pkg_dict": pkg_dict,
                "pkg": pkg,
                "resources_json": resources_json,
                "form_snippet": form_snippet,
                "errors_json": errors_json,
            },
        )


class DeleteView(MethodView):
    def _prepare(self) -> Context:
        context: Context = {
            "user": current_user.name,
            "auth_user_obj": current_user,
        }
        return context

    def post(self, package_type: str, id: str) -> Response:
        if "cancel" in request.form:
            return h.redirect_to("{}.edit".format(package_type), id=id)
        context = self._prepare()
        try:
            get_action("package_delete")(context, {"id": id})
        except NotFound:
            return base.abort(404, _("Dataset not found"))
        except NotAuthorized:
            return base.abort(403, _("Unauthorized to delete package %s") % "")

        h.flash_notice(_("Dataset has been deleted."))
        return h.redirect_to(package_type + ".search")

    def get(self, package_type: str, id: str) -> Union[Response, str]:
        context = self._prepare()
        try:
            pkg_dict = get_action("package_show")(context, {"id": id})
        except NotFound:
            return base.abort(404, _("Dataset not found"))
        except NotAuthorized:
            return base.abort(403, _("Unauthorized to delete package %s") % "")

        dataset_type = pkg_dict["type"] or package_type

        # TODO: remove
        g.pkg_dict = pkg_dict

        return base.render(
            "package/confirm_delete.html",
            {"pkg_dict": pkg_dict, "dataset_type": dataset_type},
        )


def follow(package_type: str, id: str) -> Response:
    """Start following this dataset."""
    context: Context = {
        "user": current_user.name,
        "auth_user_obj": current_user,
    }
    data_dict = {"id": id}
    try:
        get_action("follow_dataset")(context, data_dict)
        package_dict = get_action("package_show")(context, data_dict)
        id = package_dict["name"]
    except ValidationError as e:
        error_message = e.message or e.error_summary or e.error_dict
        h.flash_error(error_message)
    except NotAuthorized as e:
        h.flash_error(e.message)
    else:
        h.flash_success(
            _("You are now following {0}").format(package_dict["title"])
        )

    return h.redirect_to("{}.read".format(package_type), id=id)


def unfollow(package_type: str, id: str) -> Union[Response, str]:
    """Stop following this dataset."""
    context: Context = {
        "user": current_user.name,
        "auth_user_obj": current_user,
    }
    data_dict = {"id": id}
    try:
        get_action("unfollow_dataset")(context, data_dict)
        package_dict = get_action("package_show")(context, data_dict)
        id = package_dict["name"]
    except ValidationError as e:
        error_message = e.message or e.error_summary or e.error_dict
        h.flash_error(error_message)
    except NotFound as e:
        error_message = e.message or ""
        base.abort(404, _(error_message))
    except NotAuthorized as e:
        error_message = e.message or ""
        base.abort(403, _(error_message))
    else:
        h.flash_success(
            _("You are no longer following {0}").format(package_dict["title"])
        )

    return h.redirect_to("{}.read".format(package_type), id=id)


def followers(
    package_type: str, id: Optional[str] = None
) -> Union[Response, str]:
    context: Context = {
        "user": current_user.name,
        "for_view": True,
        "auth_user_obj": current_user,
    }

    data_dict = {"id": id}
    try:
        pkg_dict = get_action("package_show")(context, data_dict)
        pkg = context["package"]
        followers = get_action("dataset_follower_list")(
            context, {"id": pkg_dict["id"]}
        )

        dataset_type = pkg.type or package_type
    except NotFound:
        return base.abort(404, _("Dataset not found"))
    except NotAuthorized:
        return base.abort(403, _("Unauthorized to read package %s") % id)

    # TODO: remove
    g.pkg_dict = pkg_dict
    g.pkg = pkg
    g.followers = followers

    return base.render(
        "package/followers.html",
        {
            "dataset_type": dataset_type,
            "pkg_dict": pkg_dict,
            "pkg": pkg,
            "followers": followers,
        },
    )


class GroupView(MethodView):
    def _prepare(self, id: str) -> tuple[Context, dict[str, Any]]:
        context: Context = {
            "user": current_user.name,
            "for_view": True,
            "auth_user_obj": current_user,
            "use_cache": False,
        }

        try:
            pkg_dict = get_action("package_show")(context, {"id": id})
        except (NotFound, NotAuthorized):
            return base.abort(404, _("Dataset not found"))
        return context, pkg_dict

    def post(self, package_type: str, id: str) -> Response:
        context = self._prepare(id)[0]
        new_group = request.form.get("group_added")
        if new_group:
            data_dict = {
                "id": new_group,
                "object": id,
                "object_type": "package",
                "capacity": "public",
            }
            try:
                get_action("member_create")(context, data_dict)
            except NotFound:
                return base.abort(404, _("Group not found"))

        removed_group = None
        for param in request.form:
            if param.startswith("group_remove"):
                removed_group = param.split(".")[-1]
                break
        if removed_group:
            data_dict = {
                "id": removed_group,
                "object": id,
                "object_type": "package",
            }

            try:
                get_action("member_delete")(context, data_dict)
            except NotFound:
                return base.abort(404, _("Group not found"))
        return h.redirect_to("{}.groups".format(package_type), id=id)

    def get(self, package_type: str, id: str) -> str:
        context, pkg_dict = self._prepare(id)
        dataset_type = pkg_dict["type"] or package_type
        context["is_member"] = True
        users_groups = get_action("group_list_authz")(context, {"id": id})

        pkg_group_ids = set(
            group["id"] for group in pkg_dict.get("groups", [])
        )

        user_group_ids = set(group["id"] for group in users_groups)

        group_dropdown = [
            [group["id"], group["display_name"]]
            for group in users_groups
            if group["id"] not in pkg_group_ids
        ]

        for group in pkg_dict.get("groups", []):
            group["user_member"] = group["id"] in user_group_ids

        # TODO: remove
        g.pkg_dict = pkg_dict
        g.group_dropdown = group_dropdown

        return base.render(
            "package/group_list.html",
            {
                "dataset_type": dataset_type,
                "pkg_dict": pkg_dict,
                "group_dropdown": group_dropdown,
            },
        )


def collaborators_read(
    package_type: str, id: str
) -> Union[Response, str]:  # noqa
    context: Context = {"user": current_user.name}
    data_dict = {"id": id}

    try:
        check_access("package_collaborator_list", context, data_dict)
        # needed to ckan_extend package/edit_base.html
        pkg_dict = get_action("package_show")(context, data_dict)
    except NotAuthorized:
        message = _("Unauthorized to read collaborators {}").format(id)
        return base.abort(401, message)
    except NotFound:
        return base.abort(404, _("Dataset not found"))

    return base.render(
        "package/collaborators/collaborators.html", {"pkg_dict": pkg_dict}
    )


def collaborator_delete(
    package_type: str, id: str, user_id: str
) -> Response:  # noqa
    context: Context = {"user": current_user.name}

    try:
        get_action("package_collaborator_delete")(
            context, {"id": id, "user_id": user_id}
        )
    except NotAuthorized:
        message = _("Unauthorized to delete collaborators {}").format(id)
        return base.abort(401, _(message))
    except NotFound as e:
        return base.abort(404, _(e.message))

    h.flash_success(_("User removed from collaborators"))

    return h.redirect_to("dataset.collaborators_read", id=id)


class CollaboratorEditView(MethodView):
    def post(self, package_type: str, id: str) -> Response:  # noqa
        context: Context = {"user": current_user.name}

        try:
            form_dict = logic.clean_dict(
                dict_fns.unflatten(
                    logic.tuplize_dict(logic.parse_params(request.form))
                )
            )

            user = get_action("user_show")(
                context, {"id": form_dict["username"]}
            )

            data_dict: dict[str, Any] = {
                "id": id,
                "user_id": user["id"],
                "capacity": form_dict["capacity"],
            }

            get_action("package_collaborator_create")(context, data_dict)

        except dict_fns.DataError:
            return base.abort(400, _("Integrity Error"))
        except NotAuthorized:
            message = _("Unauthorized to edit collaborators {}").format(id)
            return base.abort(401, _(message))
        except NotFound:
            h.flash_error(_("User not found"))
            return h.redirect_to("dataset.new_collaborator", id=id)
        except ValidationError as e:
            h.flash_error(e.error_summary)
            return h.redirect_to("dataset.new_collaborator", id=id)
        else:
            h.flash_success(_("User added to collaborators"))

        return h.redirect_to("dataset.collaborators_read", id=id)

    def get(self, package_type: str, id: str) -> Union[Response, str]:  # noqa
        context: Context = {"user": current_user.name}
        data_dict = {"id": id}

        try:
            check_access("package_collaborator_list", context, data_dict)
            # needed to ckan_extend package/edit_base.html
            pkg_dict = get_action("package_show")(context, data_dict)
        except NotAuthorized:
            message = "Unauthorized to read collaborators {}".format(id)
            return base.abort(401, _(message))
        except NotFound:
            return base.abort(404, _("Resource not found"))

        user = request.args.get("user_id")
        user_capacity = "member"

        if user:
            collaborators = get_action("package_collaborator_list")(
                context, data_dict
            )
            for c in collaborators:
                if c["user_id"] == user:
                    user_capacity = c["capacity"]
            user = get_action("user_show")(context, {"id": user})

        capacities: list[dict[str, str]] = []
        if authz.check_config_permission("allow_admin_collaborators"):
            capacities.append({"name": "admin", "value": "admin"})
        capacities.extend(
            [
                {"name": "editor", "value": "editor"},
                {"name": "member", "value": "member"},
            ]
        )

        extra_vars: dict[str, Any] = {
            "capacities": capacities,
            "user_capacity": user_capacity,
            "user": user,
            "pkg_dict": pkg_dict,
        }

        return base.render(
            "package/collaborators/collaborator_new.html", extra_vars
        )


def register_dataset_plugin_rules(blueprint: Blueprint):
    blueprint.add_url_rule("/", view_func=search, strict_slashes=False)
    blueprint.add_url_rule("/new", view_func=CreateView.as_view(str("new")))
    blueprint.add_url_rule("/<id>", view_func=read)
    blueprint.add_url_rule("/resources/<id>", view_func=resources)
    blueprint.add_url_rule(
        "/edit/<id>", view_func=EditView.as_view(str("edit"))
    )
    blueprint.add_url_rule(
        "/delete/<id>", view_func=DeleteView.as_view(str("delete"))
    )
    blueprint.add_url_rule("/follow/<id>", view_func=follow, methods=("POST",))
    blueprint.add_url_rule(
        "/unfollow/<id>", view_func=unfollow, methods=("POST",)
    )
    blueprint.add_url_rule("/followers/<id>", view_func=followers)
    blueprint.add_url_rule(
        "/groups/<id>", view_func=GroupView.as_view(str("groups"))
    )

    if authz.check_config_permission("allow_dataset_collaborators"):
        blueprint.add_url_rule(
            rule="/collaborators/<id>",
            view_func=collaborators_read,
            methods=[
                "GET",
            ],
        )

        blueprint.add_url_rule(
            rule="/collaborators/<id>/new",
            view_func=CollaboratorEditView.as_view(str("new_collaborator")),
            methods=[
                "GET",
                "POST",
            ],
        )

        blueprint.add_url_rule(
            rule="/collaborators/<id>/delete/<user_id>",
            view_func=collaborator_delete,
            methods=[
                "POST",
            ],
        )


register_dataset_plugin_rules(dataset)
# remove this when we improve blueprint registration to be explicit:
dataset.auto_register = False  # type: ignore
