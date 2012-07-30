import re

from pylons.i18n import _
from webhelpers.html import literal

import ckan.lib.helpers as h
import ckan.lib.base as base
import ckan.logic as logic


# get_snippet functions are used to substitute placeholders in the activity
# strings.  They need to be added to activity_snippet_functions dict to be
# available.

def get_snippet_actor(activity, detail):
    return h.linked_user(activity['user_id'])


def get_snippet_user(activity, detail):
    return h.linked_user(activity['data']['user']['name'])


def get_snippet_dataset(activity, detail):
    data = activity['data']
    return h.dataset_link(data.get('package') or data.get('dataset'))


def get_snippet_tag(activity, detail):
    return h.tag_link(detail['data']['tag'])


def get_snippet_group(activity, detail):
    return h.group_link(activity['data']['group'])


def get_snippet_extra(activity, detail):
    return '"%s"' % detail['data']['package_extra']['key']


def get_snippet_resource(activity, detail):
    return h.resource_link(detail['data']['resource'],
                           activity['data']['package']['id'])


def get_snippet_related_item(activity, detail):
    return h.relate_item_link(activity['data']['related'])


def get_snippet_related_type(activity, detail):
    # FIXME this needs to be translated
    return activity['data']['related']['type']


activity_snippet_functions = {
    'actor': get_snippet_actor,
    'user': get_snippet_user,
    'dataset': get_snippet_dataset,
    'tag': get_snippet_tag,
    'group': get_snippet_group,
    'extra': get_snippet_extra,
    'resource': get_snippet_resource,
    'related_item': get_snippet_related_item,
    'related_type': get_snippet_related_type,
}


# activity_stream_string functions return a translated string for the activity
# containing placeholders for substitution by snippets

def activity_stream_string_added_tag():
    return _("{actor} added the tag {tag} to the dataset {dataset}")


def activity_stream_string_changed_group():
    return _("{actor} updated the group {group}")


def activity_stream_string_changed_package():
    return _("{actor} updated the dataset {dataset}")


def activity_stream_string_changed_package_extra():
    return _("{actor} changed the extra {extra} of the dataset {dataset}")


def activity_stream_string_changed_resource():
    return _("{actor} updated the resource {resource} in the dataset {dataset}")


def activity_stream_string_changed_user():
    return _("{actor} updated their profile")


def activity_stream_string_deleted_group():
    return _("{actor} deleted the group {group}")


def activity_stream_string_deleted_package():
    return _("{actor} deleted the dataset {dataset}")


def activity_stream_string_deleted_package_extra():
    return _("{actor} deleted the extra {extra} from the dataset {dataset}")


def activity_stream_string_deleted_resource():
    return _("{actor} deleted the resource {resource} from the dataset {dataset}")


def activity_stream_string_new_group():
    return _("{actor} created the group {group}")


def activity_stream_string_new_package():
    return _("{actor} created the dataset {dataset}")


def activity_stream_string_new_package_extra():
    return _("{actor} added the extra {extra} to the dataset {dataset}")


def activity_stream_string_new_resource():
    return _("{actor} added the resource {resource} to the dataset {dataset}")


def activity_stream_string_new_user():
    return _("{actor} signed up")


def activity_stream_string_removed_tag():
    return _("{actor} removed the tag {tag} from the dataset {dataset}")


def activity_stream_string_deleted_related_item():
    return _("{actor} deleted the related item {related_item}")


def activity_stream_string_follow_dataset():
    return _("{actor} started following {dataset}")


def activity_stream_string_follow_user():
    return _("{actor} started following {user}")


def activity_stream_string_new_related_item():
    return _("{actor} created the link to related {related_type} {related_item}")


activity_info = {
  'added tag': activity_stream_string_added_tag,
  'changed group': activity_stream_string_changed_group,
  'changed package': activity_stream_string_changed_package,
  'changed package_extra': activity_stream_string_changed_package_extra,
  'changed resource': activity_stream_string_changed_resource,
  'changed user': activity_stream_string_changed_user,
  'deleted group': activity_stream_string_deleted_group,
  'deleted package': activity_stream_string_deleted_package,
  'deleted package_extra': activity_stream_string_deleted_package_extra,
  'deleted resource': activity_stream_string_deleted_resource,
  'new group': activity_stream_string_new_group,
  'new package': activity_stream_string_new_package,
  'new package_extra': activity_stream_string_new_package_extra,
  'new resource': activity_stream_string_new_resource,
  'new user': activity_stream_string_new_user,
  'removed tag': activity_stream_string_removed_tag,
  'deleted related item': activity_stream_string_deleted_related_item,
  'follow dataset': activity_stream_string_follow_dataset,
  'follow user': activity_stream_string_follow_user,
  'new related item': activity_stream_string_new_related_item,
}


def activity_list_to_html(context, activity_stream):
    ''' A generalised function to try to render all activity streams '''

    # These are the activity stream messages

    activity_list = []
    for activity in activity_stream:
        detail = None
        activity_type = activity['activity_type']
        # if package changed then we may have extra details
        if activity_type == 'changed package':
            details = logic.get_action('activity_detail_list')(context=context,
                data_dict={'id': activity['id']})
            if details:
                detail = details[0]
                object_type = detail['object_type']
                if object_type == 'PackageExtra':
                    object_type = 'package_extra'
                new_activity_type = '%s %s' % (detail['activity_type'],
                                           object_type.lower())
                if new_activity_type in activity_info:
                    activity_type = new_activity_type

        if not activity_type in activity_info:
            raise NotImplementedError("No activity renderer for activity "
                "type '%s'" % str(activity_type))
        activity_msg = activity_info[activity_type]()
        # get the data needed by the message
        matches = re.findall('\{([^}]*)\}', activity_msg)
        data = {}
        for match in matches:
            snippet = activity_snippet_functions[match](activity, detail)
            data[str(match)] = snippet
        activity_list.append({'msg': activity_msg,
                              'data': data,
                              'timestamp': activity['timestamp']})
    return literal(base.render('activity_streams/general.html',
        extra_vars={'activities': activity_list}))
