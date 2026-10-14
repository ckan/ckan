from __future__ import annotations

import logging
from typing import Any, Union, cast

import sqlalchemy
from sqlalchemy import text
import ckan
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.logic as logic
import ckan.model as model
import ckan.model.misc as misc
import ckan.plugins as plugins
import ckan.lib.search as search
from ckan.common import _
from ckan.logic import (
    NotFound,
    ValidationError,
    check_access as _check_access,
    fresh_context as _fresh_context,
    get_action as _get_action,
    get_or_bust as _get_or_bust,
    side_effect_free,
)
from ckan.types import ActionResult, Context, DataDict, ErrorDict

_and_ = sqlalchemy.and_
_func = sqlalchemy.func
_or_ = sqlalchemy.or_
log = logging.getLogger("ckan.logic")


def resource_create(
    context: Context, data_dict: DataDict
) -> ActionResult.ResourceCreate:
    """Appends a new resource to a datasets list of resources.

    :param package_id: id of package that the resource should be added to.

    :type package_id: string
    :param url: url of resource
    :type url: string
    :param description: (optional)
    :type description: string
    :param format: (optional)
    :type format: string
    :param hash: (optional)
    :type hash: string
    :param name: (optional)
    :type name: string
    :param resource_type: (optional)
    :type resource_type: string
    :param mimetype: (optional)
    :type mimetype: string
    :param mimetype_inner: (optional)
    :type mimetype_inner: string
    :param cache_url: (optional)
    :type cache_url: string
    :param size: (optional)
    :type size: int
    :param created: (optional)
    :type created: iso date string
    :param last_modified: (optional)
    :type last_modified: iso date string
    :param cache_last_updated: (optional)
    :type cache_last_updated: iso date string
    :param upload: (optional)
    :type upload: FieldStorage (optional) needs multipart/form-data

    :returns: the newly created resource
    :rtype: dictionary

    """
    package_id = _get_or_bust(data_dict, "package_id")
    if not data_dict.get("url"):
        data_dict["url"] = ""

    package_show_context: Union[Context, Any] = dict(context, for_update=True)
    pkg_dict = _get_action("package_show")(package_show_context, {"id": package_id})

    _check_access("resource_create", context, data_dict)

    for plugin in plugins.PluginImplementations(plugins.IResourceController):
        plugin.before_resource_create(context, data_dict)

    original_package = dict(pkg_dict)

    # allow metadata_modified to be updated
    pkg_dict.pop("metadata_modified", None)
    pkg_dict["resources"] = list(pkg_dict.get("resources", []))

    pkg_dict["resources"].append(data_dict)

    try:
        update_context = Context(context)
        update_context["original_package"] = original_package
        updated_pkg_dict = _get_action("package_update")(update_context, pkg_dict)
    except ValidationError as e:
        try:
            error_dict = cast("list[ErrorDict]", e.error_dict["resources"])[-1]
        except (KeyError, IndexError):
            error_dict = e.error_dict
        raise ValidationError(error_dict)

    resource = updated_pkg_dict["resources"][-1]

    #  Add the default views to the new resource
    logic.get_action("resource_create_default_resource_views")(
        {"user": context["user"], "ignore_auth": True},
        {"resource": resource, "package": updated_pkg_dict},
    )

    for plugin in plugins.PluginImplementations(plugins.IResourceController):
        plugin.after_resource_create(context, resource)

    return resource


@side_effect_free
def resource_show(context: Context, data_dict: DataDict) -> ActionResult.ResourceShow:
    """Return the metadata of a resource.

    :param id: the id of the resource
    :type id: string

    :rtype: dictionary

    """
    id = _get_or_bust(data_dict, "id")

    resource = model.Resource.get(id)
    if not resource:
        raise NotFound

    resource_context = Context(context, resource=resource)
    _check_access("resource_show", resource_context, data_dict)

    pkg_dict = logic.get_action("package_show")(
        context.copy(), {"id": resource.package.id}
    )

    for resource_dict in pkg_dict["resources"]:
        if resource_dict["id"] == id:
            break
    else:
        log.error(
            "Resource %s exists but it is not found in the package it should belong to.",
            id,
        )
        raise NotFound(_("Resource was not found."))

    return resource_dict


