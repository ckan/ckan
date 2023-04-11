# encoding: utf-8

'''
These dictize functions generally take a domain object (such as Package) and
convert it to a dictionary, including related objects (e.g. for Package it
includes PackageTags, PackageExtras, PackageGroup etc).

The basic recipe is to call:

    dictized = ckan.lib.dictization.table_dictize(domain_object)

which builds the dictionary by iterating over the table columns.
'''
from __future__ import annotations

import copy
from typing import (
    Any, Callable, Iterable,
    Optional, Union, cast, overload
)
from typing_extensions import Literal

from urllib.parse import urlsplit
from sqlalchemy.sql.schema import Table
from sqlalchemy.sql.selectable import Select

from sqlalchemy.sql import select

import ckan.logic as logic
import ckan.plugins as plugins
import ckan.lib.helpers as h
import ckan.lib.dictization as d
import ckan.authz as authz
import ckan.lib.search as search
import ckan.lib.munge as munge
import ckan.model as model
from ckan.types import Context
from ckan.common import config

## package save

def group_list_dictize(
        obj_list: Union[Iterable[model.Group],
                        Iterable[tuple[model.Group, str]]],
        context: Context,
        sort_key: Callable[..., Any]=lambda x: h.strxfrm(x['display_name']), reverse: bool=False,
        with_package_counts: bool=True,
        include_groups: bool=False,
        include_tags: bool=False,
        include_extras: bool=False) -> list[dict[str, Any]]:

    group_dictize_context: Context = context.copy()
    # Set options to avoid any SOLR queries for each group, which would
    # slow things further.
    group_dictize_options: dict[str, Any] = {
            'packages_field': 'dataset_count' if with_package_counts else None,
            # don't allow packages_field='datasets' as it is too slow
            'include_groups': include_groups,
            'include_tags': include_tags,
            'include_extras': include_extras,
            'include_users': False,  # too slow - don't allow
            }
    if with_package_counts and 'dataset_counts' not in group_dictize_context:
        # 'dataset_counts' will already be in the context in the case that
        # group_list_dictize recurses via group_dictize (groups in groups)
        group_dictize_context['dataset_counts'] = get_group_dataset_counts()
    if context.get('with_capacity'):
        group_list = [
            group_dictize(
                group, group_dictize_context,
                capacity=capacity, **group_dictize_options)
            for group, capacity
            in cast("list[tuple[model.Group, str]]", obj_list)]
    else:
        group_list = [
            group_dictize(group, group_dictize_context,
                          **group_dictize_options)
            for group in cast("list[model.Group]", obj_list)]

    return sorted(group_list, key=sort_key, reverse=reverse)

def resource_list_dictize(
        res_list: list[model.Resource],
        context: Context) -> list[dict[str, Any]]:

    active = context.get('active', True)
    result_list = []
    for res in res_list:
        resource_dict = resource_dictize(res, context)
        if active and res.state != 'active':
            continue

        result_list.append(resource_dict)

    return sorted(result_list, key=lambda x: x["position"])

def extras_dict_dictize(
        extras_dict: dict[str, Any],
        context: Context) -> list[dict[str, Any]]:
    result_list = []
    for extra in extras_dict.values():
        dictized = d.table_dictize(extra, context)
        if not extra.state == 'active':
            continue
        result_list.append(dictized)

    return sorted(result_list, key=lambda x: x["key"])

def extras_list_dictize(
        extras_list: list[Any], context: Context) -> list[dict[str, Any]]:
    result_list = []
    active = context.get('active', True)
    for extra in extras_list:
        dictized = d.table_dictize(extra, context)
        if active and extra.state != 'active':
            continue
        result_list.append(dictized)

    return sorted(result_list, key=lambda x: x["key"])


def resource_dictize(res: model.Resource, context: Context) -> dict[str, Any]:
    resource = d.table_dictize(res, context)
    extras = resource.pop("extras", None)
    if extras:
        resource.update(extras)
    # some urls do not have the protocol this adds http:// to these
    url = resource['url']
    ## for_edit is only called at the times when the dataset is to be edited
    ## in the frontend. Without for_edit the whole qualified url is returned.
    if resource.get('url_type') == 'upload' and not context.get('for_edit'):
        url = url.rsplit('/')[-1]
        cleaned_name = munge.munge_filename(url)
        resource['url'] = h.url_for('resource.download',
                                    id=resource['package_id'],
                                    resource_id=res.id,
                                    filename=cleaned_name,
                                    qualified=True)
    elif resource['url'] and not urlsplit(url).scheme \
         and not context.get('for_edit'):
        resource['url'] = u'http://' + url.lstrip('/')
    return resource


