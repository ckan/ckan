import os

data_path = os.path.expanduser('~/ckan-local/data/')

def load_month(month, year):
    assert month < 13
    assert year > 2000
    data_filepath = os.path.join(data_path, 'ons_hub_%s_%#02d.xml' % (year, month))
    try:
        cmd = 'paster db load-onshub %s' % (data_filepath)
        print cmd
        response = os.system(cmd)
        print '\n%s %r' % (data_filepath, response)
    except Exception, e:
        print '\nEXCEPTION %s %r' % (data_filepath, e.args)


load_month(1, 2010)
for year in (2009, 2008, 2007, 2006, 2005, 2004):
    for month in range(12):
        load_month(month+1, year)

