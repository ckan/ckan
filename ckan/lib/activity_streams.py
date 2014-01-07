import re

from webhelpers.html import literal

import ckan.lib.helpers as h
import ckan.lib.base as base
import ckan.logic as logic

from ckan.common import _

# get_snippet_*() functions replace placeholders like {user}, {dataset}, etc.
# in activity strings with HTML representations of particular users, datasets,
# etc.

def get_snippet_actor(activity, detail):
    return literal('''<span class="actor">%s</span>'''
        % (h.linked_user(activity['user_id'], 0, 30))
        )

def get_snippet_user(activity, detail):
    return literal('''<span>%s</span>'''
        % (h.linked_user(activity['object_id'], 0, 20))
        )

def get_snippet_dataset(activity, detail):
    data = activity['data']
    link = h.dataset_link(data.get('package') or data.get('dataset'))
    return literal('''<span>%s</span>'''
        % (link)
        )

def get_snippet_tag(activity, detail):
    return h.tag_link(detail['data']['tag'])

def get_snippet_group(activity, detail):
    link = h.group_link(activity['data']['group'])
    return literal('''<span>%s</span>'''
        % (link)
        )

def get_snippet_organization(activity, detail):
    return h.organization_link(activity['data']['group'])

def get_snippet_extra(activity, detail):
    return '"%s"' % detail['data']['package_extra']['key']

def get_snippet_resource(activity, detail):
    return h.resource_link(detail['data']['resource'],
                           activity['data']['package']['id'])

def get_snippet_related_item(activity, detail):
    return h.related_item_link(activity['data']['related'])

def get_snippet_related_type(activity, detail):
    # FIXME this needs to be translated
    return activity['data']['related']['type']

# activity_stream_string_*() functions return translatable string
# representations of activity types, the strings contain placeholders like
# {user}, {dataset} etc. to be replaced with snippets from the get_snippet_*()
# functions above.

def activity_stream_string_added_tag(context, activity):
    return _("{actor} added the tag {tag} to the dataset {dataset}")

def activity_stream_string_changed_group(context, activity):
    return _("{actor} updated the group {group}")

def activity_stream_string_changed_organization(context, activity):
    return _("{actor} updated the organization {organization}")

def activity_stream_string_changed_package(context, activity):
    return _("{actor} updated the dataset {dataset}")

def activity_stream_string_changed_package_extra(context, activity):
    return _("{actor} changed the extra {extra} of the dataset {dataset}")

def activity_stream_string_changed_resource(context, activity):
    return _("{actor} updated the resource {resource} in the dataset {dataset}")

def activity_stream_string_changed_user(context, activity):
    return _("{actor} updated their profile")

def activity_stream_string_changed_related_item(context, activity):
    if activity['data'].get('dataset'):
        return _("{actor} updated the {related_type} {related_item} of the "
                "dataset {dataset}")
    else:
        return _("{actor} updated the {related_type} {related_item}")

def activity_stream_string_deleted_group(context, activity):
    return _("{actor} deleted the group {group}")

def activity_stream_string_deleted_organization(context, activity):
    return _("{actor} deleted the organization {organization}")

def activity_stream_string_deleted_package(context, activity):
    return _("{actor} deleted the dataset {dataset}")

def activity_stream_string_deleted_package_extra(context, activity):
    return _("{actor} deleted the extra {extra} from the dataset {dataset}")

def activity_stream_string_deleted_resource(context, activity):
    return _("{actor} deleted the resource {resource} from the dataset "
             "{dataset}")

def activity_stream_string_new_group(context, activity):
    return _("{actor} created the group {group}")

def activity_stream_string_new_organization(context, activity):
    return _("{actor} created the organization {organization}")

def activity_stream_string_new_package(context, activity):
    return _("{actor} created the dataset {dataset}")

def activity_stream_string_new_package_extra(context, activity):
    return _("{actor} added the extra {extra} to the dataset {dataset}")

def activity_stream_string_new_resource(context, activity):
    return _("{actor} added the resource {resource} to the dataset {dataset}")

def activity_stream_string_new_user(context, activity):
    return _("{actor} signed up")

def activity_stream_string_removed_tag(context, activity):
    return _("{actor} removed the tag {tag} from the dataset {dataset}")

def activity_stream_string_deleted_related_item(context, activity):
    return _("{actor} deleted the related item {related_item}")

def activity_stream_string_follow_dataset(context, activity):
    return _("{actor} started following {dataset}")

def activity_stream_string_follow_user(context, activity):
    return _("{actor} started following {user}")

def activity_stream_string_follow_group(context, activity):
    return _("{actor} started following {group}")

def activity_stream_string_new_related_item(context, activity):
    if activity['data'].get('dataset'):
        return _("{actor} added the {related_type} {related_item} to the "
                 "dataset {dataset}")
    else:
        return _("{actor} added the {related_type} {related_item}")

