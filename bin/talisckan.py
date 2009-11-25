import sys
from optparse import OptionParser

import ckanclient
import ckan.lib.talis as talis

class TalisCkan:
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
        
    def get_ckan_package_names(self):
        res = self.ckan.package_register_get()
        assert self.ckan.last_status == 200, self.ckan.last_status
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

    def dump_talis(self, pkg_names):
        if pkg_names:
            for pkg_name in pkg_names:
                print self._talis.get_pkg(pkg_name)
        else:
            # TODO
            print self._talis.dump()

        
if __name__ == '__main__':
    usage = '''usage: %prog [options] <command>
    commands:
        dump_talis - show contents of packages in talis
        load_ckan_to_talis - 
    '''
    parser = OptionParser(usage=usage)
#    parser.add_option('-k', '--apikey', dest='apikey', help='API key')
    parser.add_option('-c', '--ckanhost', dest='ckanhost', help='CKAN host name', default='www.ckan.net')
    parser.add_option('-s', '--store', dest='store', help='Talis store name', default='ckan-dev1')
    parser.add_option('-u', '--talislogin', dest='talislogin', help='Talis login details: "username:password"', default='ckan')
#    parser.add_option('-u', '--talisusername', dest='talisuser', help='Talis user name', default='ckan')
    parser.add_option('-p', '--packages', dest='packages', help='Quoted list of packages', default='')
    parser.add_option('', '--startfrompackage', dest='startpackage', help='Package to start from', default='')

    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.print_help()
        sys.exit(0)
    command = args[0]

    if ':' in options.talislogin:
        talisuser, talispassword = options.talislogin.split(':')
    else:
        talisuser, talispassword = options.talislogin, ''

    tc = TalisCkan(options.ckanhost, options.store, talisuser, talispassword)

    pkg_names = None
    if options.startpackage:
        start_index = pkg_names.index(options.startpackage)
        assert start_index
        pkg_names = pkg_names[start_index:]
    if options.packages:
        pkgs = options.packages.replace(',', ' ')
        pkg_names = pkgs.split() if ' ' in pkgs else [pkgs]
            
    if command == 'load_ckan_to_talis':
        pkg_names = tc.get_ckan_package_names()
        start_index = 0
        for pkg_name in pkg_names:
            tc.load_to_talis(pkg_name)
    elif command == 'dump_talis':
        tc.dump_talis(pkg_names)
