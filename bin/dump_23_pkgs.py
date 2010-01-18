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
full_row_dicts = [pkg_to_xl_dict(pkg) for pkg in [model.Package.by_name(u'annakarenina'), model.Package.by_name(u'warandpeace')]]
dumper.PackagesXlWriter(full_row_dicts).save(open('23pkgs.xl', 'wb'))
        
print 'Found %i matching packages' % count
