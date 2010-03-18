'''Script for doing various edits to ckan data that is stored on a local
CKAN instance'''

import os
import sys
from optparse import OptionParser

def ons_prefix():
    '''Remove "http://www.statistics.gov.uk/" from resource IDs derived from ONS'''
    from ckan import model
    prefix = 'http://www.statistics.gov.uk/'
    pkgs_changed = []
    for pkg in model.Session.query(model.Package):
        is_changed = False
        for resource in pkg.resources:
            is_changed = is_changed or prefix in resource.description
            if is_changed:
                resource.description = resource.description.replace(prefix, '')
        if is_changed:
            rev = model.repo.new_revision() 
            rev.author = u'auto-loader'
            rev.message = u'Removed domain from ONS IDs'

            model.Session.commit()

            pkgs_changed.append(pkg.name)
    
    model.Session.remove()
    print 'Removed ONS prefix from %i packages out of %i' % (len(pkgs_changed), model.Session.query(model.Package).count())
            

if __name__ == '__main__':
    usage = '''usage: %prog [options] <command>
    options:
        -c <config.ini> - pylons config ini filepath (default=development.ini)
    commands:
        ons-prefix - Remove ONS prefix in resources
    '''
    parser = OptionParser(usage=usage)
    parser.add_option('-c', '--config', dest='config', help='Config filepath', default='development.ini')

    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.print_help()
        sys.exit(0)
    command = args[0]

    if options.config:
        import loadconfig
        path = os.path.abspath(options.config)
        loadconfig.load_config(path)
            
    if command == 'ons-prefix':
        ons_prefix()
