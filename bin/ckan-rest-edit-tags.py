import sys
from optparse import OptionParser

import ckanclient

class TagEditor:
    def __init__(self, host, api_key):
        if not host.startswith('http://'):
            host = 'http://' + host
        host = host + '/api'
        self.ckan = ckanclient.CkanClient(base_location=host, api_key=api_key)
        
    def get_packages_by_tag_search(self, tagname):
        res = self.ckan.package_search('', {'tags':tagname, 'all_fields':1})
        status = self.ckan.last_status
        assert status == 200, status
        packages = res['results']
        return packages

    def get_package_names_by_tag(self, tagname):
        res = self.ckan.tag_entity_get(tagname)
        assert self.ckan.last_status == 200, self.ckan.last_status
        packages = res
        return packages

    def edit_tags(self, pkg_name, add_tags, remove_tags):
        pkg = self.ckan.package_entity_get(pkg_name)
        if self.ckan.last_status != 200:
            print 'Error! Package: %s Error reading package: %s' % (pkg_name, self.ckan.last_status)
            return self.ckan.last_status
        tags = set()
        for tag in pkg['tags']:
            tags.add(tag)
        tags_before = tags.copy()
        for tag in add_tags:
            tags.add(tag)
        for tag in remove_tags:
            tags.discard(tag)
        if tags == tags_before:
            print "PKG %s: no change" % (pkg_name)
            return
        print "PKG %s: %i->%i tags" % (pkg_name, len(tags_before), len(tags))
        self.ckan.package_entity_put({'name':pkg_name,
                                      'tags':list(tags)})
        if self.ckan.last_status != 200:
            print 'Error! Package: %s Error writing package: %s' % (pkg_name, self.ckan.last_status)
            return self.ckan.last_status
        return self.ckan.last_status 
        

if __name__ == "__main__":
    usage = "usage: %prog [options] ckan-host"
    parser = OptionParser(usage=usage)
    parser.add_option("-k", "--apikey", dest="apikey", 
                      help="API key")

    (options, args) = parser.parse_args()

    if not args:
        parser.print_help()
        sys.exit(0)
        
    ckan_host = args[0]
    te = TagEditor(ckan_host, options.apikey)

    pkg_names = te.get_package_names_by_tag('ckanupload.esw.200910')
    for pkg_name in pkg_names:
        te.edit_tags(pkg_name, ['lod', 'linkeddata'], ['linked-open-data'])
