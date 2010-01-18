import os

output_path = os.path.expanduser('~/ckan-local/data/')

url_base = 'http://www.statistics.gov.uk/hub/release-calendar/rss.xml?lday=01&lmonth=%(month)s&lyear=%(year)s&uday=31&umonth=%(month)s&uyear=%(year)s'
for year in (2009, 2008, 2007, 2006, 2005, 2004):
    for month in range(12):
        url = url_base % {'year':year, 'month':month+1}
        output_filepath = os.path.join(output_path, 'ons_hub_%s_%#02d.xml' % (year, month+1))
        response = os.system('wget "%s" --output-document=%s' % (url, output_filepath))
        print response