def _execute(q: Select, table: Table, context: Context) -> Any:
    '''
    Takes an SqlAlchemy query (q) that is (at its base) a Select on an
    object table (table), and it returns the object.

    Analogous with _execute_with_revision, so takes the same params, even
    though it doesn't need the table.
    '''
    model = context['model']
    session = model.Session
    result: Any = session.execute(q)
    return result


def package_dictize(
    pkg: model.Package, context: Context, include_plugin_data: bool = False
    ) -> dict[str, Any]:
    '''
    Given a Package object, returns an equivalent dictionary.
    '''
    model = context['model']
    assert not (context.get('revision_id') or
                context.get('revision_date')), \
        'Revision functionality is moved to migrate_package_activity'
    execute = _execute
    # package
    if not pkg:
        raise logic.NotFound
    result_dict = d.table_dictize(pkg, context)
    # strip whitespace from title
    if result_dict.get('title'):
        result_dict['title'] = result_dict['title'].strip()
    # plugin_data
    plugin_data = result_dict.pop('plugin_data', None)
    if include_plugin_data:
        result_dict['plugin_data'] = copy.deepcopy(
            plugin_data) if plugin_data else plugin_data

    # resources
    res = model.resource_table
    q = select([res]).where(res.c["package_id"] == pkg.id)
    result = execute(q, res, context)
    result_dict["resources"] = resource_list_dictize(result, context)
    result_dict['num_resources'] = len(result_dict.get('resources', []))

    # tags
    tag = model.tag_table
    pkg_tag = model.package_tag_table
    q = select([tag, pkg_tag.c["state"]],
               from_obj=pkg_tag.join(tag, tag.c["id"] == pkg_tag.c["tag_id"])
               ).where(pkg_tag.c["package_id"] == pkg.id)
    result = execute(q, pkg_tag, context)
    result_dict["tags"] = d.obj_list_dictize(result, context,
                                             lambda x: x["name"])
    result_dict['num_tags'] = len(result_dict.get('tags', []))

    # Add display_names to tags. At first a tag's display_name is just the
    # same as its name, but the display_name might get changed later (e.g.
    # translated into another language by the multilingual extension).
    for tag_dict in result_dict['tags']:
        assert 'display_name' not in tag_dict
        tag_dict['display_name'] = tag_dict['name']

    # extras - no longer revisioned, so always provide latest
    extra = model.package_extra_table
    q = select([extra]).where(extra.c["package_id"] == pkg.id)
    result = execute(q, extra, context)
    result_dict["extras"] = extras_list_dictize(result, context)

    # groups
    member = model.member_table
    group = model.group_table
    q = select([group, member.c["capacity"]],
               from_obj=member.join(group, group.c["id"] == member.c["group_id"])
               ).where(member.c["table_id"] == pkg.id)\
                .where(member.c["state"] == 'active') \
                .where(group.c["is_organization"] == False)
    result = execute(q, member, context)
    context['with_capacity'] = False
    # no package counts as cannot fetch from search index at the same
    # time as indexing to it.
    # tags, extras and sub-groups are not included for speed
    result_dict["groups"] = group_list_dictize(result, context,
                                               with_package_counts=False)

    # owning organization
    group = model.group_table
    q = select([group]
               ).where(group.c["id"] == pkg.owner_org) \
                .where(group.c["state"] == 'active')
    result = execute(q, group, context)
    organizations = d.obj_list_dictize(result, context)
    if organizations:
        result_dict["organization"] = organizations[0]
    else:
        result_dict["organization"] = None

    # relations
    rel = model.package_relationship_table
    q = select([rel]).where(rel.c["subject_package_id"] == pkg.id)
    result = execute(q, rel, context)
    result_dict["relationships_as_subject"] = \
        d.obj_list_dictize(result, context)
    q = select([rel]).where(rel.c["object_package_id"] == pkg.id)
    result = execute(q, rel, context)
    result_dict["relationships_as_object"] = \
        d.obj_list_dictize(result, context)

    # Extra properties from the domain object

    # isopen
    result_dict['isopen'] = pkg.isopen if isinstance(pkg.isopen, bool) \
        else pkg.isopen()

    # type
    # if null assign the default value to make searching easier
    result_dict['type'] = pkg.type or u'dataset'

    # license
    if pkg.license and pkg.license.url:
        result_dict['license_url'] = pkg.license.url
        result_dict['license_title'] = pkg.license.title.split('::')[-1]
    elif pkg.license:
        result_dict['license_title'] = pkg.license.title
    else:
        result_dict['license_title'] = pkg.license_id

    # creation and modification date
    result_dict['metadata_modified'] = pkg.metadata_modified.isoformat()
    result_dict['metadata_created'] = pkg.metadata_created.isoformat() \
        if pkg.metadata_created else None

    return result_dict


