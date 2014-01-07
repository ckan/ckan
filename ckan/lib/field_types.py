import re
import time
import datetime
import warnings

with warnings.catch_warnings():
    warnings.filterwarnings('ignore', '.*compile_mappers.*')
    import formalchemy

from ckan.common import OrderedDict

months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

class DateConvertError(Exception):
    pass

class DateType(object):
    '''Utils for handling dates in forms.
    * Full or partial dates
    * User inputs in form DD/MM/YYYY and it is stored in db as YYYY-MM-DD.
    '''
    format_types = ('form', 'db')
    datetime_fields = OrderedDict([('year', (1000, 2100, 4, 'YYYY')),
                                   ('month', (1, 12, 2, 'MM')),
                                   ('day', (1, 31, 2, 'DD')),
                                   ('hour', (0, 23, 2, 'HH')),
                                   ('minute', (0, 59, 2, 'MM')),
                                   ])
    datetime_fields_indexes = {'min':0, 'max':1, 'digits':2, 'format_code':3}
    date_fields_order = {'db':('year', 'month', 'day'),
                         'form':('day', 'month', 'year')}
    parsing_separators = {'date':'-/',
                          'time':':\.'}
    default_separators = {'db':{'date':'-',
                                'time':':'},
                          'form':{'date':'/',
                                  'time':':'},}
    field_code_map = {'year':'YYYY', 'month':'MM', 'day':'DD',
                      'hour':'HH', 'minute':'MM'}
    word_match = re.compile('[A-Za-z]+')
    timezone_match = re.compile('(\s[A-Z]{3})|(\s[+-]\d\d:?\d\d)')
    months_abbreviated = [month[:3] for month in months]

    @classmethod
    def parse_timedate(cls, timedate_str, format_type):
        '''Takes a timedate and returns a dictionary of the fields.
        * Little validation is done.
        * If it can\'t understand the layout it raises DateConvertError
        '''
        assert format_type in cls.format_types
        if not hasattr(cls, 'matchers'):
            # build up a list of re matches for the different
            # acceptable ways of expressing the time and date
            cls.matchers = {}
            cls.readable_formats = {}
            for format_type_ in cls.format_types:
                finished_regexps = []
                readable_formats = [] # analogous to the regexps,
                                      # but human readable
                year_re = '(?P<%s>\d{2,4})'
                month_re = '(?P<%s>\w+)'
                two_digit_decimal_re = '(?P<%s>\d{1,2})'
                time_re = '%s[%s]%s' % (
                    two_digit_decimal_re % 'hour',
                    cls.parsing_separators['time'],
                    two_digit_decimal_re % 'minute')
                time_readable = '%s%s%s' % (
                    cls.datetime_fields['hour'][cls.datetime_fields_indexes['format_code']],
                    cls.default_separators[format_type_]['time'],
                    cls.datetime_fields['minute'][cls.datetime_fields_indexes['format_code']])
                date_field_re = {'year':year_re % 'year',
                                 'month':month_re % 'month',
                                 'day':two_digit_decimal_re % 'day'}
                date_fields = list(cls.date_fields_order[format_type_])
                for how_specific in ('day', 'month', 'year'):
                    date_sep_re = '[%s]' % cls.parsing_separators['date']
                    date_sep_readable = cls.default_separators[format_type_]['date']
                    date_field_regexps = [date_field_re[field] for field in date_fields]
                    date_field_readable = [cls.datetime_fields[field][cls.datetime_fields_indexes['format_code']] for field in date_fields]
                    date_re = date_sep_re.join(date_field_regexps)
                    date_readable = date_sep_readable.join(date_field_readable)
                    finished_regexps.append(date_re)
                    readable_formats.append(date_readable)
                    date_fields.remove(how_specific)
                full_date_re = finished_regexps[0]
                full_date_readable = readable_formats[0]
                # Allow time to be before or after the date
                for format_ in ('%(time_re)s%(sep)s%(full_date_re)s',
                                '%(full_date_re)s%(sep)s%(time_re)s'):
                    finished_regexps.insert(0, format_ % {
                        'time_re':time_re,
                        'sep':'\s',
                        'full_date_re':full_date_re})
                    readable_formats.insert(0, format_ % {
                        'time_re':time_readable,
                        'sep':' ',
                        'full_date_re':full_date_readable})
                cls.matchers[format_type_] = [re.compile('^%s$' % regexp) for regexp in finished_regexps]
                cls.readable_formats[format_type_] = readable_formats
                #print format_type_, finished_regexps, readable_formats
        for index, matcher in enumerate(cls.matchers[format_type]):
            match = matcher.match(timedate_str)
            if match:
                timedate_dict = match.groupdict()
                timedate_dict = cls.int_timedate(timedate_dict)
                timedate_dict['readable_format'] = cls.readable_formats[format_type][index]
                return timedate_dict
        else:
            acceptable_formats = ', '.join(["'%s'" % format_ for format_ in cls.readable_formats[format_type]])
            raise DateConvertError("Cannot parse %s date '%s'. Acceptable formats: %s" % (format_type, timedate_str, acceptable_formats))

    @classmethod
    def int_timedate(cls, timedate_dict):
        # Convert timedate string values to integers
        int_timedate_dict = timedate_dict.copy()
        for field in cls.datetime_fields.keys():
            if timedate_dict.has_key(field):
                val = timedate_dict[field]
                if field == 'year':
                    if len(val) == 2:
                        # Deal with 2 digit dates
                        try:
                            int_val = int(val)
                        except ValueError:
                            raise DateConvertError('Expecting integer for %s value: %s' % (field, val))
                        val = cls.add_centurys_to_two_digit_year(int_val)
                    elif len(val) == 3:
                        raise DateConvertError('Expecting 2 or 4 digit year: "%s"' % (val))
                if field == 'month':
                    # Deal with months expressed as words
                    if val in months:
                        val = months.index(val) + 1
                    if val in cls.months_abbreviated:
                        val = cls.months_abbreviated.index(val) + 1
                try:
                    int_timedate_dict[field] = int(val)
                except ValueError:
                    raise DateConvertError('Expecting integer for %s value: %s' % (field, val))
        return int_timedate_dict

    @classmethod
    def iso_to_db(cls, iso_date, format):
        # e.g. 'Wed, 06 Jan 2010 09:30:00'
        #      '%a, %d %b %Y %H:%M:%S'
        assert isinstance(iso_date, (unicode, str))
        try:
            date_tuple = time.strptime(iso_date, format)
        except ValueError, e:
            raise DateConvertError('Could not read date as ISO format "%s". Date provided: "%s"' % (format, iso_date))
        date_obj = datetime.datetime(*date_tuple[:4])
        date_str = cls.date_to_db(date_obj)
        return date_str

    @classmethod
    def strip_iso_timezone(cls, iso_date):
        return cls.timezone_match.sub('', iso_date)

    @classmethod
    def form_to_db(cls, form_str, may_except=True):
        '''
        27/2/2005 -> 2005-02-27
        27/Feb/2005 -> 2005-02-27
        2/2005 -> 2005-02
        Feb/2005 -> 2005-02
        2005 -> 2005
        '''
        try:
            # Allow blank input or None
            if not form_str:
                return u''
            form_str = form_str.strip()
            if not form_str:
                return u''

            # Parse form value
            timedate_dict = cls.parse_timedate(form_str, 'form')
                    
            # Check range of dates and format as standard string
            try:
                db_datetime = cls.format(timedate_dict, 'db')
            except DateConvertError, e:
                msg = 'Date error reading in format \'%s\': %s' % (timedate_dict['readable_format'], ' '.join(e.args))
                raise DateConvertError(msg)
            return db_datetime

        except DateConvertError, e:
            if may_except:
                raise e
            else:
                return form_str

    @classmethod
    def date_to_db(cls, date):
        '''
        datetime.date(2005, 2, 27) -> 2005-02-27
        '''
        assert isinstance(date, datetime.date)
        date_str = date.strftime('%Y-%m-%d')
        return date_str

    @classmethod
    def format(cls, datetime_dict, format_type):
        '''Takes datetime_dict and formats them either for
        the form or the database. If it encounters an out
        of range value, it raises an exception.
        '''
        assert isinstance(datetime_dict, dict)
        assert format_type in ('form', 'db')

        # convert each field to a string
        str_datetime_dict = {} # strings by field
        for field in cls.datetime_fields:
            if not datetime_dict.has_key(field):
                break
            val = datetime_dict[field]
            min_, max_ = cls.datetime_fields[field][cls.datetime_fields_indexes['min']:cls.datetime_fields_indexes['max'] + 1]
            if val < min_ or val > max_:
                raise DateConvertError('%s value of "%s" is out of range.' % (field.capitalize(), val))
            if format_type == 'form':
                int_format_string = '%d'
            elif format_type == 'db':
                num_digits = cls.datetime_fields['hour'][cls.datetime_fields_indexes['digits']]
                int_format_string = '%%0%sd' % num_digits                
            str_datetime_dict[field] = int_format_string % val

        # assemble the date
        date_fields = []
        for field in cls.date_fields_order[format_type]:
            if str_datetime_dict.has_key(field):
                date_fields.append(str_datetime_dict[field])
        formatted_datetime = unicode(cls.default_separators[format_type]['date'].join(date_fields))

        # add in the time if specified
        if str_datetime_dict.has_key('hour'):
            if format_type == 'form':
                datetime_format_string = '%(hour)s%(time_separator)s%(minute)s %(date)s'
            elif format_type == 'db':
                datetime_format_string = '%(date)s %(hour)s%(time_separator)s%(minute)s'
            format_dict = str_datetime_dict.copy()
            format_dict['date'] = formatted_datetime
            format_dict['time_separator'] = cls.default_separators[format_type]['time']
            formatted_datetime = datetime_format_string % format_dict
        return formatted_datetime

    @staticmethod
    def form_validator(form_date_str, field=None):
        try:
            DateType.form_to_db(form_date_str)
        except DateConvertError, e:
            raise formalchemy.ValidationError(e)

    @classmethod
    def db_to_form(cls, db_str):
        '2005-02-27 -> 27/2/2005 if correct format, otherwise, display as is.'
        db_str = db_str.strip()
        if not db_str:
            return db_str
        try:
            timedate_dict = cls.parse_timedate(db_str, 'db')
        except DateConvertError, e:
            # cannot parse - simply display as-is
            return db_str
        try:
            datetime_form = cls.format(timedate_dict, 'form')
        except DateConvertError, e:
            # values out of range - simply display as-is
            return db_str
        return datetime_form

    @classmethod
    def add_centurys_to_two_digit_year(cls, year, near_year=2010):
        assert isinstance(year, int)
        assert isinstance(near_year, int)
        assert year < 1000, repr(year)
        assert near_year > 1000 and near_year < 2200, repr(near_year)
        year += 1000
        while abs(year - near_year) > 50:
            year += 100
        return year
