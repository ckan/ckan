import sys
from optparse import OptionParser

import ckanclient
import talis

class TalisLoader:
    def __init__(self, ckan_host, store, talisuser, talispassword):
        api_key = None
        
        # ckan connection
        if not ckan_host.startswith('http://'):
            ckan_host = 'http://' + ckan_host
        ckan_host = ckan_host + '/api'
        self.ckan = ckanclient.CkanClient(base_location=ckan_host,
                                          api_key=api_key)

        # talis connection
        talis.TalisLogin.init(store, talisuser, talispassword)
        self._talis = talis.Talis()
        
    def get_package_names(self):
        res = self.ckan.package_register_get()
        assert self.ckan.last_status == 200, 'Error accessing \'%s\': %s' % (self.ckan.last_location, self.ckan.last_status)
        packages = res
        return packages

    def load_to_talis(self, pkg_name):
        print '=== Loading %s ===' % pkg_name
        res = self.ckan.package_entity_get(pkg_name)
        if self.ckan.last_status != 200:
            print 'Failed to read CKAN package %s: %s' % (pkg_name, self.ckan.last_status)
            return
        pkg_dict = res
        res = self._talis.post_pkg(pkg_dict)
        if res:
            print 'Failed to post package %s to Talis: %s' % (pkg_name, res)
            return
##        res = self._talis.get_pkg(pkg_name)
##        assert res, res
##        print 'Done!'
        

if __name__ == '__main__':
    usage = 'usage: %prog [options] talis-password'
    parser = OptionParser(usage=usage)
#    parser.add_option('-k', '--apikey', dest='apikey', help='API key')
    parser.add_option('-c', '--ckanhost', dest='ckanhost', help='CKAN host name', default='www.ckan.net')
    parser.add_option('-s', '--store', dest='store', help='Talis store name', default='ckan-dev1')
    parser.add_option('-u', '--talisusername', dest='talisuser', help='Talis user name', default='ckan')
    parser.add_option('', '--startfrompackage', dest='startpackage', help='Package to start from', default='')
    parser.add_option('-p', '--packages', dest='packages', help='Quoted list of packages to upload', default='')

    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.print_help()
        sys.exit(0)

    talispassword = args[0]

    te = TalisLoader(options.ckanhost, options.store, options.talisuser, talispassword)

    pkg_names = te.get_package_names()
    start_index = 0
    if options.startpackage:
        start_index = pkg_names.index(options.startpackage)
        assert start_index
        pkg_names = pkg_names[start_index:]
    elif options.packages:
        pkgs = options.packages.replace(',', ' ')
        pkg_names = pkgs.split() if ' ' in pkgs else [pkgs]
    for pkg_name in pkg_names:
        te.load_to_talis(pkg_name)
                              
