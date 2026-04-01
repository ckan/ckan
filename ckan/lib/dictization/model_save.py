# encoding: utf-8
from __future__ import annotations

import copy
import datetime
import uuid
import logging
from typing import (
    Any, Collection, Optional, TYPE_CHECKING, Type, Union, cast, overload,
    Literal,
)

import ckan.lib.dictization as d
import ckan.authz as authz
from ckan import model
from ckan.types import Context

if TYPE_CHECKING:
    import ckan.model.follower as follower_


log = logging.getLogger(__name__)


def resource_dict_save(
        res_dict: dict[str, Any], context: Context) \
        -> tuple['model.Resource', Literal['create', 'update', None]]:
    '''
    Returns (resource_object, change) where change is:
    - 'create' if this is a new resource object
    - 'update' if any core fields or extras were changed
    - None if no change for an existing resource object
    '''
    session = context["session"]

    id = res_dict.get("id")
    obj = None
    if id:
        obj = session.get(model.Resource, id)
    if not obj:
        new = True
        obj = model.Resource()
    else:
        new = False

    # Strip the full url for resources of type 'upload'
    if res_dict.get('url') and res_dict.get('url_type') == u'upload':
        res_dict['url'] = res_dict['url'].rsplit('/')[-1]

    # unconditionally ignored fields
    res_dict.pop('extras', None)
    res_dict.pop('revision_timestamp', None)
    res_dict.pop('tracking_summary', None)

    changed, skipped = obj.from_dict(res_dict)

    if 'url' in changed or ('last_modified' in changed and not new):
        obj.url_changed = True

    any_change = changed or obj.extras != skipped
    if res_dict.get('metadata_modified'):
        obj.metadata_modified = res_dict['metadata_modified']
    elif any_change:
        obj.metadata_modified = datetime.datetime.utcnow()
        session.add(obj)
    obj.state = u'active'
    obj.extras = skipped

    return obj, 'create' if new else 'update' if any_change else None


def package_resource_list_save(
        res_dicts: Optional[list[dict[str, Any]]],
        package: 'model.Package', context: Context,
        copy_resources: dict[int, int] | tuple[()]) -> bool:
    """
    Store a list of resources in the database. Returns True if any resources
    were changed.

    :param res_dicts: List of resource dictionaries to store
    :type res_dict: list of dicts
    :param package: The package model object that resources belong to
    :param package: model.Package
    :param context: A context dict with extra information
    :type context: dict
    :param copy_resources: A dictionary with resource indexes that should be copied from the existing resource list rather than creating new models for them. It should have the format `{<new_index>: <old_index>,}`
    :type copy_resources: dict
    """
    if res_dicts is None:
        return False

    session = context['session']
    resource_list = package.resources_all
    # existing resources not marked as deleted - when removed these
    # need to be kept in the db marked as deleted so that extensions like
    # datastore have a chance to remove tables created for those resources
    old_list = session.query(model.Resource) \
        .filter(model.Resource.package_id == package.id) \
        .filter(model.Resource.state != 'deleted') \
        .order_by(model.Resource.position)[:]

    # resources previously deleted can be removed permanently as part
    # of this update
    deleted_list = session.query(model.Resource) \
        .filter(model.Resource.package_id == package.id) \
        .filter(model.Resource.state == 'deleted')[:]

    obj_list = []
    resources_changed = False
    for i, res_dict in enumerate(res_dicts or []):
        if i in copy_resources:
            obj_list.append(old_list[copy_resources[i]])
            if i != copy_resources[i]:
                resources_changed = True
            continue
        if not u'package_id' in res_dict or not res_dict[u'package_id']:
            res_dict[u'package_id'] = package.id
        obj, change = resource_dict_save(res_dict, context)
        obj_list.append(obj)
        if change:
            resources_changed = True

    if old_list == obj_list:
        return resources_changed

    # Set the package's resources. resource_list is an ORM relation - the
    # package's resources. If we didn't have the slice operator "[:]" then it
    # would reassign the variable "resource_list" to be the obj_list. But with
    # the slice operator it changes the contents of the relation, setting the
    # package's resources.
    # At the table level, for each resource in the obj_list, its
    # resource.package_id is changed to this package (which is needed for new
    # resources), and every resource.position is set to ascending integers,
    # according to their ordering in the obj_list.
    resource_list[:] = obj_list

    # Permanently remove old deleted resources
    for resource in set(deleted_list) - set(obj_list):
        resource.purge()
    # Mark any left-over resources as deleted
    for resource in set(old_list) - set(obj_list):
        resource.state = 'deleted'
        resource_list.append(resource)

    return True