@side_effect_free
@logic.validate(ckan.logic.schema.default_autocomplete_schema)
def format_autocomplete(
    context: Context, data_dict: DataDict
) -> ActionResult.FormatAutocomplete:
    """Return a list of resource formats whose names contain a string.

    :param q: the string to search for
    :type q: string
    :param limit: the maximum number of resource formats to return (optional,
        default: ``5``)
    :type limit: int

    :rtype: list of strings

    """
    session = context["session"]

    _check_access("format_autocomplete", context, data_dict)

    q = data_dict["q"]
    limit = data_dict.get("limit", 5)

    like_q = "%" + q + "%"

    query = (
        session.query(
            model.Resource.format, _func.count(model.Resource.format).label("total")
        )
        .filter(
            _and_(
                model.Resource.state == "active",
            )
        )
        .filter(model.Resource.format.ilike(like_q))
        .group_by(model.Resource.format)
        .order_by(text("total DESC"))
        .limit(limit)
    )

    return [resource.format.lower() for resource in query]


@side_effect_free
@logic.validate(ckan.logic.schema.default_resource_search_schema)
def resource_search(
    context: Context, data_dict: DataDict
) -> ActionResult.ResourceSearch:
    """
    Searches for resources in public Datasets satisfying the search criteria.

    It returns a dictionary with 2 fields: ``count`` and ``results``.  The
    ``count`` field contains the total number of Resources found without the
    limit or query parameters having an effect.  The ``results`` field is a
    list of dictized Resource objects.

    The 'query' parameter is a required field.  It is a string of the form
    ``{field}:{term}`` or a list of strings, each of the same form. Within
    each string, ``{field}`` is a field or extra field on the Resource domain
    object.

    If ``{field}`` is ``"hash"``, then an attempt is made to match the
    `{term}` as a *prefix* of the ``Resource.hash`` field.

    If ``{field}`` is an extra field, then an attempt is made to match against
    the extra fields stored against the Resource.

    Note: The search is limited to search against extra fields declared in
    the config setting ``ckan.extra_resource_fields``.

    Note: Due to a Resource's extra fields being stored as a json blob, the
    match is made against the json string representation.  As such, false
    positives may occur:

    If the search criteria is: ::

        query = "field1:term1"

    Then a json blob with the string representation of: ::

        {"field1": "foo", "field2": "term1"}

    will match the search criteria!  This is a known short-coming of this
    approach.

    All matches are made ignoring case; and apart from the ``"hash"`` field,
    a term matches if it is a substring of the field's value.

    Finally, when specifying more than one search criteria, the criteria are
    AND-ed together.

    The ``order`` parameter is used to control the ordering of the results.
    Currently only ordering one field is available, and in ascending order
    only.

    The context may contain a flag, `search_query`, which if True will make
    this action behave as if being used by the internal search api.  ie - the
    results will not be dictized, and SearchErrors are thrown for bad search
    queries (rather than ValidationErrors).

    :param query: The search criteria.  See above for description.
    :type query: string or list of strings of the form ``{field}:{term1}``
    :param order_by: A field on the Resource model that orders the results.
    :type order_by: string
    :param offset: Apply an offset to the query.
    :type offset: int
    :param limit: Apply a limit to the query.
    :type limit: int

    :returns:  A dictionary with a ``count`` field, and a ``results`` field.
    :rtype: dict

    """
    _check_access("resource_search", context, data_dict)

    query = data_dict.get("query")
    order_by = data_dict.get("order_by")
    offset = data_dict.get("offset")
    limit = data_dict.get("limit")

    if query is None:
        raise ValidationError({"query": _("Missing value")})

    if isinstance(query, str):
        query = [query]

    try:
        fields = dict(pair.split(":", 1) for pair in query)
    except ValueError:
        raise ValidationError({"query": _("Must be <field>:<value> pair(s)")})

    q = (
        model.Session.query(model.Resource)
        .join(model.Package)
        .filter(model.Package.state == "active")
        .filter(model.Package.private == False)
        .filter(model.Resource.state == "active")
    )
    resource_fields = model.Resource.get_columns()
    for field, term in fields.items():
        if field not in resource_fields:
            msg = _('Field "{field}" not recognised in resource_search.').format(
                field=field
            )

            # Running in the context of the internal search api.
            if context.get("search_query", False):
                raise search.SearchError(msg)

            # Otherwise, assume we're in the context of an external api
            # and need to provide meaningful external error messages.
            raise ValidationError({"query": msg})

        # prevent pattern injection
        term = misc.escape_sql_like_special_characters(term)

        model_attr = getattr(model.Resource, field)

        # Treat the has field separately, see docstring.
        if field == "hash":
            q = q.filter(model_attr.ilike(str(term) + "%"))

        # Resource extras are stored in a json blob.  So searching for
        # matching fields is a bit trickier. See the docstring.
        elif field in model.Resource.get_extra_columns():
            model_attr = getattr(model.Resource, "extras")

            like = _or_(
                model_attr.ilike("""%%"%s": "%%%s%%",%%""" % (field, term)),
                model_attr.ilike("""%%"%s": "%%%s%%"}""" % (field, term)),
            )
            q = q.filter(like)

        # Just a regular field
        else:
            column = model_attr.property.columns[0]
            if isinstance(column.type, sqlalchemy.UnicodeText):
                q = q.filter(model_attr.ilike("%" + str(term) + "%"))
            else:
                q = q.filter(model_attr == term)

    if order_by is not None:
        if hasattr(model.Resource, order_by):
            q = q.order_by(getattr(model.Resource, order_by))

    count = q.count()
    q = q.offset(offset)
    q = q.limit(limit)

    results = []
    for result in q:
        if isinstance(result, tuple) and isinstance(result[0], model.DomainObject):
            # This is the case for order_by rank due to the add_column.
            results.append(result[0])
        else:
            results.append(result)

    # If run in the context of a search query, then don't dictize the results.
    if not context.get("search_query", False):
        results = model_dictize.resource_list_dictize(results, context)

    return {"count": count, "results": results}