# A dictionary mapping activity snippets to functions that expand the snippets.
activity_snippet_functions = {
    'actor': get_snippet_actor,
    'user': get_snippet_user,
    'dataset': get_snippet_dataset,
    'tag': get_snippet_tag,
    'group': get_snippet_group,
    'organization': get_snippet_organization,
    'extra': get_snippet_extra,
    'resource': get_snippet_resource,
    'related_item': get_snippet_related_item,
    'related_type': get_snippet_related_type,
}

# A dictionary mapping activity types to functions that return translatable
# string descriptions of the activity types.
activity_stream_string_functions = {
  'added tag': activity_stream_string_added_tag,
  'changed group': activity_stream_string_changed_group,
  'changed organization': activity_stream_string_changed_organization,
  'changed package': activity_stream_string_changed_package,
  'changed package_extra': activity_stream_string_changed_package_extra,
  'changed resource': activity_stream_string_changed_resource,
  'changed user': activity_stream_string_changed_user,
  'changed related item': activity_stream_string_changed_related_item,
  'deleted group': activity_stream_string_deleted_group,
  'deleted organization': activity_stream_string_deleted_organization,
  'deleted package': activity_stream_string_deleted_package,
  'deleted package_extra': activity_stream_string_deleted_package_extra,
  'deleted resource': activity_stream_string_deleted_resource,
  'new group': activity_stream_string_new_group,
  'new organization': activity_stream_string_new_organization,
  'new package': activity_stream_string_new_package,
  'new package_extra': activity_stream_string_new_package_extra,
  'new resource': activity_stream_string_new_resource,
  'new user': activity_stream_string_new_user,
  'removed tag': activity_stream_string_removed_tag,
  'deleted related item': activity_stream_string_deleted_related_item,
  'follow dataset': activity_stream_string_follow_dataset,
  'follow user': activity_stream_string_follow_user,
  'follow group': activity_stream_string_follow_group,
  'new related item': activity_stream_string_new_related_item,
}

# A dictionary mapping activity types to the icons associated to them
activity_stream_string_icons = {
  'added tag': 'tag',
  'changed group': 'group',
  'changed package': 'sitemap',
  'changed package_extra': 'edit',
  'changed resource': 'file',
  'changed user': 'user',
  'deleted group': 'group',
  'deleted package': 'sitemap',
  'deleted package_extra': 'edit',
  'deleted resource': 'file',
  'new group': 'group',
  'new package': 'sitemap',
  'new package_extra': 'edit',
  'new resource': 'file',
  'new user': 'user',
  'removed tag': 'tag',
  'deleted related item': 'picture',
  'follow dataset': 'sitemap',
  'follow user': 'user',
  'follow group': 'group',
  'new related item': 'picture',
  'changed organization': 'briefcase',
  'deleted organization': 'briefcase',
  'new organization': 'briefcase',
  'undefined': 'certificate', # This is when no activity icon can be found
}

# A list of activity types that may have details
activity_stream_actions_with_detail = ['changed package']

def activity_list_to_html(context, activity_stream, extra_vars):
    '''Return the given activity stream as a snippet of HTML.

    :param activity_stream: the activity stream to render
    :type activity_stream: list of activity dictionaries
    :param extra_vars: extra variables to pass to the activity stream items
        template when rendering it
    :type extra_vars: dictionary

    :rtype: HTML-formatted string

    '''
    activity_list = [] # These are the activity stream messages.
    for activity in activity_stream:
        detail = None
        activity_type = activity['activity_type']
        # Some activity types may have details.
        if activity_type in activity_stream_actions_with_detail:
            details = logic.get_action('activity_detail_list')(context=context,
                data_dict={'id': activity['id']})
            # If an activity has just one activity detail then render the
            # detail instead of the activity.
            if len(details) == 1:
                detail = details[0]
                object_type = detail['object_type']

                if object_type == 'PackageExtra':
                    object_type = 'package_extra'

                new_activity_type = '%s %s' % (detail['activity_type'],
                                            object_type.lower())
                if new_activity_type in activity_stream_string_functions:
                    activity_type = new_activity_type

        if not activity_type in activity_stream_string_functions:
            raise NotImplementedError("No activity renderer for activity "
                "type '%s'" % activity_type)

        if activity_type in activity_stream_string_icons:
            activity_icon = activity_stream_string_icons[activity_type]
        else:
            activity_icon = activity_stream_string_icons['undefined']

        activity_msg = activity_stream_string_functions[activity_type](context,
                activity)

        # Get the data needed to render the message.
        matches = re.findall('\{([^}]*)\}', activity_msg)
        data = {}
        for match in matches:
            snippet = activity_snippet_functions[match](activity, detail)
            data[str(match)] = snippet

        activity_list.append({'msg': activity_msg,
                              'type': activity_type.replace(' ', '-').lower(),
                              'icon': activity_icon,
                              'data': data,
                              'timestamp': activity['timestamp'],
                              'is_new': activity.get('is_new', False)})
    extra_vars['activities'] = activity_list
    return literal(base.render('activity_streams/activity_stream_items.html',
        extra_vars=extra_vars))
