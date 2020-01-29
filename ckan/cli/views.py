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


@click.group()
def views():
    """Manage resource views.
    """
    pass


@views.command()
@click.argument(u"types", nargs=-1)
@click.option(u"-d", u"--dataset", multiple=True)
@click.option(u"--no-default-filters", is_flag=True)
@click.option(u"-s", u"--search")
@click.option(u"-y", u"--yes", is_flag=True)
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
        u"datastore" in p.toolkit.config[u"ckan.plugins"].split()
    )

    flask_app = ctx.meta['flask_app']
    with flask_app.test_request_context():
        loaded_view_plugins = _get_view_plugins(types, datastore_enabled)
    if loaded_view_plugins is None:
        return
    site_user = logic.get_action(u"get_site_user")({u"ignore_auth": True}, {})
    context = {u"user": site_user[u"name"]}

    page = 1
    while True:
        query = _search_datasets(
            page, loaded_view_plugins, dataset, search, no_default_filters
        )
        if query is None:
            return
        if page == 1 and query[u"count"] == 0:
            return error_shout(
                u"No datasets to create resource views on, exiting..."
            )

        elif page == 1 and not yes:

            msg = (
                u"\nYou are about to check {0} datasets for the "
                + u"following view plugins: {1}\n"
                + u" Do you want to continue?"
            )

            click.confirm(
                msg.format(query[u"count"], loaded_view_plugins), abort=True
            )

        if query[u"results"]:
            for dataset_dict in query[u"results"]:

                if not dataset_dict.get(u"resources"):
                    continue
                with flask_app.test_request_context():
                    views = add_views_to_dataset_resources(
                        context, dataset_dict, view_types=loaded_view_plugins
                    )

                if views:
                    view_types = list({view[u"view_type"] for view in views})
                    msg = (
                        u"Added {0} view(s) of type(s) {1} to "
                        + u"resources from dataset {2}"
                    )
                    click.secho(
                        msg.format(
                            len(views),
                            u", ".join(view_types),
                            dataset_dict[u"name"],
                        )
                    )

            if len(query[u"results"]) < _page_size:
                break

            page += 1
        else:
            break

    click.secho(u"Done", fg=u"green")


@views.command()
@click.argument(u"types", nargs=-1)
@click.option(u"-y", u"--yes", is_flag=True)
def clear(types, yes):
    """Permanently delete all views or the ones with the provided types.

    """

    if not yes:
        if types:
            msg = (
                u"Are you sure you want to delete all resource views "
                + u"of type {0}?".format(u", ".join(types))
            )
        else:
            msg = u"Are you sure you want to delete all resource views?"
        click.confirm(msg, abort=True)

    site_user = logic.get_action(u"get_site_user")({u"ignore_auth": True}, {})

    context = {u"user": site_user[u"name"]}
    logic.get_action(u"resource_view_clear")(context, {u"view_types": types})

    click.secho(u"Done", fg=u"green")


@views.command()
@click.option(u"-y", u"--yes", is_flag=True)
@click.pass_context
def clean(ctx, yes):
    """Permanently delete views for all types no longer present in the
    `ckan.plugins` configuration option.

    """
    names = []
    flask_app = ctx.meta['flask_app']
    with flask_app.test_request_context():
        for plugin in p.PluginImplementations(p.IResourceView):
            names.append(str(plugin.info()[u"name"]))

    results = model.ResourceView.get_count_not_in_view_types(names)

    if not results:
        return click.secho(u"No resource views to delete", fg=u"red")

    click.secho(u"This command will delete.\n")
    for row in results:
        click.secho(u"%s of type %s" % (row[1], row[0]))

    yes or click.confirm(
        u"Do you want to delete these resource views?", abort=True
    )

    model.ResourceView.delete_not_in_view_types(names)
    model.Session.commit()
    click.secho(u"Deleted resource views.", fg=u"green")


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
        click.secho(u"No view types provided, using default types")
        view_plugins = get_default_view_plugins()
        if get_datastore_views:
            view_plugins.extend(
                get_default_view_plugins(get_datastore_views=True)
            )
    else:
        view_plugins = get_view_plugins(view_plugin_types)

    loaded_view_plugins = [
        view_plugin.info()[u"name"] for view_plugin in view_plugins
    ]

    plugins_not_found = list(set(view_plugin_types) - set(loaded_view_plugins))

    if plugins_not_found:
        error_shout(
            u"View plugin(s) not found : {0}. ".format(plugins_not_found)
            + u"Have they been added to the `ckan.plugins` configuration"
            + u" option?"
        )
        return None
    return loaded_view_plugins


def _search_datasets(
    page=1, view_types=[], dataset=[], search=u"", no_default_filters=False
):
    """
    Perform a query with `package_search` and return the result

    Results can be paginated using the `page` parameter
    """

    n = _page_size

    search_data_dict = {
        u"q": u"",
        u"fq": u"",
        u"fq_list": [],
        u"include_private": True,
        u"rows": n,
        u"start": n * (page - 1),
    }

    if dataset:

        search_data_dict[u"q"] = u" OR ".join(
            [
                u'id:{0} OR name:"{0}"'.format(dataset_id)
                for dataset_id in dataset
            ]
        )

    elif search:

        search_data_dict = _update_search_params(search_data_dict, search)
        if search_data_dict is None:
            return None

    elif not no_default_filters:

        _add_default_filters(search_data_dict, view_types)

    if not search_data_dict.get(u"q"):
        search_data_dict[u"q"] = u"*:*"

    query = p.toolkit.get_action(u"package_search")({}, search_data_dict)

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
        if view_type == u"image_view":

            for _format in DEFAULT_IMAGE_FORMATS:
                filter_formats.extend([_format, _format.upper()])

        elif view_type == u"text_view":
            formats = get_text_formats(p.toolkit.config)
            for _format in itertools.chain.from_iterable(formats.values()):
                filter_formats.extend([_format, _format.upper()])

        elif view_type == u"pdf_view":
            filter_formats.extend([u"pdf", u"PDF"])

        elif view_type in [
            u"recline_view",
            u"recline_grid_view",
            u"recline_graph_view",
            u"recline_map_view",
        ]:

            if datapusher_formats[0] in filter_formats:
                continue

            for _format in datapusher_formats:
                if u"/" not in _format:
                    filter_formats.extend([_format, _format.upper()])
        else:
            # There is another view type provided so we can't add any
            # filter
            return search_data_dict

    filter_formats_query = [
        u'+res_format:"{0}"'.format(_format) for _format in filter_formats
    ]
    search_data_dict[u"fq_list"].append(u" OR ".join(filter_formats_query))

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
        error_shout(u"Unable to parse JSON search parameters: {0}".format(e))
        return None

    if user_search_params.get(u"q"):
        search_data_dict[u"q"] = user_search_params[u"q"]

    if user_search_params.get(u"fq"):
        if search_data_dict[u"fq"]:
            search_data_dict[u"fq"] += u" " + user_search_params[u"fq"]
        else:
            search_data_dict[u"fq"] = user_search_params[u"fq"]

    if user_search_params.get(u"fq_list") and isinstance(
        user_search_params[u"fq_list"], list
    ):
        search_data_dict[u"fq_list"].extend(user_search_params[u"fq_list"])
    return search_data_dict
