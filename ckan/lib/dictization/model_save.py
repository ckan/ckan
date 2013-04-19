import datetime
import uuid
import logging

from sqlalchemy.orm import class_mapper

import ckan.lib.dictization as d
import ckan.lib.helpers as h
import ckan.new_authz as new_authz

log = logging.getLogger(__name__)

def resource_dict_save(res_dict, context):
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

    table = class_mapper(model.Resource).mapped_table
    fields = [field.name for field in table.c]

    for key, value in res_dict.iteritems():
        if isinstance(value, list):
            continue
        if key in ('extras', 'revision_timestamp', 'tracking_summary'):
            continue
        if key in fields:
            if isinstance(getattr(obj, key), datetime.datetime):
                if getattr(obj, key).isoformat() == value:
                    continue
            if key == 'url' and not new and obj.url <> value:
                obj.url_changed = True
            # this is an internal field so ignore
            # FIXME This helps get the tests to pass but is a hack and should
            # be fixed properly. basically don't update the format if not needed
            if (key == 'format' and value == obj.format
                    or value == d.model_dictize._unified_resource_format(obj.format)):
                continue
            setattr(obj, key, value)
        else:
            # resources save extras directly onto the object, instead
            # of in a separate extras field like packages and groups
            obj.extras[key] = value

    # Resource extras not submitted should be removed from the extras dict
    extras_to_delete = set(obj.extras.keys()) - set(res_dict.keys())
    for delete_me in extras_to_delete:
        del obj.extras[delete_me]

    if context.get('pending'):
        if session.is_modified(obj, include_collections=False, passive=True):
            obj.state = u'pending'
    else:
        obj.state = u'active'

    session.add(obj)
    return obj

def package_resource_list_save(res_dicts, package, context):
    allow_partial_update = context.get("allow_partial_update", False)
    if res_dicts is None and allow_partial_update:
        return

    pending = context.get('pending')

    resource_list = package.resource_groups_all[0].resources_all
    old_list = package.resource_groups_all[0].resources_all[:]

    obj_list = []
    for res_dict in res_dicts or []:
        obj = resource_dict_save(res_dict, context)
        obj_list.append(obj)

    resource_list[:] = obj_list

    for resource in set(old_list) - set(obj_list):
        if pending and resource.state != 'deleted':
            resource.state = 'pending-deleted'
        else:
            resource.state = 'deleted'
        resource_list.append(resource)
    tag_package_tag = dict((package_tag.tag, package_tag)
                            for package_tag in
                            package.package_tag_all)


def package_extras_save(extra_dicts, obj, context):
    allow_partial_update = context.get("allow_partial_update", False)
    if extra_dicts is None and allow_partial_update:
        return

    model = context["model"]
    session = context["session"]

    extras_list = obj.extras_list
    old_extras = dict((extra.key, extra) for extra in extras_list)

    new_extras = {}
    for extra_dict in extra_dicts or []:
        if extra_dict.get("deleted"):
            continue

        if extra_dict['value'] is None:
            pass
        else:
            new_extras[extra_dict["key"]] = extra_dict["value"]
    #new
    for key in set(new_extras.keys()) - set(old_extras.keys()):
        state = 'pending' if context.get('pending') else 'active'
        extra = model.PackageExtra(state=state, key=key, value=new_extras[key])
        session.add(extra)
        extras_list.append(extra)
    #changed
    for key in set(new_extras.keys()) & set(old_extras.keys()):
        extra = old_extras[key]
        #dont change state to pending if nothing has changed
        if new_extras[key] == extra.value and extra.state != 'deleted':
            continue
        state = 'pending' if context.get('pending') else 'active'
        extra.value = new_extras[key]
        extra.state = state
        session.add(extra)
    #deleted
    for key in set(old_extras.keys()) - set(new_extras.keys()):
        extra = old_extras[key]
        if extra.state == 'deleted':
            continue
        state = 'pending-deleted' if context.get('pending') else 'deleted'
        extra.state = state

def group_extras_save(extras_dicts, context):

    model = context["model"]
    session = context["session"]

    result_dict = {}
    for extra_dict in extras_dicts:
        if extra_dict.get("deleted"):
            continue
        result_dict[extra_dict["key"]] = extra_dict["value"]

    return result_dict