@overload
def _get_members(context: Context, group: model.Group,
                 member_type: Literal['users'],
                 ) -> list[tuple[model.User, str]]:
    ...


@overload
def _get_members(context: Context, group: model.Group,
                 member_type: Literal['groups'],
                 ) -> list[tuple[model.Group, str]]:
    ...


@overload
def _get_members(context: Context, group: model.Group,
                 member_type: Literal['tags'],
                 ) -> list[tuple[model.Tag, str]]:
    ...


def _get_members(context: Context, group: model.Group,
                 member_type: str) -> list[tuple[Any, str]]:

    model = context['model']
    Entity = getattr(model, member_type[:-1].capitalize())
    q = model.Session.query(
        Entity, model.Member.capacity).\
        join(model.Member, model.Member.table_id == Entity.id).\
        filter(model.Member.group_id == group.id).\
        filter(model.Member.state == 'active').\
        filter(model.Member.table_name == member_type[:-1])
    if member_type == 'packages':
        q = q.filter(Entity.private==False)
    if 'limits' in context and member_type in context['limits']:
        limit: int = context['limits'][member_type]
        return q.limit(limit).all()
    return q.all()


def get_group_dataset_counts() -> dict[str, Any]:
    '''For all public groups, return their dataset counts, as a SOLR facet'''
    query = search.PackageSearchQuery()
    q: dict[str, Any] = {'q': '',
         'fl': 'groups', 'facet.field': ['groups', 'owner_org'],
         'facet.limit': -1, 'rows': 1}
    query.run(q)
    return query.facets


def group_dictize(group: model.Group, context: Context,
                  include_groups: bool=True,
                  include_tags: bool=True,
                  include_users: bool=True,
                  include_extras: bool=True,
                  packages_field: Optional[str]='datasets',
                  **kw: Any) -> dict[str, Any]:
    '''
    Turns a Group object and related into a dictionary. The related objects
    like tags are included unless you specify it in the params.

    :param packages_field: determines the format of the `packages` field - can
    be `datasets`, `dataset_count` or None.
    '''
    assert packages_field in ('datasets', 'dataset_count', None)

    result_dict = d.table_dictize(group, context)
    result_dict.update(kw)

    result_dict['display_name'] = group.title or group.name

    if include_extras:
        result_dict['extras'] = extras_dict_dictize(
            group._extras, context)

    context['with_capacity'] = True

    if packages_field:
        def get_packages_for_this_group(group_: model.Group,
                                        just_the_count: bool = False):
            # Ask SOLR for the list of packages for this org/group
            q: dict[str, Any] = {
                'facet': 'false',
                'rows': 0,
            }

            if group_.is_organization:
                q['fq'] = '+owner_org:"{0}"'.format(group_.id)
            else:
                q['fq'] = '+groups:"{0}"'.format(group_.name)

            if group_.is_organization:
                is_group_member = (context.get('user') and
                    authz.has_user_permission_for_group_or_org(
                        group_.id, context.get('user'), 'read'))
                if is_group_member:
                    q['include_private'] = True
                else:
                    if config.get('ckan.auth.allow_dataset_collaborators'):
                        q['include_private'] = True

            if not just_the_count:
                # package_search limits 'rows' anyway, so this is only if you
                # want even fewer
                try:
                    packages_limit = context['limits']['packages']
                except KeyError:
                    del q['rows']  # leave it to package_search to limit it
                else:
                    q['rows'] = packages_limit

            search_context = cast(
                Context, dict((k, v) for (k, v) in context.items()
                              if k != 'schema'))
            search_results = logic.get_action('package_search')(
                search_context, q)
            return search_results['count'], search_results['results']

        if packages_field == 'datasets':
            package_count, packages = get_packages_for_this_group(group)
            result_dict['packages'] = packages
        else:
            dataset_counts = context.get('dataset_counts', None)

            if dataset_counts is None:
                package_count, packages = get_packages_for_this_group(
                    group, just_the_count=True)
            else:
                # Use the pre-calculated package_counts passed in.
                facets = dataset_counts
                if group.is_organization:
                    package_count = facets['owner_org'].get(group.id, 0)
                else:
                    package_count = facets['groups'].get(group.name, 0)

        result_dict['package_count'] = package_count

    if include_tags:
        # group tags are not creatable via the API yet, but that was(/is) a
        # future intention (see kindly's commit 5c8df894 on 2011/12/23)
        result_dict['tags'] = tag_list_dictize(
            _get_members(context, group, 'tags'),
            context)

    if include_groups:
        # these sub-groups won't have tags or extras for speed
        result_dict['groups'] = group_list_dictize(
            _get_members(context, group, 'groups'),
            context, include_groups=True)

    if include_users:
        result_dict['users'] = user_list_dictize(
            _get_members(context, group, 'users'),
            context)

    context['with_capacity'] = False

    if context.get('for_view'):
        if result_dict['is_organization']:
            plugin = plugins.IOrganizationController
        else:
            plugin = plugins.IGroupController
        for item in plugins.PluginImplementations(plugin):
            result_dict = item.before_view(result_dict)

    image_url = result_dict.get('image_url')
    result_dict['image_display_url'] = image_url
    if image_url and not image_url.startswith('http'):
        #munge here should not have an effect only doing it incase
        #of potential vulnerability of dodgy api input
        image_url = munge.munge_filename_legacy(image_url)
        result_dict['image_display_url'] = h.url_for_static(
            'uploads/group/%s' % result_dict.get('image_url'),
            qualified=True
        )
    return result_dict

