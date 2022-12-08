# encoding: utf-8
from __future__ import annotations

import copy
import datetime
import uuid
import logging
from typing import (
    Any, Collection, Optional, TYPE_CHECKING, Type, Union, cast, overload
)

import ckan.lib.dictization as d
import ckan.authz as authz
from ckan.types import Context

if TYPE_CHECKING:
    import ckan.model as model
    import ckan.model.follower as follower_


log = logging.getLogger(__name__)


def resource_dict_save(res_dict: dict[str, Any],
                       context: Context) -> 'model.Resource':
    model = context["model"]
    session = context["session"]

    id = res_dict.get("id")
    obj = None
    if id:
        obj = session.query(model.Resource).get(id)
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

    if changed or obj.extras != skipped:
        obj.metadata_modified = datetime.datetime.utcnow()
    obj.state = u'active'
    obj.extras = skipped

    session.add(obj)
    return obj


def package_resource_list_save(
        res_dicts: Optional[list[dict[str, Any]]],
        package: 'model.Package', context: Context) -> None:
    allow_partial_update = context.get("allow_partial_update", False)
    if res_dicts is None and allow_partial_update:
        return

    session = context['session']
    model = context['model']
    resource_list = package.resources_all
    # existing resources not marked as deleted - when removed these
    # need to be kept in the db marked as deleted so that extensions like
    # datastore have a chance to remove tables created for those resources
    old_list = session.query(model.Resource) \
        .filter(model.Resource.package_id == package.id) \
        .filter(model.Resource.state != 'deleted')[:]
    # resources previously deleted can be removed permanently as part
    # of this update
    deleted_list = session.query(model.Resource) \
        .filter(model.Resource.package_id == package.id) \
        .filter(model.Resource.state == 'deleted')[:]

    obj_list = []
    for res_dict in res_dicts or []:
        if not u'package_id' in res_dict or not res_dict[u'package_id']:
            res_dict[u'package_id'] = package.id
        obj = resource_dict_save(res_dict, context)
        obj_list.append(obj)

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


def package_extras_save(
        extra_dicts: Optional[list[dict[str, Any]]], pkg: 'model.Package',
        context: Context) -> None:
    allow_partial_update = context.get("allow_partial_update", False)
    if extra_dicts is None and allow_partial_update:
        return

    session = context["session"]

    old_extras = pkg._extras

    new_extras: dict[str, Any] = {}
    for extra_dict in extra_dicts or []:
        if extra_dict.get("deleted"):
            continue

        if extra_dict['value'] is None:
            pass
        else:
            new_extras[extra_dict["key"]] = extra_dict["value"]

    #new
    for key in set(new_extras.keys()) - set(old_extras.keys()):
        pkg.extras[key] = new_extras[key]
    #changed
    for key in set(new_extras.keys()) & set(old_extras.keys()):
        extra = old_extras[key]
        if new_extras[key] == extra.value:
            continue
        extra.value = new_extras[key]
        session.add(extra)
    #deleted
    for key in set(old_extras.keys()) - set(new_extras.keys()):
        extra = old_extras[key]
        session.delete(extra)


def package_tag_list_save(tag_dicts: Optional[list[dict[str, Any]]],
                          package: 'model.Package', context: Context) -> None:
    allow_partial_update = context.get("allow_partial_update", False)
    if tag_dicts is None and allow_partial_update:
        return

    model = context["model"]
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
            tag_obj = d.table_dict_save(tag_dict, model.Tag, context)
            tags.add(tag_obj)
            tag_name_vocab.add((tag_obj.name, tag_obj.vocabulary_id))

    # 3 cases
    # case 1: currently active but not in new list
    for tag in set(tag_package_tag.keys()) - tags:
        package_tag = tag_package_tag[tag]
        package_tag.state = 'deleted'

    # case 2: in new list but never used before
    for tag in tags - set(tag_package_tag.keys()):
        state = 'active'
        package_tag_obj = model.PackageTag(package, tag, state)
        session.add(package_tag_obj)
        tag_package_tag[tag] = package_tag_obj

    # case 3: in new list and already used but in deleted state
    for tag in tags.intersection(set(tag_package_tag_inactive.keys())):
        state = 'active'
        package_tag = tag_package_tag[tag]
        package_tag.state = state

    package.package_tags[:] = tag_package_tag.values()

def package_membership_list_save(
        group_dicts: Optional[list[dict[str, Any]]],
        package: 'model.Package', context: Context) -> None:

    allow_partial_update = context.get("allow_partial_update", False)
    if group_dicts is None and allow_partial_update:
        return

    capacity = 'public'
    model = context["model"]
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
            group = session.query(model.Group).get(id)
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
        if authz.has_user_permission_for_group_or_org(
                member_obj.group_id, user, 'read'):
            member_obj.capacity = capacity
            member_obj.state = 'deleted'
            session.add(member_obj)

    # Add any new groups
    for group in groups:
        member_obj = group_member.get(group)
        if member_obj and member_obj.state == 'active':
            continue
        if authz.has_user_permission_for_group_or_org(
                group.id, user, 'read'):
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


def relationship_list_save(
        relationship_dicts: Optional[list[dict[str, Any]]],
        package: 'model.Package', attr: str, context: Context) -> None:

    allow_partial_update = context.get("allow_partial_update", False)
    if relationship_dicts is None and allow_partial_update:
        return

    model = context["model"]

    relationship_list = getattr(package, attr)
    old_list = relationship_list[:]

    relationships = []
    for relationship_dict in relationship_dicts or []:
        obj = d.table_dict_save(relationship_dict,
                              model.PackageRelationship, context)
        relationships.append(obj)

    relationship_list[:] = relationships

    for relationship in set(old_list) - set(relationship_list):
        relationship.state = 'deleted'
        relationship_list.append(relationship)