def package_tag_list_save(tag_dicts, package, context):
    allow_partial_update = context.get("allow_partial_update", False)
    if tag_dicts is None and allow_partial_update:
        return

    model = context["model"]
    session = context["session"]
    pending = context.get('pending')

    tag_package_tag = dict((package_tag.tag, package_tag)
                            for package_tag in
                            package.package_tag_all)

    tag_package_tag_inactive = dict(
        [ (tag,pt) for tag,pt in tag_package_tag.items() if
            pt.state in ['deleted', 'pending-deleted'] ]
        )

    tag_name_vocab = set()
    tags = set()
    for tag_dict in tag_dicts or []:
        if (tag_dict.get('name'), tag_dict.get('vocabulary_id')) not in tag_name_vocab:
            tag_obj = d.table_dict_save(tag_dict, model.Tag, context)
            tags.add(tag_obj)
            tag_name_vocab.add((tag_obj.name, tag_obj.vocabulary_id))

    # 3 cases
    # case 1: currently active but not in new list
    for tag in set(tag_package_tag.keys()) - tags:
        package_tag = tag_package_tag[tag]
        if pending and package_tag.state != 'deleted':
            package_tag.state = 'pending-deleted'
        else:
            package_tag.state = 'deleted'

    # case 2: in new list but never used before
    for tag in tags - set(tag_package_tag.keys()):
        state = 'pending' if pending else 'active'
        package_tag_obj = model.PackageTag(package, tag, state)
        session.add(package_tag_obj)
        tag_package_tag[tag] = package_tag_obj

    # case 3: in new list and already used but in deleted state
    for tag in tags.intersection(set(tag_package_tag_inactive.keys())):
        state = 'pending' if pending else 'active'
        package_tag = tag_package_tag[tag]
        package_tag.state = state

    package.package_tag_all[:] = tag_package_tag.values()

