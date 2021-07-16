# encoding: utf-8

import itertools

import click
import json

import ckan.logic as logic
import ckan.model as model
import ckan.plugins as p
from ckan.cli import error_shout
from ckan.lib.datapreview import (
    add_views_to_dataset_resources,
    get_view_plugins,
    get_default_view_plugins,
)


_page_size = 100


@click.group(short_help="Manage resource views.")
def views():
    """Manage resource views.
    """
    pass


@views.command()
@click.argument("types", nargs=-1)
@click.option("-d", "--dataset", multiple=True)
@click.option("--no-default-filters", is_flag=True)
@click.option("-s", "--search")
@click.option("-y", "--yes", is_flag=True)
@click.pass_context
def create(ctx, types, dataset, no_default_filters, search, yes):
    """Create views on relevant resources. You can optionally provide
    specific view types (eg `recline_view`, `image_view`). If no types
    are provided, the default ones will be used. These are generally
    the ones defined in the `ckan.views.default_views` config option.
    Note that on either case, plugins must be loaded (ie added to
    `ckan.plugins`), otherwise the command will stop.

    """

    datastore_enabled = (
        "datastore" in p.toolkit.config["ckan.plugins"].split()
    )

    flask_app = ctx.meta['flask_app']
    with flask_app.test_request_context():
        loaded_view_plugins = _get_view_plugins(types, datastore_enabled)
    if loaded_view_plugins is None:
        return
    site_user = logic.get_action("get_site_user")({"ignore_auth": True}, {})
    context = {"user": site_user["name"]}

    page = 1
    while True:
        query = _search_datasets(
            page, loaded_view_plugins, dataset, search, no_default_filters
        )
        if query is None:
            return
        if page == 1 and query["count"] == 0:
            return error_shout(
                "No datasets to create resource views on, exiting..."
            )

        elif page == 1 and not yes:

            msg = (
                "\nYou are about to check {0} datasets for the "
                + "following view plugins: {1}\n"
                + " Do you want to continue?"
            )

            click.confirm(
                msg.format(query["count"], loaded_view_plugins), abort=True
            )

        if query["results"]:
            for dataset_dict in query["results"]:

                if not dataset_dict.get("resources"):
                    continue
                with flask_app.test_request_context():
                    views = add_views_to_dataset_resources(
                        context, dataset_dict, view_types=loaded_view_plugins
                    )

                if views:
                    view_types = list({view["view_type"] for view in views})
                    msg = (
                        "Added {0} view(s) of type(s) {1} to "
                        + "resources from dataset {2}"
                    )
                    click.secho(
                        msg.format(
                            len(views),
                            ", ".join(view_types),
                            dataset_dict["name"],
                        )
                    )

            if len(query["results"]) < _page_size:
                break

            page += 1
        else:
            break

    click.secho("Done", fg="green")


@views.command()
@click.argument("types", nargs=-1)
@click.option("-y", "--yes", is_flag=True)
def clear(types, yes):
    """Permanently delete all views or the ones with the provided types.

    """

    if not yes:
        if types:
            msg = (
                "Are you sure you want to delete all resource views "
                + "of type {0}?".format(", ".join(types))
            )
        else:
            msg = "Are you sure you want to delete all resource views?"
        click.confirm(msg, abort=True)

    site_user = logic.get_action("get_site_user")({"ignore_auth": True}, {})

    context = {"user": site_user["name"]}
    logic.get_action("resource_view_clear")(context, {"view_types": types})

    click.secho("Done", fg="green")


@views.command()
@click.option("-y", "--yes", is_flag=True)
@click.pass_context
def clean(ctx, yes):
    """Permanently delete views for all types no longer present in the
    `ckan.plugins` configuration option.

    """
    names = []
    flask_app = ctx.meta['flask_app']
    with flask_app.test_request_context():
        for plugin in p.PluginImplementations(p.IResourceView):
            names.append(str(plugin.info()["name"]))

    results = model.ResourceView.get_count_not_in_view_types(names)

    if not results:
        return click.secho("No resource views to delete", fg="red")

    click.secho("This command will delete.\n")
    for row in results:
        click.secho("%s of type %s" % (row[1], row[0]))

    yes or click.confirm(
        "Do you want to delete these resource views?", abort=True
    )

    model.ResourceView.delete_not_in_view_types(names)
    model.Session.commit()
    click.secho("Deleted resource views.", fg="green")


