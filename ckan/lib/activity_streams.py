import ckan.lib.helpers as h

def get_snippet_actor(activity, detail):
    return h.linked_user(activity['user_id'])

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

snippet_functions = {
    'actor': get_snippet_actor,
    'dataset': get_snippet_dataset,
    'tag': get_snippet_tag,
    'group': get_snippet_group,
    'extra': get_snippet_extra,
    'resource': get_snippet_resource,
    'related_item': get_snippet_related_item,
    'related_type': get_snippet_related_type,
}

def get_snippet(name, activity, detail):
    ''' get the snippet for the required data '''
    return snippet_functions[name](activity, detail)