def resource_update(
    context: Context, data_dict: DataDict
) -> ActionResult.ResourceUpdate:
    """Update a resource.

    To update a resource you must be authorized to update the dataset that the
    resource belongs to.

    .. note:: Update methods may delete parameters not explicitly provided in the
        data_dict. If you want to edit only a specific attribute use `resource_patch`
        instead.

    For further parameters see
    :py:func:`~ckan.logic.action.create.resource_create`.

    :param id: the id of the resource to update
    :type id: string

    :returns: the updated resource
    :rtype: string

    """
    rid: str = _get_or_bust(data_dict, "id")

    if not data_dict.get("url"):
        data_dict["url"] = ""

    resource = model.Resource.get(rid)
    if not resource:
        log.debug("Could not find resource %s", rid)
        raise NotFound(_("Resource was not found."))
    context["resource"] = resource
    old_resource_format = resource.format

    _check_access("resource_update", context, data_dict)
    del context["resource"]

    update_context = Context(context)
    pkg_dict = context.get("original_package")
    if not pkg_dict:
        package_id = resource.package.id
        package_show_context: Union[Context, Any] = dict(context, for_update=True)
        pkg_dict = _get_action("package_show")(package_show_context, {"id": package_id})

    update_context["original_package"] = dict(pkg_dict)
    # allow dataset metadata_modified to be updated
    pkg_dict.pop("metadata_modified", None)
    pkg_dict["resources"] = list(pkg_dict["resources"])

    resources = cast("list[dict[str, Any]]", pkg_dict["resources"])
    if resources[resource.position]["id"] != rid:
        log.error("Could not find resource %s after all", rid)
        raise NotFound(_("Resource was not found."))

    # Persist the datastore_active extra if already present and not provided
    if "datastore_active" in resource.extras and "datastore_active" not in data_dict:
        data_dict["datastore_active"] = resource.extras["datastore_active"]

    for plugin in plugins.PluginImplementations(plugins.IResourceController):
        plugin.before_resource_update(
            context, pkg_dict["resources"][resource.position], data_dict
        )

    resources[resource.position] = data_dict

    try:
        updated_pkg_dict = _get_action("package_update")(update_context, pkg_dict)
    except ValidationError as e:
        try:
            error_dict = cast("list[ErrorDict]", e.error_dict["resources"])[
                resource.position
            ]
        except (KeyError, IndexError):
            error_dict = e.error_dict
        raise ValidationError(error_dict)

    resource = updated_pkg_dict["resources"][resource.position]

    if old_resource_format != resource["format"]:
        _get_action("resource_create_default_resource_views")(
            {"user": context["user"], "ignore_auth": True},
            {"package": updated_pkg_dict, "resource": resource},
        )

    for plugin in plugins.PluginImplementations(plugins.IResourceController):
        plugin.after_resource_update(context, resource)

    return resource


