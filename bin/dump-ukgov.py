# Best to cut and paste this into a paster shell

import ckan.model as model
from ckan.lib.dumper import SimpleDumper

query = model.Session.query(model.Package)

active = model.State.ACTIVE
query = query.filter_by(state=active)

query = query.join('groups').filter(model.Group.name==u'ukgov')

filepath_base = 'hmg.dump'

SimpleDumper().dump(open(filepath_base+'.csv', 'w'), 'csv', query)
SimpleDumper().dump(open(filepath_base+'.json', 'w'), 'json', query)