def package_dict_save(
        pkg_dict: dict[str, Any], context: Context, 
        include_plugin_data: bool = False) -> 'model.Package':
    model = context["model"]
    package = context.get("package")
    if package:
        pkg_dict["id"] = package.id
    Package = model.Package

    if 'metadata_created' in pkg_dict:
        del pkg_dict['metadata_created']
    if 'metadata_modified' in pkg_dict:
        del pkg_dict['metadata_modified']

    plugin_data = pkg_dict.pop('plugin_data', None)    
    if include_plugin_data:
        pkg_dict['plugin_data'] = copy.deepcopy(
            plugin_data) if plugin_data else plugin_data

    pkg = d.table_dict_save(pkg_dict, Package, context)

    if not pkg.id:
        pkg.id = str(uuid.uuid4())

    package_resource_list_save(pkg_dict.get("resources"), pkg, context)
    package_tag_list_save(pkg_dict.get("tags"), pkg, context)
    package_membership_list_save(pkg_dict.get("groups"), pkg, context)

    # relationships are not considered 'part' of the package, so only
    # process this if the key is provided
    if 'relationships_as_subject' in pkg_dict:
        subjects = pkg_dict.get('relationships_as_subject')
        relationship_list_save(subjects, pkg, 'relationships_as_subject', context)
    if 'relationships_as_object' in pkg_dict:
        objects = pkg_dict.get('relationships_as_object')
        relationship_list_save(objects, pkg, 'relationships_as_object', context)

    package_extras_save(pkg_dict.get("extras"), pkg, context)

    return pkg

def group_member_save(context: Context, group_dict: dict[str, Any],
                      member_table_name: str) -> dict[str, Any]:
    model = context["model"]
    session = context["session"]
    group = context['group']
    assert group is not None
    entity_list: list[dict[str, Any]] = group_dict.get(member_table_name, None)

    if entity_list is None:
        if context.get('allow_partial_update', False):
            return {'added': [], 'removed': []}
        else:
            entity_list = []

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

    model = context["model"]
    session = context["session"]
    group = context.get("group")

    Group = model.Group
    if group:
        group_dict["id"] = group.id

    group = d.table_dict_save(group_dict, Group, context)
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
    group_tags_changed = group_member_save(context, group_dict, 'tags')
    log.debug('Group save membership changes - Packages: %r  Users: %r  '
            'Groups: %r  Tags: %r', pkgs_edited, group_users_changed,
            group_groups_changed, group_tags_changed)

    extras = group_dict.get("extras", [])
    new_extras = {i['key'] for i in extras}
    if extras:
        old_extras = group.extras
        for key in set(old_extras) - new_extras:
            del group.extras[key]
        for x in extras:
            if 'deleted' in x and x['key'] in old_extras:
                del group.extras[x['key']]
                continue
            group.extras[x['key']] = x['value']

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

    model = context['model']
    user = context.get('user_obj')

    User = model.User
    if user:
        user_dict['id'] = user.id

    if 'password' in user_dict and not len(user_dict['password']):
        del user_dict['password']

    user = d.table_dict_save(
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
    model = context["model"]
    task_status = context.get("task_status")
    if task_status:
        task_status_dict["id"] = task_status.id

    task_status = d.table_dict_save(
        task_status_dict, model.TaskStatus, context)
    return task_status


def vocabulary_tag_list_save(
        new_tag_dicts: list[dict[str, Any]],
        vocabulary_obj: 'model.Vocabulary', context: Context) -> None:
    model = context['model']
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
            tag_dict_save(tag_dict, {'model': model, 'session': session})

def vocabulary_dict_save(vocabulary_dict: dict[str, Any],
                         context: Context) -> 'model.Vocabulary':
    model = context['model']
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

    model = context['model']

    vocabulary_obj = model.Vocabulary.get(vocabulary_dict['id'])
    assert vocabulary_obj
    if 'name' in vocabulary_dict:
        vocabulary_obj.name = vocabulary_dict['name']

    if 'tags' in vocabulary_dict:
        vocabulary_tag_list_save(vocabulary_dict['tags'], vocabulary_obj,
            context)

    return vocabulary_obj

def tag_dict_save(tag_dict: dict[str, Any], context: Context) -> 'model.Tag':
    model = context['model']
    tag = context.get('tag')
    if tag:
        tag_dict['id'] = tag.id
    tag = d.table_dict_save(tag_dict, model.Tag, context)
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
    model = context['model']
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
    model = context['model']
    resource_view = context.get('resource_view')
    if resource_view:
        data_dict['id'] = resource_view.id
    config = {}
    for key, value in data_dict.items():
        if key not in model.ResourceView.get_columns():
            config[key]  = value
    data_dict['config'] = config


    return d.table_dict_save(data_dict, model.ResourceView, context)


def api_token_save(data_dict: dict[str, Any],
                   context: Context) -> 'model.ApiToken':
    model = context[u"model"]
    user = model.User.get(data_dict['user'])
    assert user
    return d.table_dict_save(
        {
            u"user_id": user.id,
            u"name": data_dict[u"name"]
        },
        model.ApiToken, context
    )