def package_membership_list_save(group_dicts, package, context):

    allow_partial_update = context.get("allow_partial_update", False)
    if group_dicts is None and allow_partial_update:
        return

    capacity = 'public'
    model = context["model"]
    session = context["session"]
    pending = context.get('pending')
    user = context.get('user')

    members = session.query(model.Member) \
            .filter(model.Member.table_id == package.id) \
            .filter(model.Member.capacity != 'organization')

    group_member = dict((member.group, member)
                         for member in
                         members)
    groups = set()
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
        if new_authz.has_user_permission_for_group_or_org(
                member_obj.group_id, user, 'read'):
            member_obj.capacity = capacity
            member_obj.state = 'deleted'
            session.add(member_obj)

    # Add any new groups
    for group in groups:
        member_obj = group_member.get(group)
        if member_obj and member_obj.state == 'active':
            continue
        if new_authz.has_user_permission_for_group_or_org(
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


def relationship_list_save(relationship_dicts, package, attr, context):

    allow_partial_update = context.get("allow_partial_update", False)
    if relationship_dicts is None and allow_partial_update:
        return

    model = context["model"]
    session = context["session"]
    pending = context.get('pending')

    relationship_list = getattr(package, attr)
    old_list = relationship_list[:]

    relationships = []
    for relationship_dict in relationship_dicts or []:
        obj = d.table_dict_save(relationship_dict,
                              model.PackageRelationship, context)
        relationships.append(obj)

    relationship_list[:] = relationships

    for relationship in set(old_list) - set(relationship_list):
        if pending and relationship.state <> 'deleted':
            relationship.state = 'pending-deleted'
        else:
            relationship.state = 'deleted'
        relationship_list.append(relationship)

def package_dict_save(pkg_dict, context):
    model = context["model"]
    package = context.get("package")
    allow_partial_update = context.get("allow_partial_update", False)
    if package:
        pkg_dict["id"] = package.id
    Package = model.Package

    if 'metadata_created' in pkg_dict:
        del pkg_dict['metadata_created']
    if 'metadata_modified' in pkg_dict:
        del pkg_dict['metadata_modified']

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

    extras = package_extras_save(pkg_dict.get("extras"), pkg, context)

    return pkg

def group_member_save(context, group_dict, member_table_name):
    model = context["model"]
    session = context["session"]
    group = context['group']
    entity_list = group_dict.get(member_table_name, None)

    if entity_list is None:
        if context.get('allow_partial_update', False):
            return {'added': [], 'removed': []}
        else:
            entity_list = []

    entities = {}
    Member = model.Member

    ModelClass = getattr(model, member_table_name[:-1].capitalize())

    for entity_dict in entity_list:
        name_or_id = entity_dict.get('id') or entity_dict.get('name')
        obj = ModelClass.get(name_or_id)
        if obj and obj not in entities.values():
            entities[(obj.id, entity_dict.get('capacity', 'public'))] = obj

    members = session.query(Member).filter_by(
        table_name=member_table_name[:-1],
        group_id=group.id,
    ).all()

    processed = {
        'added': [],
        'removed': []
    }

    entity_member = dict(((member.table_id, member.capacity), member) for member in members)
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


def group_dict_save(group_dict, context):
    from ckan.lib.search import rebuild

    model = context["model"]
    session = context["session"]
    group = context.get("group")
    allow_partial_update = context.get("allow_partial_update", False)
    prevent_packages_update = context.get("prevent_packages_update", False)

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
        pkgs_edited = {
            'added': [],
            'removed': []
        }
    group_users_changed = group_member_save(context, group_dict, 'users')
    group_groups_changed = group_member_save(context, group_dict, 'groups')
    group_tags_changed = group_member_save(context, group_dict, 'tags')
    log.debug('Group save membership changes - Packages: %r  Users: %r  '
            'Groups: %r  Tags: %r', pkgs_edited, group_users_changed,
            group_groups_changed, group_tags_changed)

    # We will get a list of packages that we have either added or
    # removed from the group, and trigger a re-index.
    package_ids = pkgs_edited['removed']
    package_ids.extend( pkgs_edited['added'] )
    if package_ids:
        session.commit()
        map( rebuild, package_ids )

    extras = group_extras_save(group_dict.get("extras", {}), context)
    if extras or not allow_partial_update:
        old_extras = set(group.extras.keys())
        new_extras = set(extras.keys())
        for key in old_extras - new_extras:
            del group.extras[key]
        for key in new_extras:
            group.extras[key] = extras[key]

    return group


def user_dict_save(user_dict, context):

    model = context['model']
    session = context['session']
    user = context.get('user_obj')

    User = model.User
    if user:
        user_dict['id'] = user.id

    if 'password' in user_dict and not len(user_dict['password']):
        del user_dict['password']

    user = d.table_dict_save(user_dict, User, context)

    return user


def related_dict_save(related_dict, context):
    model = context['model']
    session = context['session']

    return d.table_dict_save(related_dict,model.Related, context)


def package_api_to_dict(api1_dict, context):

    package = context.get("package")
    api_version = context.get('api_version')
    assert api_version, 'No api_version supplied in context'

    dictized = {}

    for key, value in api1_dict.iteritems():
        new_value = value
        if key == 'tags':
            if isinstance(value, basestring):
                new_value = [{"name": item} for item in value.split()]
            else:
                new_value = [{"name": item} for item in value]
        if key == 'extras':
            updated_extras = {}
            if package:
                updated_extras.update(package.extras)
            updated_extras.update(value)

            new_value = []

            for extras_key, extras_value in updated_extras.iteritems():
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

def group_api_to_dict(api1_dict, context):

    dictized = {}

    for key, value in api1_dict.iteritems():
        new_value = value
        if key == 'packages':
            new_value = [{"id": item} for item in value]
        if key == 'extras':
            new_value = [{"key": extra_key, "value": value[extra_key]}
                         for extra_key in value]
        dictized[key] = new_value

    return dictized

def task_status_dict_save(task_status_dict, context):
    model = context["model"]
    task_status = context.get("task_status")
    allow_partial_update = context.get("allow_partial_update", False)
    if task_status:
        task_status_dict["id"] = task_status.id

    task_status = d.table_dict_save(task_status_dict, model.TaskStatus, context)
    return task_status

def activity_dict_save(activity_dict, context):

    model = context['model']
    session = context['session']
    user_id = activity_dict['user_id']
    object_id = activity_dict['object_id']
    revision_id = activity_dict['revision_id']
    activity_type = activity_dict['activity_type']
    if activity_dict.has_key('data'):
        data = activity_dict['data']
    else:
        data = None
    activity_obj = model.Activity(user_id, object_id, revision_id,
            activity_type, data)
    session.add(activity_obj)

    # TODO: Handle activity details.

    return activity_obj

def vocabulary_tag_list_save(new_tag_dicts, vocabulary_obj, context):
    model = context['model']
    session = context['session']

    # First delete any tags not in new_tag_dicts.
    for tag in vocabulary_obj.tags:
        if tag.name not in [tag['name'] for tag in new_tag_dicts]:
            tag.delete()
    # Now add any new tags.
    for tag_dict in new_tag_dicts:
        current_tag_names = [tag.name for tag in vocabulary_obj.tags]
        if tag_dict['name'] not in current_tag_names:
            # Make sure the tag belongs to this vocab..
            tag_dict['vocabulary_id'] = vocabulary_obj.id
            # then add it.
            tag_dict_save(tag_dict, {'model': model, 'session': session})

def vocabulary_dict_save(vocabulary_dict, context):
    model = context['model']
    session = context['session']
    vocabulary_name = vocabulary_dict['name']

    vocabulary_obj = model.Vocabulary(vocabulary_name)
    session.add(vocabulary_obj)

    if vocabulary_dict.has_key('tags'):
        vocabulary_tag_list_save(vocabulary_dict['tags'], vocabulary_obj,
            context)

    return vocabulary_obj

def vocabulary_dict_update(vocabulary_dict, context):

    model = context['model']
    session = context['session']

    vocabulary_obj = model.vocabulary.Vocabulary.get(vocabulary_dict['id'])

    if vocabulary_dict.has_key('name'):
        vocabulary_obj.name = vocabulary_dict['name']

    if vocabulary_dict.has_key('tags'):
        vocabulary_tag_list_save(vocabulary_dict['tags'], vocabulary_obj,
            context)

    return vocabulary_obj

def tag_dict_save(tag_dict, context):
    model = context['model']
    tag = context.get('tag')
    if tag:
        tag_dict['id'] = tag.id
    tag = d.table_dict_save(tag_dict, model.Tag, context)
    return tag

def follower_dict_save(data_dict, context, FollowerClass):
    model = context['model']
    session = context['session']
    follower_obj = FollowerClass(
            follower_id=model.User.get(context['user']).id,
            object_id=data_dict['id'])
    session.add(follower_obj)
    return follower_obj
