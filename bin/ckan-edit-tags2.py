import os

import loadconfig
path = os.path.abspath('development.ini')
loadconfig.load_config(path)

import ckan.model as model

for pkg in model.Session.query(model.Package):
    source = pkg.extras.get('import_source', u'')
    ns = pkg.extras.get('national_statistic', u'')
    remove_national_statistic = not source.startswith('ONS-') and ns == 'yes'
    print 'Package: name=%s national_statistic=%s source=%s remove_ns=%s' % (pkg.name, ns, source, remove_national_statistic)
    
    if remove_national_statistic:
        pkg.extras['national_statistic'] = u''

        rev = model.repo.new_revision() 
        rev.author = u'auto-loader'
        rev.message = u'Removed unconfirmed national_statistic designation'

        model.Session.commit()

model.Session.remove()