def resource_patch(context: Context, data_dict: DataDict) -> ActionResult.ResourcePatch:
    """Patch a resource

    :param id: the id of the resource
    :type id: string

    The difference between the update and patch methods is that the patch will
    perform an update of the provided parameters, while leaving all other
    parameters unchanged, whereas the update methods deletes all parameters
    not explicitly provided in the data_dict
    """
    _check_access("resource_patch", context, data_dict)

    resource = model.Resource.get(_get_or_bust(data_dict, "id"))
    if not resource:
        raise NotFound("Resource was not found.")

    show_context: Context = _fresh_context(context)
    show_context.update({"for_update": True})

    package_dict = _get_action("package_show")(
        show_context, {"id": resource.package_id}
    )

    if package_dict["resources"][resource.position]["id"] != resource.id:
        raise NotFound("Resource was not found.")

    patched = dict(package_dict["resources"][resource.position])
    # allow metadata_modified to be updated if data has changed
    patched.pop("metadata_modified", None)

    patched.update(data_dict)
    update_context = Context(context)
    update_context["original_package"] = package_dict
    return _get_action("resource_update")(update_context, patched)


def package_resource_reorder(
    context: Context, data_dict: DataDict
) -> ActionResult.PackageResourceReorder:
    """Reorder resources against datasets.  If only partial resource ids are
    supplied then these are assumed to be first and the other resources will
    stay in their original order

    :param id: the id or name of the package to update
    :type id: string
    :param order: a list of resource ids in the order needed
    :type order: list
    """

    id = _get_or_bust(data_dict, "id")
    order = _get_or_bust(data_dict, "order")
    if not isinstance(order, list):
        raise ValidationError({"order": "Must be a list of resource"})

    if len(set(order)) != len(order):
        raise ValidationError({"order": "Must supply unique resource_ids"})

    package_show_context: Union[Context, Any] = dict(context, for_update=True)
    package_dict = _get_action("package_show")(package_show_context, {"id": id})

    # allow metadata_modified to be updated if data has changed
    # removes from original_package for comparison in package_update
    package_dict.pop("metadata_modified", None)

    existing_resources = list(package_dict.get("resources", []))
    ordered_resources = []

    for resource_id in order:
        for i in range(0, len(existing_resources)):
            if existing_resources[i]["id"] == resource_id:
                resource = existing_resources.pop(i)
                ordered_resources.append(resource)
                break
        else:
            raise ValidationError(
                {
                    "order": _("resource_id %(id)s can not be found")
                    % {"id": resource_id}
                }
            )

    new_resources = ordered_resources + existing_resources
    update_context = Context(context)
    update_context["original_package"] = dict(package_dict)
    package_dict["resources"] = new_resources

    _check_access("package_resource_reorder", context, package_dict)
    _get_action("package_update")(update_context, package_dict)

    return {"id": id, "order": [resource["id"] for resource in new_resources]}


def resource_delete(
    context: Context, data_dict: DataDict
) -> ActionResult.ResourceDelete:
    """Delete a resource from a dataset.

    You must be a sysadmin or the owner of the resource to delete it.

    :param id: the id of the resource
    :type id: string

    """
    id = _get_or_bust(data_dict, "id")

    entity = model.Resource.get(id)

    if entity is None:
        raise NotFound

    _check_access("resource_delete", context, data_dict)

    package_id = entity.get_package_id()

    pkg_dict = _get_action("package_show")(context, {"id": package_id})

    for plugin in plugins.PluginImplementations(plugins.IResourceController):
        plugin.before_resource_delete(context, data_dict, pkg_dict.get("resources", []))

    package_show_context: Union[Context, Any] = dict(context, for_update=True)
    pkg_dict = _get_action("package_show")(package_show_context, {"id": package_id})

    update_context = Context(context)
    update_context["original_package"] = dict(pkg_dict)

    if pkg_dict.get("resources"):
        pkg_dict["resources"] = [r for r in pkg_dict["resources"] if not r["id"] == id]
    try:
        pkg_dict = _get_action("package_update")(update_context, pkg_dict)
    except ValidationError as e:
        errors = cast("list[ErrorDict]", e.error_dict["resources"])[-1]
        raise ValidationError(errors)

    for plugin in plugins.PluginImplementations(plugins.IResourceController):
        plugin.after_resource_delete(context, pkg_dict.get("resources", []))

    model.repo.commit()
