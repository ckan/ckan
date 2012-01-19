'''
Script to sort out the tags imported from ca.ckan.net to thedatahub.org and
got mangled in the process.
'''

import re
from optparse import OptionParser
import copy

import ckanclient
from status import Status

def sort_out_tags(source_ckan_uri,
                  dest_ckan_uri, dest_api_key,
                  ):
    ckan1 = ckanclient.CkanClient(base_location=source_ckan_uri)
    ckan2 = ckanclient.CkanClient(base_location=dest_ckan_uri,
                                  api_key=dest_api_key)

    # ensure group exists
    group = 'country-ca'
    assert group in set(ckan2.group_register_get())
    group_to_change = 'canadagov'

    # work out tag mappings
    tag_status = Status('tag mapping')
    tag_replace_map = {}
    source_tags = ckan1.tag_register_get()
    for tag in source_tags:
        mangled_tag = re.sub('[-._]', '', tag)
        replacement_tag = tag
        # Change underscores to hyphens
        replacement_tag = replacement_tag.replace('_', '-')
        # Remove trailing punctuation
        if replacement_tag[-1] in '_-.':
            replacement_tag = replacement_tag[:-1]
        if replacement_tag[0] in '_-.':
            replacement_tag = replacement_tag[1:]
        if mangled_tag == replacement_tag:
            tag_status.record('Unchanged', mangled_tag, do_print=False)
            continue
        if mangled_tag in tag_replace_map and tag_replace_map[mangled_tag] != replacement_tag:
            print 'Warning - can\'t differentiate %s : %s / %s' % \
                  (mangled_tag, tag_replace_map[mangled_tag], replacement_tag)
        tag_status.record('Mapping added', '%s:%s' % (mangled_tag, replacement_tag), do_print=False)
        tag_replace_map[mangled_tag] = replacement_tag
    example_map = tag_replace_map.items()[0]
    print tag_status

    # Custom mappings
    tag_replace_map['metaimportedfromcackannet'] = 'meta.imported-from-ca-ckan-net'

    # edit packages
    pkg_status = Status('Packages')
    pkgs = ckan2.group_entity_get(group)['packages']
    print 'Packages in the group: %i' % len(pkgs)
    for pkg_name in pkgs:
        pkg = ckan2.package_entity_get(pkg_name)
        original_pkg = copy.deepcopy(pkg)

        # Change tags
        edited_tags = [tag_replace_map.get(tag, tag) for tag in pkg['tags']]
        if 'canada' in edited_tags:
            edited_tags.remove('canada')

        if group_to_change in pkg['groups']:
            pkg['groups'].remove(group_to_change)
            edited_tags.append('canada-gov')

        if set(pkg['tags']) != set(edited_tags):
            pkg['tags'] = edited_tags
            print '%s: %r -> %r' % (pkg_name, sorted(original_pkg['tags']), sorted(edited_tags))

        if pkg == original_pkg:
            pkg_status.record('Unchanged', pkg_name)
            continue

        try:
            ckan2.package_entity_put(pkg)
        except ckanclient.CkanApiError, e:
            pkg_status.record('Error: %r' % e.args, pkg_name)
            continue
        
        pkg_status.record('Successfully changed', pkg_name)

    print pkg_status

usage = '''%prog [OPTIONS] <source_ckan_api_uri> <destination_ckan_api_uri>
Recopy tags that got mangled in Canadian copy.'''
parser = OptionParser(usage=usage)
parser.add_option("-k", "--destination-ckan-api-key", dest="destination_ckan_api_key",
                  help="Destination CKAN's API key", metavar="API-KEY")

(options, args) = parser.parse_args()

assert len(args) == 2, 'The source and destination CKAN API URIs are the only two arguments. Found: %r' % args
source_ckan_uri, destination_ckan_uri = args
print 'Key: ', options.destination_ckan_api_key

sort_out_tags(source_ckan_uri,
              destination_ckan_uri,
              options.destination_ckan_api_key,
)
