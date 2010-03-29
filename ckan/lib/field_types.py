import re
import time
import datetime

months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

class DateType(object):
    '''Utils for handling dates in forms.
    * Full or partial dates
    * User inputs in form DD/MM/YYYY and it is stored in db as YYYY-MM-DD.
    '''
    date_match = re.compile('(\w+)([/\-.]\w+)?([/\-.]\w+)?')
    default_db_separator = '-'
    default_form_separator = '/'
    word_match = re.compile('[A-Za-z]+')
    months_chopped = [month[:3] for month in months]

    @classmethod
    def iso_to_db(self, iso_date, format):
        # e.g. 'Wed, 06 Jan 2010 09:30:00 GMT'
        #      '%a, %d %b %Y %H:%M:%S %Z'
        assert isinstance(iso_date, (unicode, str))
        try:
            date_tuple = time.strptime(iso_date, format)
        except ValueError, e:
            raise TypeError('Could not read date as ISO format "%s". Date provided: "%s"' % (format, iso_date))
        date_obj = datetime.datetime(*date_tuple[:4])
        date_str = date_obj.strftime('%Y-%m-%d')
        return date_str

    @classmethod
    def form_to_db(self, form_str):
        '''
        27/2/2005 -> 2005-02-27
        27/Feb/2005 -> 2005-02-27
        2/2005 -> 2005-02
        Feb/2005 -> 2005-02
        2005 -> 2005
        '''
        if not form_str:
            # Allow blank
            return u''
        err_str = 'Date must be format DD/MM/YYYY or DD/MM/YY.'
        match = self.date_match.match(form_str)
        if not match:
            raise TypeError('%s Date provided: "%s"' % (err_str, form_str))
        matched_date = ''.join([group if group else '' for group in match.groups()])
        if matched_date != form_str:
            raise TypeError('%s Matched only "%s"' % (err_str, matched_date))
        standard_date_fields = [] # integers, year first
        for match_group in match.groups()[::-1]:
            if match_group is not None:
                val = match_group.strip('/-.')
                word_in_val = self.word_match.match(val)
                if word_in_val:
                    word_in_val_c = word_in_val.group().capitalize()
                    month_i = None
                    if word_in_val_c in months:
                        month_i = months.index(word_in_val_c)
                    elif word_in_val_c in self.months_chopped:
                        month_i = self.months_chopped.index(word_in_val_c)
                    if month_i is not None:
                        val = val.replace(word_in_val.group(), str(month_i+1))
                try:
                    standard_date_fields.append(int(val))
                except ValueError:
                    raise TypeError('%s Date provided: "%s"' % (err_str, form_str))
        # Deal with 2 digit dates
        if standard_date_fields[0] < 100:
            standard_date_fields[0] = self.add_centurys_to_two_digit_year(standard_date_fields[0])
        # Check range of dates
        if standard_date_fields[0] < 1000 or standard_date_fields[0] > 2100:
            raise TypeError('%s Year of "%s" is outside range.' % (err_str, standard_date_fields[0]))
        if len(standard_date_fields) > 1 and (standard_date_fields[1] > 12 or standard_date_fields[1] < 1):
            raise TypeError('%s Month of "%s" is outside range.' % (err_str, standard_date_fields[0]))
        if len(standard_date_fields) > 2 and (standard_date_fields[2] > 31 or standard_date_fields[2] < 1):
            raise TypeError('%s Month of "%s" is outside range.' % (err_str, standard_date_fields[0]))
        str_date_fields = [] # strings, year first
        for i, digits in enumerate((4, 2, 2)):
            if len(standard_date_fields) > i:
                format_string = '%%0%sd' % digits
                str_date_fields.append(format_string % standard_date_fields[i])
        db_date = unicode(self.default_db_separator.join(str_date_fields))
        return db_date

    @staticmethod
    def form_validator(form_date_str, field=None):
        try:
            DateType.form_to_db(form_date_str)
        except TypeError, e:
            return e

    @classmethod
    def db_to_form(self, db_str):
        '2005-02-27 -> 27/2/2005 if correct format, otherwise, display as is.'
        if not db_str.strip():
            return db_str
        match = self.date_match.match(db_str)
        if not match:
            return db_str
        matched_date = ''.join([group if group else '' for group in match.groups()])
        if matched_date != db_str.strip():
            return db_str
        standard_date_fields = [] # integers, year first
        for match_group in match.groups():
            if match_group is not None:
                try:
                    standard_date_fields.append(int(match_group.strip('/-.')))
                except ValueError:
                    return db_str
        if standard_date_fields[0] < 1000 or standard_date_fields[0] > 2100:
            return db_str
        if len(standard_date_fields) > 1 and (standard_date_fields[1] > 12 or standard_date_fields[1] < 1):
            return db_str
        if len(standard_date_fields) > 2 and (standard_date_fields[2] > 31 or standard_date_fields[2] < 1):
            return db_str
        str_date_fields = [str(field) for field in standard_date_fields]
        form_date = unicode(self.default_form_separator.join(str_date_fields[::-1]))
        return form_date

    @classmethod
    def add_centurys_to_two_digit_year(self, year, near_year=2010):
        assert isinstance(year, int)
        assert isinstance(near_year, int)
        assert year < 1000, repr(year)
        assert near_year > 1000 and near_year < 2200, repr(near_year)
        year += 1000
        while abs(year - near_year) > 50:
            year += 100
        return year
