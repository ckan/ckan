import os

import loadconfig
path = os.path.abspath('development.ini')
loadconfig.load_config(path)

import ckan.model as model

ukgov = model.Group.by_name(u'ukgov')
if not ukgov:
    model.Session.add(model.Group(name=u'ukgov'))
    model.repo.commit_and_remove()

pkgs = model.Session.query(model.Package).all()
ukgov = model.Group.by_name(u'ukgov')
for pkg in pkgs:
    print 'Package: ', pkg.name
    
    # Add packages to group ukgov
    if pkg not in ukgov.packages:
        ukgov.packages.append(pkg)
        print 'Added to group'

    # Add extra 'import_source'
    if not pkg.extras.has_key('import_source'):
        pkg.extras['import_source'] = 'Manual 28, Oct 09'
        print 'Added source'

rev = model.repo.new_revision() 
rev.author = u'auto-loader'
rev.message = u'Add tag and group'

model.repo.commit_and_remove()