def package_tag_list_save(tag_dicts: Optional[list[dict[str, Any]]],
                          package: 'model.Package', context: Context) -> bool:
    '''
    Returns True if any tags were changed
    '''
    changed = False
    session = context["session"]

    tag_package_tag = dict((package_tag.tag, package_tag)
                            for package_tag in
                            package.package_tags)

    tag_package_tag_inactive = {
        tag: pt for tag,pt in tag_package_tag.items()
        if pt.state in ['deleted']}

    tag_name_vocab: set[tuple[str, str]] = set()
    tags: set[model.Tag] = set()
    for tag_dict in tag_dicts or []:
        name_vocab = (tag_dict.get('name'), tag_dict.get('vocabulary_id'))
        if name_vocab not in tag_name_vocab:
            tag_obj, _change = d.table_dict_save(tag_dict, model.Tag, context)
            tags.add(tag_obj)
            tag_name_vocab.add((tag_obj.name, tag_obj.vocabulary_id))

    # 3 cases
    # case 1: currently active but not in new list
    for tag in set(tag_package_tag.keys()) - tags:
        package_tag = tag_package_tag[tag]
        package_tag.state = 'deleted'
        changed = True

    # case 2: in new list but never used before
    for tag in tags - set(tag_package_tag.keys()):
        state = 'active'
        package_tag_obj = model.PackageTag(package, tag, state)
        session.add(package_tag_obj)
        tag_package_tag[tag] = package_tag_obj
        changed = True

    # case 3: in new list and already used but in deleted state
    for tag in tags.intersection(set(tag_package_tag_inactive.keys())):
        state = 'active'
        package_tag = tag_package_tag[tag]
        package_tag.state = state
        changed = True

    if changed:
        package.package_tags[:] = tag_package_tag.values()
    return changed


def package_membership_list_save(
        group_dicts: Optional[list[dict[str, Any]]],
        package: 'model.Package', context: Context) -> bool:
    '''
    Returns True if any member was changed.
    '''
    changed = False

    if group_dicts is None:
        return changed

    capacity = 'public'
    session = context["session"]
    user = context.get('user', '')

    members = session.query(model.Member) \
            .filter(model.Member.table_id == package.id) \
            .filter(model.Member.capacity != 'organization')

    group_member = dict((member.group, member)
                         for member in
                         members)
    groups: set[model.Group] = set()
    for group_dict in group_dicts or []:
        id = group_dict.get("id")
        name = group_dict.get("name")
        capacity = group_dict.get("capacity", "public")
        if capacity == 'organization':
            continue
        if id:
            group = session.get(model.Group, id)
        else:
            group = session.query(model.Group).filter_by(name=name).first()
        if group:
            groups.add(group)

    ## need to flush so we can get out the package id
    model.Session.flush()

    # Remove any groups we are no longer in
    for group in set(group_member.keys()) - groups:
        member_obj = group_member[group]
        if member_obj and member_obj.state == 'deleted':
            continue
        if (context.get('ignore_auth') or
            authz.has_user_permission_for_group_or_org(
                member_obj.group_id, user, 'read')):
            member_obj.capacity = capacity
            member_obj.state = 'deleted'
            session.add(member_obj)
            changed = True

    # Add any new groups
    for group in groups:
        member_obj = group_member.get(group)
        if member_obj and member_obj.state == 'active':
            continue
        if (context.get('ignore_auth') or
            authz.has_user_permission_for_group_or_org(
                group.id, user, 'read')):
            member_obj = group_member.get(group)
            if member_obj:
                member_obj.capacity = capacity
                member_obj.state = 'active'
            else:
                member_obj = model.Member(table_id=package.id,
                                          table_name='package',
                                          group=group,
                                          capacity=capacity,
                                          group_id=group.id,
                                          state = 'active')
            session.add(member_obj)
            changed = True

    return changed