def tag_list_dictize(
        tag_list: Union[Iterable[model.Tag], Iterable[tuple[model.Tag, str]]],
        context: Context) -> list[dict[str, Any]]:

    result_list: list[dict[str, Any]] = []
    for tag in tag_list:
        if context.get('with_capacity'):
            assert not isinstance(tag, model.Tag)
            tag, capacity = tag
            dictized = d.table_dictize(tag, context, capacity=capacity)
        else:
            dictized = d.table_dictize(tag, context)

        # Add display_names to tag dicts. At first a tag's display_name is just
        # the same as its name, but the display_name might get changed later
        # (e.g.  translated into another language by the multilingual
        # extension).
        assert 'display_name' not in dictized
        dictized['display_name'] = dictized['name']

        if context.get('for_view'):
            for item in plugins.PluginImplementations(
                    plugins.ITagController):
                dictized = item.before_view(dictized)

        result_list.append(dictized)

    return result_list

def tag_dictize(tag: model.Tag, context: Context,
                include_datasets: bool=True) -> dict[str, Any]:
    tag_dict = d.table_dictize(tag, context)
    package_dicts = []
    if include_datasets:
        query = search.PackageSearchQuery()

        tag_query = u'+capacity:public '
        vocab_id = tag_dict.get('vocabulary_id')

        if vocab_id:
            model = context['model']
            vocab = model.Vocabulary.get(vocab_id)
            assert vocab
            tag_query += u'+vocab_{0}:"{1}"'.format(vocab.name, tag.name)
        else:
            tag_query += u'+tags:"{0}"'.format(tag.name)

        q: dict[str, Any] = {
            'q': tag_query, 'fl': 'data_dict', 'wt': 'json', 'rows': 1000}

        package_dicts = [h.json.loads(result['data_dict'])
                         for result in query.run(q)['results']]

    # Add display_names to tags. At first a tag's display_name is just the
    # same as its name, but the display_name might get changed later (e.g.
    # translated into another language by the multilingual extension).
    assert 'display_name' not in tag_dict
    tag_dict['display_name'] = tag_dict['name']

    if context.get('for_view'):
        for item in plugins.PluginImplementations(plugins.ITagController):
            tag_dict = item.before_view(tag_dict)

        if include_datasets:
            tag_dict['packages'] = []
            for package_dict in package_dicts:
                for item in plugins.PluginImplementations(plugins.IPackageController):
                    package_dict = item.before_dataset_view(package_dict)
                tag_dict['packages'].append(package_dict)
    else:
        if include_datasets:
            tag_dict['packages'] = package_dicts

    return tag_dict

def user_list_dictize(
        obj_list: Union[list[model.User], list[tuple[model.User, str]]],
        context: Context,
        sort_key: Callable[[Any], Any] = lambda x: h.strxfrm(x['name']),
        reverse: bool=False) -> list[dict[str, Any]]:

    result_list = []

    for obj in obj_list:
        user_dict = user_dictize(obj, context)
        user_dict.pop('reset_key', None)
        user_dict.pop('apikey', None)
        user_dict.pop('email', None)
        result_list.append(user_dict)
    return sorted(result_list, key=sort_key, reverse=reverse)

def member_dictize(member: Union[model.Member, model.PackageMember],
                   context: Context) -> dict[str, Any]:
    return d.table_dictize(member, context)

