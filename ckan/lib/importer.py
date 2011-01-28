import StringIO

import re
import datetime

from ckan.model.license import LicenseRegister
import ckan.model as model

class ImportException(Exception):
    pass

class RowParseError(ImportException):
    pass

class DataRecords(object):
    '''Represents raw data records in the form of a dictionary.
    (The raw data is not yet processed - it will be converted to package_dict
    in the next step.)
    '''
    @property
    def records(self):
        '''Yields each record as a dict.'''
        raise NotImplementedError


class PackageImporter(object):
    '''Base class for an importer that converts a particular file type
    and creates corresponding package dictionaries.'''
    _log = []

    def __init__(self, filepath=None, buf=None):
        assert filepath or buf, 'Must specify a filepath or a buf.'
        self._filepath = filepath
        self._buf = buf
        self.import_into_package_records()

    def import_into_package_records(self):
        '''Reads in the source file given by self._filepath and
        stores the resulting DataRecords in self._package_data_records.'''
        raise NotImplementedError()

    @classmethod
    def log(cls, msg):
        cls._log.append(msg)

    @classmethod
    def get_log(cls):
        return cls._log

    @classmethod
    def clear_log(cls):
        cls._log = []

    def record_2_package(self, record_dict):
        '''Converts a raw record into a package dictionary.
        @param record_dict - the raw record
        @return - pkg_dict'''
        raise NotImplementedError()

    def pkg_dict(self):
        '''Generates package dicts from the package data records.'''
        for row_dict in self._package_data_records.records:
            try:
                yield self.record_2_package(row_dict)
            except RowParseError, e:
                print 'Error with row', e
        raise StopIteration

    @classmethod
    def license_2_license_id(cls, license_title, logger=None):
        licenses = LicenseRegister()
        license_obj = licenses.get_by_title(license_title)
        if license_obj:
            return u'%s' % license_obj.id
        else:
            logger('Warning: No license name matches \'%s\'. Ignoring license.' % license_title)


    @classmethod
    def munge(cls, name):
        '''Munge a title into a name.

        Note this function must be only carefully changed, as reimporting
        data with a name munged differently may create duplicates packages.
        For this reason, this munge function is for use by the importers only.
        Other users should use the API slug creation functionality.
        '''
        # convert spaces to underscores
        name = re.sub(' ', '_', name).lower()        
        # convert symbols to dashes
        name = re.sub('[:]', '_-', name).lower()        
        name = re.sub('[/]', '-', name).lower()        
        # take out not-allowed characters
        name = re.sub('[^a-zA-Z0-9-_]', '', name).lower()
        # remove double underscores
        name = re.sub('__', '_', name).lower()
        # if longer than max_length, keep last word if a year
        max_length = model.PACKAGE_NAME_MAX_LENGTH - 5
        # (make length less than max, in case we need a few for '_' chars
        # to de-clash names.)
        if len(name) > max_length:
            year_match = re.match('.*?[_-]((?:\d{2,4}[-/])?\d{2,4})$', name)
            if year_match:
                year = year_match.groups()[0]
                name = '%s-%s' % (name[:(max_length-len(year)-1)], year)
            else:
                name = name[:max_length]
        return name

    @classmethod
    def name_munge(cls, input_name):
        '''Munges the name field in case it is not to spec.

        Note this function must be only carefully changed, as reimporting
        data with a name munged differently may create duplicates packages.
        For this reason, this munge function is for use by the importers only.
        Other users should use the API slug creation functionality.
        '''
        return cls.munge(input_name.replace(' ', '').replace('.', '_').replace('&', 'and'))

    @classmethod
    def tidy_url(cls, url, logger=None):
        if url and not url.startswith('http') and not url.startswith('webcal:'):
            if url.startswith('www.'):
                url = url.replace('www.', 'http://www.')
            else:
                logger('Warning: URL doesn\'t start with http: %s' % url)
        return url