def relationship_list_save(
        relationship_dicts: Optional[list[dict[str, Any]]],
        package: 'model.Package', attr: str, context: Context) -> None:

    if relationship_dicts is None:
        return

    relationship_list = getattr(package, attr)
    old_list = relationship_list[:]

    relationships = []
    for relationship_dict in relationship_dicts or []:
        obj, _change = d.table_dict_save(
            relationship_dict, model.PackageRelationship, context)
        relationships.append(obj)

    relationship_list[:] = relationships

    for relationship in set(old_list) - set(relationship_list):
        relationship.state = 'deleted'
        relationship_list.append(relationship)

def package_dict_save(
        pkg_dict: dict[str, Any], context: Context,
        include_plugin_data: bool = False,
        copy_resources: dict[int, int] | tuple[()] = ()) \
        -> tuple['model.Package', Literal['create', 'update', None]]:
    '''
    Returns (package_object, change) where change is:
    - 'create' if this is a new package object
    - 'update' if any fields or resources were changed
    - None if no change for an existing package object
    '''

    Package = model.Package

    plugin_data = pkg_dict.pop('plugin_data', None)
    if include_plugin_data:
        pkg_dict['plugin_data'] = copy.deepcopy(
            plugin_data) if plugin_data else plugin_data

    extras = {
        e['key']: e['value'] for e in pkg_dict.get('extras', [])
    }

    pkg, pkg_change = d.table_dict_save(
        dict(pkg_dict, extras=extras), Package, context)

    if not pkg.id:
        pkg.id = str(uuid.uuid4())

    res_change = package_resource_list_save(
        pkg_dict.get("resources"), pkg, context, copy_resources)
    tag_change = package_tag_list_save(pkg_dict.get("tags"), pkg, context)
    group_change = package_membership_list_save(
        pkg_dict.get("groups"), pkg, context)

    # relationships are not considered 'part' of the package, so only
    # process this if the key is provided
    if 'relationships_as_subject' in pkg_dict:
        subjects = pkg_dict.get('relationships_as_subject')
        relationship_list_save(subjects, pkg, 'relationships_as_subject', context)
    if 'relationships_as_object' in pkg_dict:
        objects = pkg_dict.get('relationships_as_object')
        relationship_list_save(objects, pkg, 'relationships_as_object', context)

    return (
        pkg,
        'create' if pkg_change == 'create'
        else 'update' if pkg_change or res_change or tag_change or group_change
        else None
    )

def group_member_save(context: Context, group_dict: dict[str, Any],
                      member_table_name: str) -> dict[str, Any]:
    session = context["session"]
    group = context['group']
    assert group is not None
    entity_list: list[dict[str, Any]] | None = group_dict.get(
        member_table_name, None
    )

    if entity_list is None:
        return {'added': [], 'removed': []}

    entities: dict[tuple[str, str], Any] = {}
    Member = model.Member

    classname = member_table_name[:-1].capitalize()
    if classname == 'Organization':
        # Organizations use the model.Group class
        classname = 'Group'
    ModelClass = getattr(model, classname)

    for entity_dict in entity_list:
        name_or_id = entity_dict.get('id') or entity_dict.get('name')
        obj = ModelClass.get(name_or_id)
        if obj and obj not in entities.values():
            entities[(obj.id, entity_dict.get('capacity', 'public'))] = obj

    members = session.query(Member).filter_by(
        table_name=member_table_name[:-1],
        group_id=group.id,
    ).all()

    processed: dict['str', list[Any]] = {
        'added': [],
        'removed': []
    }

    entity_member: dict[tuple[str, str], Any] = dict(
        (
            (cast(str, member.table_id), member.capacity),
            member
        )
        for member in members
    )
    for entity_id in set(entity_member.keys()) - set(entities.keys()):
        if entity_member[entity_id].state != 'deleted':
            processed['removed'].append(entity_id[0])
        entity_member[entity_id].state = 'deleted'
        session.add(entity_member[entity_id])

    for entity_id in set(entity_member.keys()) & set(entities.keys()):
        if entity_member[entity_id].state != 'active':
            processed['added'].append(entity_id[0])
        entity_member[entity_id].state = 'active'
        session.add(entity_member[entity_id])

    for entity_id in set(entities.keys()) - set(entity_member.keys()):
        member = Member(group=group, group_id=group.id, table_id=entity_id[0],
                        table_name=member_table_name[:-1],
                        capacity=entity_id[1])
        processed['added'].append(entity_id[0])
        session.add(member)

    return processed