def user_dictize(
        user: Union[model.User, tuple[model.User, str]], context: Context,
        include_password_hash: bool=False,
        include_plugin_extras: bool=False) -> dict[str, Any]:
    model = context['model']

    if context.get('with_capacity'):
        # Fix type: "User" is not iterable
        user, capacity = user  #type: ignore
        result_dict = d.table_dictize(user, context, capacity=capacity)
    else:
        result_dict = d.table_dictize(user, context)

    assert isinstance(user, model.User)
    password_hash = result_dict.pop('password')
    del result_dict['reset_key']

    result_dict['display_name'] = user.display_name
    result_dict['email_hash'] = user.email_hash
    result_dict['number_created_packages'] = user.number_created_packages(
        include_private_and_draft=context.get(
            'count_private_and_draft_datasets', False))

    requester = context.get('user')

    result_dict.pop('reset_key', None)
    apikey = result_dict.pop('apikey', None)
    email = result_dict.pop('email', None)
    plugin_extras = result_dict.pop('plugin_extras', None)

    if context.get('keep_email', False):
        result_dict['email'] = email

    if context.get('keep_apikey', False):
        result_dict['apikey'] = apikey

    if requester == user.name:
        result_dict['apikey'] = apikey
        result_dict['email'] = email

    if authz.is_sysadmin(requester):
        result_dict['apikey'] = apikey
        result_dict['email'] = email

        if include_password_hash:
            result_dict['password_hash'] = password_hash

        if include_plugin_extras:
            result_dict['plugin_extras'] = copy.deepcopy(
                plugin_extras) if plugin_extras else plugin_extras


    image_url = result_dict.get('image_url')
    result_dict['image_display_url'] = image_url
    if image_url and not image_url.startswith('http'):
        # munge here should not have any effect, only doing it in case
        # of potential vulnerability of dodgy api input.
        image_url = munge.munge_filename_legacy(image_url)
        result_dict['image_display_url'] = h.url_for_static(
            'uploads/user/%s' % result_dict.get('image_url'),
            qualified=True
        )

    return result_dict

def task_status_dictize(
        task_status: model.TaskStatus, context: Context) -> dict[str, Any]:
    return d.table_dictize(task_status, context)


def vocabulary_dictize(vocabulary: model.Vocabulary, context: Context,
                       include_datasets: bool=False) -> dict[str, Any]:
    vocabulary_dict = d.table_dictize(vocabulary, context)
    assert 'tags' not in vocabulary_dict

    vocabulary_dict['tags'] = [tag_dictize(tag, context, include_datasets)
                               for tag in vocabulary.tags]
    return vocabulary_dict

def vocabulary_list_dictize(vocabulary_list: list[model.Vocabulary],
                            context: Context) -> list[dict[str, Any]]:
    return [vocabulary_dictize(vocabulary, context)
            for vocabulary in vocabulary_list]

def user_following_user_dictize(follower: model.UserFollowingUser,
                                context: Context) -> dict[str, Any]:
    return d.table_dictize(follower, context)

def user_following_dataset_dictize(follower: model.UserFollowingDataset,
                                   context: Context) -> dict[str, Any]:
    return d.table_dictize(follower, context)

def user_following_group_dictize(follower: model.UserFollowingGroup,
                                 context: Context) -> dict[str, Any]:
    return d.table_dictize(follower, context)

def resource_view_dictize(resource_view: model.ResourceView,
                          context: Context) -> dict[str, Any]:
    dictized = d.table_dictize(resource_view, context)
    dictized.pop('order')
    config = dictized.pop('config', {})
    dictized.update(config)
    resource = context['model'].Resource.get(resource_view.resource_id)
    assert resource
    package_id = resource.package_id
    dictized['package_id'] = package_id
    return dictized

def resource_view_list_dictize(resource_views: list[model.ResourceView],
                               context: Context) -> list[dict[str, Any]]:
    resource_view_dicts: list[dict[str, Any]] = []
    for view in resource_views:
        resource_view_dicts.append(resource_view_dictize(view, context))
    return resource_view_dicts


def api_token_dictize(api_token: model.ApiToken,
                      context: Context) -> dict[str, Any]:
    include_plugin_extras = context.get(u'include_plugin_extras', False)
    result_dict = d.table_dictize(api_token, context)
    plugin_extras = result_dict.pop(u'plugin_extras', None)
    if include_plugin_extras:
        result_dict[u'plugin_extras'] = copy.deepcopy(
            plugin_extras) if plugin_extras else plugin_extras
    return result_dict


def api_token_list_dictize(tokens: Iterable[model.ApiToken],
                           context: Context) -> list[dict[str, Any]]:
    token_dicts: list[dict[str, Any]] = []
    for token in tokens:
        token_dicts.append(api_token_dictize(token, context))
    return token_dicts
