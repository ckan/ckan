import os

import loadconfig
path = os.path.abspath('development.ini')
loadconfig.load_config(path)

import ckan.model as model
import ckan.lib.dumper as dumper

pkg_to_xl_dict = dumper.PackagesXlWriter.pkg_to_xl_dict

count = 0
xl_dicts = []
for pkg in model.Session.query(model.Package):
    if pkg.revision.author == 'frontend':
        count += 1
        print pkg.name
        xl_dict = pkg_to_xl_dict(pkg)
        xl_dicts.append(xl_dict)
dumper.PackagesXlWriter(xl_dicts).save(open('28pkgs.xls', 'wb'))
        
print 'Found %i matching packages' % count