def group_dict_save(group_dict: dict[str, Any], context: Context,
                    prevent_packages_update: bool=False) -> 'model.Group':
    from ckan.lib.search import rebuild

    session = context["session"]
    group = context.get("group")

    Group = model.Group
    if group:
        group_dict["id"] = group.id

    extras = {
        e['key']: e['value'] for e in group_dict.get('extras', [])
    }

    group, _change = d.table_dict_save(dict(group_dict, extras=extras), Group, context)
    if not group.id:
        group.id = str(uuid.uuid4())

    context['group'] = group

    # Under the new org rules we do not want to be able to update datasets
    # via group edit so we need a way to prevent this.  It may be more
    # sensible in future to send a list of allowed/disallowed updates for
    # groups, users, tabs etc.
    if not prevent_packages_update:
        pkgs_edited = group_member_save(context, group_dict, 'packages')
    else:
        pkgs_edited: dict[str, list[Any]] = {
            'added': [],
            'removed': []
        }
    group_users_changed = group_member_save(context, group_dict, 'users')
    group_groups_changed = group_member_save(context, group_dict, 'groups')
    log.debug('Group save membership changes - Packages: %r  Users: %r  '
            'Groups: %r', pkgs_edited, group_users_changed,
            group_groups_changed)

    # We will get a list of packages that we have either added or
    # removed from the group, and trigger a re-index.
    package_ids = pkgs_edited['removed']
    package_ids.extend( pkgs_edited['added'] )
    if package_ids:
        session.commit()
        [rebuild(package_id) for package_id in package_ids]

    return group


def user_dict_save(
        user_dict: dict[str, Any], context: Context) -> 'model.User':
    user = context.get('user_obj')

    User = model.User
    if user:
        user_dict['id'] = user.id

    if 'password' in user_dict and not len(user_dict['password']):
        del user_dict['password']

    user, _change = d.table_dict_save(
        user_dict,
        User,
        context,
        extra_attrs=['_password'],  # for setting password_hash directly
    )

    return user


def package_api_to_dict(
        api1_dict: dict[str, Union[str, Collection[str]]],
        context: Context) -> dict[str, Any]:

    package = context.get("package")
    api_version = context.get('api_version')
    assert api_version, 'No api_version supplied in context'

    dictized: dict[str, Any] = {}

    for key, value in api1_dict.items():
        new_value = value
        if key == 'tags':
            if isinstance(value, str):
                new_value = [{"name": item} for item in value.split()]
            else:
                new_value = [{"name": item} for item in value]
        if key == 'extras':
            updated_extras: dict[str, Any] = {}
            if package:
                updated_extras.update(package.extras)
            assert isinstance(value, dict)
            updated_extras.update(value)

            new_value = []

            for extras_key, extras_value in updated_extras.items():
                new_value.append({"key": extras_key,
                                  "value": extras_value})

        if key == 'groups' and len(value):
            if api_version == 1:
                new_value = [{'name': item} for item in value]
            else:
                new_value = [{'id': item} for item in value]

        dictized[key] = new_value

    download_url = dictized.pop('download_url', None)
    if download_url and not dictized.get('resources'):
        dictized["resources"] = [{'url': download_url}]

    download_url = dictized.pop('download_url', None)

    return dictized

def group_api_to_dict(api1_dict: dict[str, Any],
                      context: Context) -> dict[str, Any]:

    dictized: dict[str, Any] = {}

    for key, value in api1_dict.items():
        new_value = value
        if key == 'packages':
            new_value = [{"id": item} for item in value]
        if key == 'extras':
            new_value = [{"key": extra_key, "value": value[extra_key]}
                         for extra_key in value]
        dictized[key] = new_value

    return dictized

