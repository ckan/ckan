from __future__ import annotations

from ckan import model
from ckan.common import _, asbool
from ckan.lib import datapreview
from ckan.lib.dictization import model_dictize, model_save
from ckan.lib.navl.dictization_functions import validate as _validate
from ckan.logic import (
    NotFound,
    ValidationError,
    side_effect_free,
)
from ckan.logic import check_access as _check_access
from ckan.logic import get_or_bust as _get_or_bust
from ckan.logic import schema as schema_
from ckan.types import ActionResult, Context, DataDict, Schema


def resource_view_create(
    context: Context, data_dict: DataDict
) -> ActionResult.ResourceViewCreate:
    """Creates a new resource view.

    :param resource_id: id of the resource
    :type resource_id: string
    :param title: the title of the view
    :type title: string
    :param description: a description of the view (optional)
    :type description: string
    :param view_type: type of view
    :type view_type: string
    :param config: options necessary to recreate a view state (optional)
    :type config: JSON string

    :returns: the newly created resource view
    :rtype: dictionary

    """
    resource_id = _get_or_bust(data_dict, "resource_id")
    view_type = _get_or_bust(data_dict, "view_type")
    view_plugin = datapreview.get_view_plugin(view_type)

    if not view_plugin:
        raise ValidationError(
            {
                "view_type": "No plugin found for view_type {view_type}".format(
                    view_type=view_type
                )
            }
        )

    default: Schema = schema_.default_create_resource_view_schema(view_plugin)
    schema: Schema = context.get("schema", default)
    plugin_schema: Schema = view_plugin.info().get("schema", {})
    schema.update(plugin_schema)

    data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    _check_access("resource_view_create", context, data_dict)

    if context.get("preview"):
        return data

    last_view = (
        model.Session.query(model.ResourceView)
        .filter_by(resource_id=resource_id)
        .order_by(model.ResourceView.order.desc())
        .first()
    )

    if not last_view:
        order = 0
    else:
        order = last_view.order + 1
    data["order"] = order

    resource_view = model_save.resource_view_dict_save(data, context)
    if not context.get("defer_commit"):
        model.repo.commit()
    return model_dictize.resource_view_dictize(resource_view, context)


def resource_create_default_resource_views(
    context: Context, data_dict: DataDict
) -> ActionResult.ResourceCreateDefaultResourceViews:
    """
    Creates the default views (if necessary) on the provided resource

    The function will get the plugins for the default views defined in
    the configuration, and if some were found the `can_view` method of
    each one of them will be called to determine if a resource view should
    be created. Resource views extensions get the resource dict and the
    parent package dict.

    If the latter is not provided, `package_show` is called to get it.

    By default only view plugins that don't require the resource data to be in
    the DataStore are called. See
    :py:func:`~ckan.logic.action.resource_view.package_create_default_resource_views`
    for details on the ``create_datastore_views`` parameter.

    :param resource: full resource dict
    :type resource: dict
    :param package: full package dict (optional, if not provided
        :py:func:`~ckan.logic.action.package.package_show` will be called).
    :type package: dict
    :param create_datastore_views: whether to create views that rely on data
        being on the DataStore (optional, defaults to False)
    :type create_datastore_views: bool

    :returns: a list of resource views created (empty if none were created)
    :rtype: list of dictionaries
    """

    resource_dict = _get_or_bust(data_dict, "resource")

    _check_access("resource_create_default_resource_views", context, data_dict)

    dataset_dict = data_dict.get("package")

    create_datastore_views = asbool(data_dict.get("create_datastore_views", False))

    return datapreview.add_views_to_resource(
        context,
        resource_dict,
        dataset_dict,
        view_types=[],
        create_datastore_views=create_datastore_views,
    )


def package_create_default_resource_views(
    context: Context, data_dict: DataDict
) -> ActionResult.PackageCreateDefaultResourceViews:
    """
    Creates the default views on all resources of the provided package

    By default only view plugins that don't require the resource data to be in
    the DataStore are called. Passing `create_datastore_views` as True will
    only create views that require data to be in the DataStore. The first case
    happens when the function is called from `package_create` or
    `package_update`, the second when it's called from the DataPusher when
    data was uploaded to the DataStore.

    :param package: full package dict (ie the one obtained
        calling :py:func:`~ckan.logic.action.package.package_show`).
    :type package: dict
    :param create_datastore_views: whether to create views that rely on data
        being on the DataStore (optional, defaults to False)
    :type create_datastore_views: bool

    :returns: a list of resource views created (empty if none were created)
    :rtype: list of dictionaries
    """

    dataset_dict = _get_or_bust(data_dict, "package")

    _check_access("package_create_default_resource_views", context, data_dict)

    create_datastore_views = asbool(data_dict.get("create_datastore_views", False))

    return datapreview.add_views_to_dataset_resources(
        context,
        dataset_dict,
        view_types=[],
        create_datastore_views=create_datastore_views,
    )


