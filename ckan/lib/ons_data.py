import os
import urllib
import datetime
import logging

def import_recent(ons_cache_dir, log=False):
    ons = OnsData(ons_cache_dir, log)
    url, url_name = ons.get_url_recent()
    return ons.import_([(url, url_name)])

def import_all(ons_cache_dir, log=False):
    ons = OnsData(ons_cache_dir, log)
    url_tuples = []
    for year in (2009, 2008, 2007, 2006, 2005, 2004):
        for month in range(12):
            url_tuples.append(ons.get_url_month(month+1, year))
    url_tuples.append(ons.get_url_month(1, 2010))
    url_tuples.append(ons.get_url_month(2, 2010)) # TODO auto update

    url, url_name = ons.get_url_recent()
    return ons.import_(url_tuples)



class OnsData(object):
    def __init__(self, local_cache_dir='~/ons_data', log=False):
        self._local_cache_dir = os.path.expanduser(local_cache_dir)
        self._url_base = 'http://www.statistics.gov.uk/hub/release-calendar/rss.xml?lday=%(lday)s&lmonth=%(lmonth)s&lyear=%(lyear)s&uday=%(uday)s&umonth=%(umonth)s&uyear=%(uyear)s'
        self._logging = log
        
    def import_(self, url_tuples):
        from pylons import config
        import ckan.getdata.ons_hub as ons_hub
        import ckan.model as model

        num_packages_before = model.Session.query(model.Package).count()

        ons_cache_dir = os.path.join(config.get('here'), 'ons_data')
        getter = ons_hub.Data()
        for url_tuple in url_tuples:
            url, url_name = url_tuple
            ons_filepath = self.download(url, url_name)
            getter.load_xml_into_db(ons_filepath, True)

        num_packages_after = model.Session.query(model.Package).count()
        new_packages = num_packages_after - num_packages_before
        assert new_packages >= 0, new_packages
        self.log(logging.info, 'Loaded %i new packages. New total is %i' % (new_packages, num_packages_after))
        return new_packages, num_packages_after


    def download(self, url, url_name):
        local_filepath = os.path.join(self._local_cache_dir, 'ons_data_%s' % url_name)
        if not os.path.exists(local_filepath):
            urllib.urlretrieve(url, local_filepath)
        else:
            self.log(logging.info, 'ONS Data already downloaded: %s' % url_name)
        return local_filepath
        
    def download_month(self, month, year):
        assert month < 13
        assert year > 2000
        url, url_name = get_url_month(month, year)
        self.download(url, url_name)

    def get_url(self, lday, lmonth, lyear, uday, umonth, uyear):
        params = { lday:lday, lmonth:lmonth, lyear:lyear,
                   uday:uday, umonth:umonth, uyear:uyear, }
        url = self._url_base % params
        url_id = '%(lyear)s-%(lmonth)s-%(lday)s_-_%(uyear)s-%(umonth)s-%(uday)s' % params
        return url, url_id
    
    def get_url_month(self, month, year):
        id = '%(lday)s-%(lmonth)s-%(lyear)s_-_%(uday)s-%(umonth)s-%(uyear)s'
        url = self._url_base % {'lday':1, 'lmonth':month, 'lyear':year,
                                'uday':31, 'umonth':month, 'uyear':year,}
        url_id = datetime.date(year, month, 1).strftime('%Y-%m')
        return url, url_id
    
    def get_url_recent(self, days=7):
        from_ = datetime.date.today() - datetime.timedelta(days=days)
        to = datetime.date.today()
        url = self._url_base % {'lday':from_.strftime('%d'),
                                'lmonth':from_.strftime('%m'),
                                'lyear':from_.strftime('%Y'),
                                'uday':to.strftime('%d'),
                                'umonth':to.strftime('%m'),
                                'uyear':to.strftime('%Y'),
                                }
        url_id = to.strftime(str(days) + '_days_to_%Y-%m-%d')
        return url, url_id

    def log(self, log_func, msg):
        if self._logging:
            log_func(msg)
        else:
            print '%s: %s' % (log_func.func_name, msg)