def _get_view_plugins(view_plugin_types, get_datastore_views=False):
    """Returns the view plugins that were succesfully loaded

    Views are provided as a list of ``view_plugin_types``. If no types
    are provided, the default views defined in the
    ``ckan.views.default_views`` will be created. Only in this case
    (when the default view plugins are used) the `get_datastore_views`
    parameter can be used to get also view plugins that require data
    to be in the DataStore.

    If any of the provided plugins could not be loaded (eg it was not
    added to `ckan.plugins`) the command will stop.

    Returns a list of loaded plugin names.

    """

    view_plugins = []

    if not view_plugin_types:
        click.secho("No view types provided, using default types")
        view_plugins = get_default_view_plugins()
        if get_datastore_views:
            view_plugins.extend(
                get_default_view_plugins(get_datastore_views=True)
            )
    else:
        view_plugins = get_view_plugins(view_plugin_types)

    loaded_view_plugins = [
        view_plugin.info()["name"] for view_plugin in view_plugins
    ]

    plugins_not_found = list(set(view_plugin_types) - set(loaded_view_plugins))

    if plugins_not_found:
        error_shout(
            "View plugin(s) not found : {0}. ".format(plugins_not_found)
            + "Have they been added to the `ckan.plugins` configuration"
            + " option?"
        )
        return None
    return loaded_view_plugins


def _search_datasets(
    page=1, view_types=[], dataset=[], search="", no_default_filters=False
):
    """
    Perform a query with `package_search` and return the result

    Results can be paginated using the `page` parameter
    """

    n = _page_size

    search_data_dict = {
        "q": "",
        "fq": "",
        "fq_list": [],
        "include_private": True,
        "rows": n,
        "start": n * (page - 1),
    }

    if dataset:

        search_data_dict["q"] = " OR ".join(
            [
                'id:{0} OR name:"{0}"'.format(dataset_id)
                for dataset_id in dataset
            ]
        )

    elif search:

        search_data_dict = _update_search_params(search_data_dict, search)
        if search_data_dict is None:
            return None

    elif not no_default_filters:

        _add_default_filters(search_data_dict, view_types)

    if not search_data_dict.get("q"):
        search_data_dict["q"] = "*:*"

    query = p.toolkit.get_action("package_search")({}, search_data_dict)

    return query


def _add_default_filters(search_data_dict, view_types):
    """
    Adds extra filters to the `package_search` dict for common view types

    It basically adds `fq` parameters that filter relevant resource formats
    for the view types provided. For instance, if one of the view types is
    `pdf_view` the following will be added to the final query:

        fq=res_format:"pdf" OR res_format:"PDF"

    This obviously should only be used if all view types are known and can
    be filtered, otherwise we want all datasets to be returned. If a
    non-filterable view type is provided, the search params are not
    modified.

    Returns the provided data_dict for `package_search`, optionally
    modified with extra filters.
    """

    from ckanext.imageview.plugin import DEFAULT_IMAGE_FORMATS
    from ckanext.textview.plugin import get_formats as get_text_formats
    from ckanext.datapusher.plugin import DEFAULT_FORMATS as datapusher_formats

    filter_formats = []

    for view_type in view_types:
        if view_type == "image_view":

            for _format in DEFAULT_IMAGE_FORMATS:
                filter_formats.extend([_format, _format.upper()])

        elif view_type == "text_view":
            formats = get_text_formats(p.toolkit.config)
            for _format in itertools.chain.from_iterable(formats.values()):
                filter_formats.extend([_format, _format.upper()])

        elif view_type == "pdf_view":
            filter_formats.extend(["pdf", "PDF"])

        elif view_type in [
            "recline_view",
            "recline_grid_view",
            "recline_graph_view",
            "recline_map_view",
        ]:

            if datapusher_formats[0] in filter_formats:
                continue

            for _format in datapusher_formats:
                if "/" not in _format:
                    filter_formats.extend([_format, _format.upper()])
        else:
            # There is another view type provided so we can't add any
            # filter
            return search_data_dict

    filter_formats_query = [
        '+res_format:"{0}"'.format(_format) for _format in filter_formats
    ]
    search_data_dict["fq_list"].append(" OR ".join(filter_formats_query))

    return search_data_dict


def _update_search_params(search_data_dict, search):
    """
    Update the `package_search` data dict with the user provided parameters

    Supported fields are `q`, `fq` and `fq_list`.

    If the provided JSON object can not be parsed the process stops with
    an error.

    Returns the updated data dict
    """

    if not search:
        return search_data_dict

    try:
        user_search_params = json.loads(search)
    except ValueError as e:
        error_shout("Unable to parse JSON search parameters: {0}".format(e))
        return None

    if user_search_params.get("q"):
        search_data_dict["q"] = user_search_params["q"]

    if user_search_params.get("fq"):
        if search_data_dict["fq"]:
            search_data_dict["fq"] += " " + user_search_params["fq"]
        else:
            search_data_dict["fq"] = user_search_params["fq"]

    if user_search_params.get("fq_list") and isinstance(
        user_search_params["fq_list"], list
    ):
        search_data_dict["fq_list"].extend(user_search_params["fq_list"])
    return search_data_dict
