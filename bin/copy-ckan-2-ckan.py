import ckanclient
from optparse import OptionParser
import re

'''
Script for copying packages from one CKAN instance to another using the API
for both.

Some of the commands used:
$ pg_dump -f dump_ckan/nederland.ckan.net.pg_dump -U okfn nederland
$ rsync --progress -z okfn@eu5.okfn.org:/home/okfn/dump_ckan/* /home/dread/db_backup/communities/
$ paster db clean && paster db load /home/dread/db_backup/communities/nederland.ckan.net.pg_dump
$ python bin/copy-ckan-2-ckan.py -k tester -g country-si -t "Slovenia" -s si.ckan.net http://127.0.0.1:5000/api http://127.0.0.1:5001/api
'''

def copy_packages(source_ckan_uri,
                  dest_ckan_uri, dest_api_key,
                  dest_group_name, dest_group_title,
                  site_name, filter,
                  ):
    ckan1 = ckanclient.CkanClient(base_location=source_ckan_uri)
    ckan2 = ckanclient.CkanClient(base_location=dest_ckan_uri,
                                  api_key=dest_api_key)

    # ensure pkg references will be the same type
    ckan1_api_version = ckan1.api_version_get()
    ckan2_api_version = ckan2.api_version_get()
    assert ckan1_api_version == ckan2_api_version

    # ensure group exists
    existing_groups = set(ckan2.group_register_get())
    def add_group_if_needed(group_name, group_title=None, fetch_title=False):
        if group_name not in existing_groups:
            if fetch_title:
                group_title = ckan1.group_entity_get(group_name)['title']
            group = {'name': group_name,
                     'title': group_title}
            ckan2.group_register_post(group)
            existing_groups.add(group_name)
            print 'Created group: %s' % group_name

    if dest_group_name:
        add_group_if_needed(dest_group_name, dest_group_title)

    existing_pkgs = ckan2.package_register_get()

    if site_name:
        import_tag = 'meta.imported-from.%s' % re.sub('[^a-zA-Z0-9-_.]', '', site_name)
        print 'Tagging with: %s' % import_tag
    else:
        import_tag = None
    
    # go through all packages
    package_list = ckan1.package_register_get()
    print 'Found %i packages to copy' % len(package_list)

    if filter:
        filter_re = re.compile(filter)
        package_list = [pkg for pkg in package_list \
                        if filter_re.match(pkg)]
        print 'Filtered down to %i packages' % len(package_list)
    
    for package_ref in package_list[:]:
        try:
            pkg = ckan1.package_entity_get(package_ref)
        except ckanclient.CkanApiNotAuthorizedError:
            print '!! Not authorized: %s' % package_ref
            package_list.remove(package_ref)
            continue
        print 'Got package: %s' % pkg['name']

        # put in groups
        for group_name in pkg['groups']:
            add_group_if_needed(group_name, fetch_title=True)
        if dest_group_name:
            # only works on CKAN 1.5.1 so add all at end anyway
            pkg['groups'].append(dest_group_name)

        del pkg['id']

        if import_tag:
            pkg['tags'].append(import_tag)

        # munge non-conformant tags
        pkg['tags'] = [munge_tag(tag) for tag in pkg['tags']]

        # do the copy
        if package_ref in existing_pkgs:
            existing_pkg = ckan2.package_entity_get(pkg['name'])
            pkg_returned = ckan2.package_entity_put(pkg)
            print '...updated'
        else:
            pkg_returned = ckan2.package_register_post(pkg)
            print '...created'
        groups_not_added_to = set(pkg['groups']) - set(pkg_returned['groups']) - set((dest_group_name or []))
        # packages don't get added to the group before when CKAN <= 1.5 so
        # we have to do this now
        for group_ref in groups_not_added_to:
            group = ckan2.group_entity_get(group_ref)
            group['packages'].append(pkg['name'])
            ckan2.group_entity_put(group)
            print '...and added to group %s' % group_ref

    if dest_group_name:
        group = ckan2.group_entity_get(dest_group_name)
        pkgs_to_add_to_group = list(set(package_list) - set(group['packages']))
        if pkgs_to_add_to_group:
            print 'Adding %i packages to group %s: %r' % (len(pkgs_to_add_to_group), dest_group_name, pkgs_to_add_to_group)
            group['packages'].extend(pkgs_to_add_to_group)
            ckan2.group_entity_put(group)

def _munge_to_length(string, min_length, max_length):
    '''Pad/truncates a string'''
    if len(string) < min_length:
        string += '_' * (min_length - len(string))
    if len(string) > max_length:
        string = string[:max_length]
    return string

MIN_TAG_LENGTH, MAX_TAG_LENGTH = (2, 100)

def munge_tag(tag):
    tag = tag.lower().strip()
    tag = re.sub(r'[^a-zA-Z0-9 ]', '', tag).replace(' ', '-')
    tag = _munge_to_length(tag, MIN_TAG_LENGTH, MAX_TAG_LENGTH)
    return tag

usage = '''%prog [OPTIONS] <source_ckan_api_uri> <destination_ckan_api_uri>
Copy datasets from ckan to another and put them in a group.'''
parser = OptionParser(usage=usage)
parser.add_option("-k", "--destination-ckan-api-key", dest="destination_ckan_api_key",
                  help="Destination CKAN's API key", metavar="API-KEY")
parser.add_option("-g", "--group-name", dest="group_name",
                  help="Destination CKAN group's name")
parser.add_option("-t", "--group-title", dest="group_title",
                  help="Destination CKAN group's title")
parser.add_option("-s", "--site-name", dest="site_name",
                  help="Name of source CKAN site - so source can be tagged")
parser.add_option("-f", "--filter", dest="filter",
                  help="Filter package names (regex format)")

(options, args) = parser.parse_args()

assert len(args) == 2, 'The source and destination CKAN API URIs are the only two arguments. Found: %r' % args
source_ckan_uri, destination_ckan_uri = args
print 'Key: ', options.destination_ckan_api_key

copy_packages(source_ckan_uri,
              destination_ckan_uri,
              options.destination_ckan_api_key,
              options.group_name, options.group_title,
              options.site_name, options.filter)