@side_effect_free
def resource_view_show(
    context: Context, data_dict: DataDict
) -> ActionResult.ResourceViewShow:
    """
    Return the metadata of a resource_view.

    :param id: the id of the resource_view
    :type id: string

    :rtype: dictionary
    """
    id = _get_or_bust(data_dict, "id")

    resource_view = model.ResourceView.get(id)
    if not resource_view:
        _check_access("resource_view_show", context, data_dict)
        raise NotFound

    context["resource_view"] = resource_view
    resource = model.Resource.get(resource_view.resource_id)
    if not resource:
        raise NotFound
    context["resource"] = resource

    _check_access("resource_view_show", context, data_dict)
    return model_dictize.resource_view_dictize(resource_view, context)


@side_effect_free
def resource_view_list(
    context: Context, data_dict: DataDict
) -> ActionResult.ResourceViewList:
    """
    Return the list of resource views for a particular resource.

    :param id: the id of the resource
    :type id: string

    :rtype: list of dictionaries.
    """
    id = _get_or_bust(data_dict, "id")
    resource = model.Resource.get(id)
    if not resource:
        raise NotFound
    context["resource"] = resource
    _check_access("resource_view_list", context, data_dict)
    q = model.Session.query(model.ResourceView).filter_by(resource_id=id)
    ## only show views when there is the correct plugin enabled
    resource_views = [
        resource_view
        for resource_view in q.order_by(model.ResourceView.order).all()
        if datapreview.get_view_plugin(resource_view.view_type)
    ]
    return model_dictize.resource_view_list_dictize(resource_views, context)


def resource_view_update(
    context: Context, data_dict: DataDict
) -> ActionResult.ResourceViewUpdate:
    """Update a resource view.

    To update a resource_view you must be authorized to update the resource
    that the resource_view belongs to. ``resource_id`` may not be modified.

    For further parameters see ``resource_view_create()``.

    :param id: the id of the resource_view to update
    :type id: string

    :returns: the updated resource_view
    :rtype: string

    """
    id = _get_or_bust(data_dict, "id")

    resource_view = model.ResourceView.get(id)
    if not resource_view or (
        'resource_id' in data_dict
        and data_dict['resource_id'] != resource_view.resource_id
    ):
        raise NotFound(_("Resource view was not found."))

    view_plugin = datapreview.get_view_plugin(resource_view.view_type)
    schema = context.get("schema") or schema_.default_update_resource_view_schema(
        view_plugin
    )
    assert view_plugin
    plugin_schema = view_plugin.info().get("schema", {})
    schema.update(plugin_schema)

    data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    context["resource_view"] = resource_view
    resource = model.Resource.get(resource_view.resource_id)
    if resource is None:
        raise NotFound(_("Resource was not found."))
    context["resource"] = resource

    _check_access("resource_view_update", context, data_dict)

    if context.get("preview"):
        return data

    resource_view = model_save.resource_view_dict_save(data, context)
    if not context.get("defer_commit"):
        model.repo.commit()
    return model_dictize.resource_view_dictize(resource_view, context)


def resource_view_reorder(
    context: Context, data_dict: DataDict
) -> ActionResult.ResourceViewReorder:
    """Reorder resource views.

    :param id: the id of the resource
    :type id: string
    :param order: the list of id of the resource to update the order of the views
    :type order: list of strings

    :returns: the updated order of the view
    :rtype: dictionary
    """
    id, order = _get_or_bust(data_dict, ["id", "order"])
    if not isinstance(order, list):
        raise ValidationError({"order": _("Must supply order as a list")})
    if len(order) != len(set(order)):
        raise ValidationError({"order": _("No duplicates allowed in order")})
    resource = model.Resource.get(id)
    if resource is None:
        raise NotFound(_("Resource was not found."))
    context["resource"] = resource

    _check_access("resource_view_reorder", context, {"resource_id": id})

    q = model.Session.query(model.ResourceView.id).filter_by(resource_id=id)
    existing_views = [res[0] for res in q.order_by(model.ResourceView.order).all()]
    ordered_views = []
    for view in order:
        try:
            existing_views.remove(view)
            ordered_views.append(view)
        except ValueError:
            raise ValidationError(
                {"order": _("View %(view)s does not exist") % {"view": view}}
            )
    new_order = ordered_views + existing_views

    for num, view in enumerate(new_order):
        model.Session.query(model.ResourceView).filter_by(id=view).update(
            {"order": num + 1}
        )
    model.Session.commit()
    return {"id": id, "order": new_order}


def resource_view_delete(
    context: Context, data_dict: DataDict
) -> ActionResult.ResourceViewDelete:
    """Delete a resource_view.

    :param id: the id of the resource_view
    :type id: string

    """
    id = _get_or_bust(data_dict, "id")

    resource_view = model.ResourceView.get(id)
    if not resource_view:
        raise NotFound

    _check_access("resource_view_delete", context, {"id": id})

    resource_view.delete()
    model.repo.commit()

    # resource_view_changed in ckanext/activity/subscriptions.py
    # needs the resource id
    return {"resource_id": resource_view.resource_id}


def resource_view_clear(
    context: Context, data_dict: DataDict
) -> ActionResult.ResourceViewClear:
    """Delete all resource views, or all of a particular type.

    :param view_types: specific types to delete (optional)
    :type view_types: list

    """
    _check_access("resource_view_clear", context, data_dict)

    view_types = data_dict.get("view_types", [])
    model.ResourceView.delete_all(view_types)
    model.repo.commit()
