import os

xl_filename = '28pkgs.xls'
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

print 'Found %i matching packages' % count

dumper_ = dumper.PackagesXlWriter(xl_dicts)
dumper_.add_col_titles(('notes', 'url', 'resource-0-url', 'resource-0-format', 'resource-0-description', 'author', 'author_email', 'state', 'version', 'tags', 'groups', 'license' ))
dumper_.save(open(xl_filename, 'wb'))
print 'Saved in %s' % xl_filename