def task_status_dict_save(task_status_dict: dict[str, Any],
                          context: Context) -> 'model.TaskStatus':
    task_status = context.get("task_status")
    if task_status:
        task_status_dict["id"] = task_status.id

    task_status, _change = d.table_dict_save(
        task_status_dict, model.TaskStatus, context)
    return task_status


def vocabulary_tag_list_save(
        new_tag_dicts: list[dict[str, Any]],
        vocabulary_obj: 'model.Vocabulary', context: Context) -> None:
    session = context['session']

    # First delete any tags not in new_tag_dicts.
    for tag in vocabulary_obj.tags:
        if tag.name not in [t['name'] for t in new_tag_dicts]:
            tag.delete()
    # Now add any new tags.
    for tag_dict in new_tag_dicts:
        current_tag_names = [tag.name for tag in vocabulary_obj.tags]
        if tag_dict['name'] not in current_tag_names:
            # Make sure the tag belongs to this vocab..
            tag_dict['vocabulary_id'] = vocabulary_obj.id
            # then add it.
            tag_dict_save(tag_dict, {'session': session})

def vocabulary_dict_save(vocabulary_dict: dict[str, Any],
                         context: Context) -> 'model.Vocabulary':
    session = context['session']
    vocabulary_name = vocabulary_dict['name']

    vocabulary_obj = model.Vocabulary(vocabulary_name)
    session.add(vocabulary_obj)

    if 'tags' in vocabulary_dict:
        vocabulary_tag_list_save(vocabulary_dict['tags'], vocabulary_obj,
            context)

    return vocabulary_obj

def vocabulary_dict_update(vocabulary_dict: dict[str, Any],
                           context: Context) -> 'model.Vocabulary':
    vocabulary_obj = model.Vocabulary.get(vocabulary_dict['id'])
    assert vocabulary_obj
    if 'name' in vocabulary_dict:
        vocabulary_obj.name = vocabulary_dict['name']

    if 'tags' in vocabulary_dict:
        vocabulary_tag_list_save(vocabulary_dict['tags'], vocabulary_obj,
            context)

    return vocabulary_obj

def tag_dict_save(tag_dict: dict[str, Any], context: Context) -> 'model.Tag':
    tag = context.get('tag')
    if tag:
        tag_dict['id'] = tag.id
    tag, _change = d.table_dict_save(tag_dict, model.Tag, context)
    return tag

@overload
def follower_dict_save(
    data_dict: dict[str, Any], context: Context,
    FollowerClass: Type['follower_.UserFollowingUser']
) -> 'follower_.UserFollowingUser':
    ...


@overload
def follower_dict_save(
    data_dict: dict[str, Any], context: Context,
    FollowerClass: Type['follower_.UserFollowingGroup']
) -> 'follower_.UserFollowingGroup':
    ...


@overload
def follower_dict_save(
    data_dict: dict[str, Any], context: Context,
    FollowerClass: Type['follower_.UserFollowingDataset']
) -> 'follower_.UserFollowingDataset':
    ...


def follower_dict_save(
    data_dict: dict[str, Any], context: Context,
    FollowerClass: Type['follower_.ModelFollowingModel[Any, Any]']
) -> 'follower_.ModelFollowingModel[Any, Any]':
    session = context['session']
    user = model.User.get(context['user'])
    assert user
    follower_obj = FollowerClass(
        follower_id=user.id,
        object_id=data_dict['id'])
    session.add(follower_obj)
    return follower_obj


def resource_view_dict_save(data_dict: dict[str, Any],
                            context: Context) -> 'model.ResourceView':
    resource_view = context.get('resource_view')
    if resource_view:
        data_dict['id'] = resource_view.id
    config = {}
    for key, value in data_dict.items():
        if key not in model.ResourceView.get_columns():
            config[key]  = value
    data_dict['config'] = config

    resview, _change = d.table_dict_save(data_dict, model.ResourceView, context)
    return resview


def api_token_save(data_dict: dict[str, Any],
                   context: Context) -> 'model.ApiToken':
    user = model.User.get(data_dict['user'])
    assert user
    token, _change = d.table_dict_save(
        {
            u"user_id": user.id,
            u"name": data_dict[u"name"]
        },
        model.ApiToken, context
    )
    return token
