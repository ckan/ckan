"""
Country specific validators for use with FormEncode.
"""
import re

from .api import FancyValidator
from .compound import Any
from .validators import Regex, Invalid, _

try:
    import pycountry
except ImportError:
    pycountry = None
try:
    from turbogears.i18n import format as tgformat
except ImportError:
    tgformat = None

if pycountry or tgformat:
    no_country = False
else:
    import warnings
    no_country = ('Please easy_install pycountry or validators handling'
                  ' country names and/or languages will not work.')

############################################################
## country lists and functions
############################################################

country_additions = [
    ('BY', _('Belarus')),
    ('ME', _('Montenegro')),
    ('AU', _('Tasmania')),
]

fuzzy_countrynames = [
    ('US', 'U.S.A'),
    ('US', 'USA'),
    ('GB', _('Britain')),
    ('GB', _('Great Britain')),
    ('CI', _('Cote de Ivoire')),
]

if tgformat:

    def get_countries():
        c1 = tgformat.get_countries('en')
        c2 = tgformat.get_countries()
        if len(c1) > len(c2):
            d = dict(country_additions)
            d.update(dict(c1))
            d.update(dict(c2))
        else:
            d = dict(country_additions)
            d.update(dict(c2))
        ret = d.items() + fuzzy_countrynames
        return ret

    def get_country(code):
        return dict(get_countries())[code]

    def get_languages():
        c1 = tgformat.get_languages('en')
        c2 = tgformat.get_languages()
        if len(c1) > len(c2):
            d = dict(c1)
            d.update(dict(c2))
            return d.items()
        else:
            return c2

    def get_language(code):
        try:
            return tgformat.get_language(code)
        except KeyError:
            return tgformat.get_language(code, 'en')

elif pycountry:

    # @@ mark: interestingly, common gettext notation does not work here
    import gettext
    gettext.bindtextdomain('iso3166', pycountry.LOCALES_DIR)
    _c = lambda t: gettext.dgettext('iso3166', t)
    gettext.bindtextdomain('iso639', pycountry.LOCALES_DIR)
    _l = lambda t: gettext.dgettext('iso639', t)

    def get_countries():
        c1 = set([(e.alpha2, _c(e.name)) for e in pycountry.countries])
        ret = c1.union(country_additions + fuzzy_countrynames)
        return ret

    def get_country(code):
        return _c(pycountry.countries.get(alpha2=code).name)

    def get_languages():
        return [(e.alpha2, _l(e.name)) for e in pycountry.languages
            if e.name and getattr(e, 'alpha2', None)]

    def get_language(code):
        return _l(pycountry.languages.get(alpha2=code).name)


############################################################
## country, state and postal code validators
############################################################

class DelimitedDigitsPostalCode(Regex):
    """
    Abstraction of common postal code formats, such as 55555, 55-555 etc.
    With constant amount of digits. By providing a single digit as partition
    you can obtain a trivial 'x digits' postal code validator.

    ::

        >>> german = DelimitedDigitsPostalCode(5)
        >>> german.to_python('55555')
        '55555'
        >>> german.to_python('5555')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a zip code (5 digits)
        >>> polish = DelimitedDigitsPostalCode([2, 3], '-')
        >>> polish.to_python('55555')
        '55-555'
        >>> polish.to_python('55-555')
        '55-555'
        >>> polish.to_python('5555')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a zip code (nn-nnn)
        >>> nicaragua = DelimitedDigitsPostalCode([3, 3, 1], '-')
        >>> nicaragua.to_python('5554443')
        '555-444-3'
        >>> nicaragua.to_python('555-4443')
        '555-444-3'
        >>> nicaragua.to_python('5555')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a zip code (nnn-nnn-n)
    """

    strip = True

    def assembly_formatstring(self, partition_lengths, delimiter):
        if len(partition_lengths) == 1:
            return _('%d digits') % partition_lengths[0]
        else:
            return delimiter.join('n' * l for l in partition_lengths)

    def assembly_regex(self, partition_lengths, delimiter):
        mg = [r'(\d{%d})' % l for l in partition_lengths]
        rd = r'\%s?' % delimiter
        return rd.join(mg)

    def __init__(self, partition_lengths, delimiter=None,
                 *args, **kw):
        if isinstance(partition_lengths, (int, long)):
            partition_lengths = [partition_lengths]
        if not delimiter:
            delimiter = ''
        self.format = self.assembly_formatstring(partition_lengths, delimiter)
        self.regex = self.assembly_regex(partition_lengths, delimiter)
        self.partition_lengths, self.delimiter = partition_lengths, delimiter
        Regex.__init__(self, *args, **kw)

    messages = dict(
        invalid=_('Please enter a zip code (%(format)s)'))

    def _convert_to_python(self, value, state):
        self.assert_string(value, state)
        match = self.regex.search(value)
        if not match:
            raise Invalid(
                self.message('invalid', state, format=self.format),
                value, state)
        return self.delimiter.join(match.groups())


def USPostalCode(*args, **kw):
    """
    US Postal codes (aka Zip Codes).

    ::

        >>> uspc = USPostalCode()
        >>> uspc.to_python('55555')
        '55555'
        >>> uspc.to_python('55555-5555')
        '55555-5555'
        >>> uspc.to_python('5555')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a zip code (5 digits)
    """
    return Any(DelimitedDigitsPostalCode(5, None, *args, **kw),
               DelimitedDigitsPostalCode([5, 4], '-', *args, **kw))


def GermanPostalCode(*args, **kw):
    return DelimitedDigitsPostalCode(5, None, *args, **kw)


def FourDigitsPostalCode(*args, **kw):
    return DelimitedDigitsPostalCode(4, None, *args, **kw)


def PolishPostalCode(*args, **kw):
    return DelimitedDigitsPostalCode([2, 3], '-', *args, **kw)


class ArgentinianPostalCode(Regex):
    """
    Argentinian Postal codes.

    ::

        >>> ArgentinianPostalCode.to_python('C1070AAM')
        'C1070AAM'
        >>> ArgentinianPostalCode.to_python('c 1070 aam')
        'C1070AAM'
        >>> ArgentinianPostalCode.to_python('5555')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a zip code (LnnnnLLL)
    """

    format = _('LnnnnLLL')
    regex = re.compile(r'^([a-zA-Z]{1})\s*(\d{4})\s*([a-zA-Z]{3})$')
    strip = True

    messages = dict(
        invalid=_('Please enter a zip code (%(format)s)'))

    def _convert_to_python(self, value, state):
        self.assert_string(value, state)
        match = self.regex.search(value)
        if not match:
            raise Invalid(
                self.message('invalid', state, format=self.format),
                value, state)
        return '%s%s%s' % (match.group(1).upper(),
                           match.group(2),
                           match.group(3).upper())


class CanadianPostalCode(Regex):
    """
    Canadian Postal codes.

    ::

        >>> CanadianPostalCode.to_python('V3H 1Z7')
        'V3H 1Z7'
        >>> CanadianPostalCode.to_python('v3h1z7')
        'V3H 1Z7'
        >>> CanadianPostalCode.to_python('5555')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a zip code (LnL nLn)
    """

    format = _('LnL nLn')
    regex = re.compile(r'^([a-zA-Z]\d[a-zA-Z])\s?(\d[a-zA-Z]\d)$')
    strip = True

    messages = dict(
        invalid=_('Please enter a zip code (%(format)s)'))

    def _convert_to_python(self, value, state):
        self.assert_string(value, state)
        match = self.regex.search(value)
        if not match:
            raise Invalid(
                self.message('invalid', state, format=self.format),
                value, state)
        return '%s %s' % (match.group(1).upper(), match.group(2).upper())


class UKPostalCode(Regex):
    """
    UK Postal codes. Please see BS 7666.

    ::

        >>> UKPostalCode.to_python('BFPO 3')
        'BFPO 3'
        >>> UKPostalCode.to_python('LE11 3GR')
        'LE11 3GR'
        >>> UKPostalCode.to_python('l1a 3gr')
        'L1A 3GR'
        >>> UKPostalCode.to_python('5555')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a valid postal code (for format see BS 7666)
    """

    regex = re.compile(r'^((ASCN|BBND|BIQQ|FIQQ|PCRN|SIQQ|STHL|TDCU|TKCA)'
        ' 1ZZ|BFPO (c\/o )?[1-9]{1,4}|GIR 0AA|[A-PR-UWYZ]'
        '([0-9]{1,2}|([A-HK-Y][0-9]|[A-HK-Y][0-9]([0-9]|[ABEHMNPRV-Y]))'
        '|[0-9][A-HJKS-UW]) [0-9][ABD-HJLNP-UW-Z]{2})$', re.I)
    strip = True

    messages = dict(
        invalid=_('Please enter a valid postal code (for format see BS 7666)'))

    def _convert_to_python(self, value, state):
        self.assert_string(value, state)
        match = self.regex.search(value)
        if not match:
            raise Invalid(
                self.message('invalid', state),
                value, state)
        return match.group(1).upper()


class CountryValidator(FancyValidator):
    """
    Will convert a country's name into its ISO-3166 abbreviation for unified
    storage in databases etc. and return a localized country name in the
    reverse step.

    @See http://www.iso.org/iso/country_codes/iso_3166_code_lists.htm

    ::

        >>> CountryValidator.to_python('Germany')
        u'DE'
        >>> CountryValidator.to_python('Finland')
        u'FI'
        >>> CountryValidator.to_python('UNITED STATES')
        u'US'
        >>> CountryValidator.to_python('Krakovia')
        Traceback (most recent call last):
            ...
        Invalid: That country is not listed in ISO 3166
        >>> CountryValidator.from_python('DE')
        u'Germany'
        >>> CountryValidator.from_python('FI')
        u'Finland'
    """

    key_ok = True

    messages = dict(
        valueNotFound=_('That country is not listed in ISO 3166'))

    def __init__(self, *args, **kw):
        FancyValidator.__init__(self, *args, **kw)
        if no_country:
            warnings.warn(no_country, Warning, 2)

    def _convert_to_python(self, value, state):
        upval = value.upper()
        if self.key_ok:
            try:
                get_country(upval)
            except Exception:
                pass
            else:
                return upval
        for k, v in get_countries():
            if v.upper() == upval:
                return k
        raise Invalid(self.message('valueNotFound', state), value, state)

    def _convert_from_python(self, value, state):
        try:
            return get_country(value.upper())
        except KeyError:
            return value


class PostalCodeInCountryFormat(FancyValidator):
    """
    Makes sure the postal code is in the country's format by chosing postal
    code validator by provided country code. Does convert it into the preferred
    format, too.

    ::

        >>> fs = PostalCodeInCountryFormat('country', 'zip')
        >>> sorted(fs.to_python(dict(country='DE', zip='30167')).items())
        [('country', 'DE'), ('zip', '30167')]
        >>> fs.to_python(dict(country='DE', zip='3008'))
        Traceback (most recent call last):
            ...
        Invalid: Given postal code does not match the country's format.
        >>> sorted(fs.to_python(dict(country='PL', zip='34343')).items())
        [('country', 'PL'), ('zip', '34-343')]
        >>> fs = PostalCodeInCountryFormat('staat', 'plz')
        >>> sorted(fs.to_python(dict(staat='GB', plz='l1a 3gr')).items())
        [('plz', 'L1A 3GR'), ('staat', 'GB')]
    """

    country_field = 'country'
    zip_field = 'zip'

    __unpackargs__ = ('country_field', 'zip_field')

    messages = dict(
        badFormat=_("Given postal code does not match the country's format."))

    _vd = {
        'AR': ArgentinianPostalCode,
        'AT': FourDigitsPostalCode,
        'BE': FourDigitsPostalCode,
        'BG': FourDigitsPostalCode,
        'CA': CanadianPostalCode,
        'CL': lambda: DelimitedDigitsPostalCode(7),
        'CN': lambda: DelimitedDigitsPostalCode(6),
        'CR': FourDigitsPostalCode,
        'DE': GermanPostalCode,
        'DK': FourDigitsPostalCode,
        'DO': lambda: DelimitedDigitsPostalCode(5),
        'ES': lambda: DelimitedDigitsPostalCode(5),
        'FI': lambda: DelimitedDigitsPostalCode(5),
        'FR': lambda: DelimitedDigitsPostalCode(5),
        'GB': UKPostalCode,
        'GF': lambda: DelimitedDigitsPostalCode(5),
        'GR': lambda: DelimitedDigitsPostalCode([2, 3], ' '),
        'HN': lambda: DelimitedDigitsPostalCode(5),
        'HT': FourDigitsPostalCode,
        'HU': FourDigitsPostalCode,
        'IS': lambda: DelimitedDigitsPostalCode(3),
        'IT': lambda: DelimitedDigitsPostalCode(5),
        'JP': lambda: DelimitedDigitsPostalCode([3, 4], '-'),
        'KR': lambda: DelimitedDigitsPostalCode([3, 3], '-'),
        'LI': FourDigitsPostalCode,
        'LU': FourDigitsPostalCode,
        'MC': lambda: DelimitedDigitsPostalCode(5),
        'NI': lambda: DelimitedDigitsPostalCode([3, 3, 1], '-'),
        'NO': FourDigitsPostalCode,
        'PL': PolishPostalCode,
        'PT': lambda: DelimitedDigitsPostalCode([4, 3], '-'),
        'PY': FourDigitsPostalCode,
        'RO': lambda: DelimitedDigitsPostalCode(6),
        'SE': lambda: DelimitedDigitsPostalCode([3, 2], ' '),
        'SG': lambda: DelimitedDigitsPostalCode(6),
        'US': USPostalCode,
        'UY': lambda: DelimitedDigitsPostalCode(5),
    }

    def _validate_python(self, fields_dict, state):
        if fields_dict[self.country_field] in self._vd:
            zip_validator = self._vd[fields_dict[self.country_field]]()
            try:
                fields_dict[self.zip_field] = zip_validator.to_python(
                    fields_dict[self.zip_field], state=state)
            except Invalid as e:
                message = self.message('badFormat', state)
                raise Invalid(message, fields_dict, state,
                    error_dict={self.zip_field: e.msg,
                        self.country_field: message})


class USStateProvince(FancyValidator):
    """
    Valid state or province code (two-letter).

    Well, for now I don't know the province codes, but it does state
    codes.  Give your own `states` list to validate other state-like
    codes; give `extra_states` to add values without losing the
    current state values.

    ::

        >>> s = USStateProvince('XX')
        >>> s.to_python('IL')
        'IL'
        >>> s.to_python('XX')
        'XX'
        >>> s.to_python('xx')
        'XX'
        >>> s.to_python('YY')
        Traceback (most recent call last):
            ...
        Invalid: That is not a valid state code
    """

    states = ['AK', 'AL', 'AR', 'AZ', 'CA', 'CO', 'CT', 'DC', 'DE',
              'FL', 'GA', 'HI', 'IA', 'ID', 'IN', 'IL', 'KS', 'KY',
              'LA', 'MA', 'MD', 'ME', 'MI', 'MN', 'MO', 'MS', 'MT',
              'NC', 'ND', 'NE', 'NH', 'NJ', 'NM', 'NV', 'NY', 'OH',
              'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT',
              'VA', 'VT', 'WA', 'WI', 'WV', 'WY']

    extra_states = []

    __unpackargs__ = ('extra_states',)

    messages = dict(
        empty=_('Please enter a state code'),
        wrongLength=_('Please enter a state code with TWO letters'),
        invalid=_('That is not a valid state code'))

    def _validate_python(self, value, state):
        value = str(value).strip().upper()
        if not value:
            raise Invalid(
                self.message('empty', state),
                value, state)
        if not value or len(value) != 2:
            raise Invalid(
                self.message('wrongLength', state),
                value, state)
        if value not in self.states and not (
                self.extra_states and value in self.extra_states):
            raise Invalid(
                self.message('invalid', state),
                value, state)

    def _convert_to_python(self, value, state):
        return str(value).strip().upper()


############################################################
## phone number validators
############################################################

class USPhoneNumber(FancyValidator):
    """
    Validates, and converts to ###-###-####, optionally with extension
    (as ext.##...).  Only support US phone numbers.  See
    InternationalPhoneNumber for support for that kind of phone number.

    ::

        >>> p = USPhoneNumber()
        >>> p.to_python('333-3333')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a number, with area code, in the form ###-###-####, optionally with "ext.####"
        >>> p.to_python('555-555-5555')
        '555-555-5555'
        >>> p.to_python('1-393-555-3939')
        '1-393-555-3939'
        >>> p.to_python('321.555.4949')
        '321.555.4949'
        >>> p.to_python('3335550000')
        '3335550000'
    """
    # for emacs: "

    _phoneRE = re.compile(r'^\s*(?:1-)?(\d\d\d)[\- \.]?(\d\d\d)[\- \.]?'
        '(\d\d\d\d)(?:\s*ext\.?\s*(\d+))?\s*$', re.I)

    messages = dict(
        phoneFormat=_('Please enter a number, with area code,'
            ' in the form ###-###-####, optionally with "ext.####"'))

    def _convert_to_python(self, value, state):
        self.assert_string(value, state)
        match = self._phoneRE.search(value)
        if not match:
            raise Invalid(
                self.message('phoneFormat', state),
                value, state)
        return value

    def _convert_from_python(self, value, state):
        self.assert_string(value, state)
        match = self._phoneRE.search(value)
        if not match:
            raise Invalid(self.message('phoneFormat', state),
                          value, state)
        result = '%s-%s-%s' % (match.group(1), match.group(2), match.group(3))
        if match.group(4):
            result += " ext.%s" % match.group(4)
        return result


class InternationalPhoneNumber(FancyValidator):
    """
    Validates, and converts phone numbers to +##-###-#######.
    Adapted from RFC 3966

    @param  default_cc      country code for prepending if none is provided
                            can be a paramerless callable

    ::

        >>> c = InternationalPhoneNumber(default_cc=lambda: 49)
        >>> c.to_python('0555/8114100')
        '+49-555-8114100'
        >>> p = InternationalPhoneNumber(default_cc=49)
        >>> p.to_python('333-3333')
        Traceback (most recent call last):
            ...
        Invalid: Please enter a number, with area code, in the form +##-###-#######.
        >>> p.to_python('0555/4860-300')
        '+49-555-4860-300'
        >>> p.to_python('0555-49924-51')
        '+49-555-49924-51'
        >>> p.to_python('0555 / 8114100')
        '+49-555-8114100'
        >>> p.to_python('0555/8114100')
        '+49-555-8114100'
        >>> p.to_python('0555 8114100')
        '+49-555-8114100'
        >>> p.to_python(' +49 (0)555 350 60 0')
        '+49-555-35060-0'
        >>> p.to_python('+49 555 350600')
        '+49-555-350600'
        >>> p.to_python('0049/ 555/ 871 82 96')
        '+49-555-87182-96'
        >>> p.to_python('0555-2 50-30')
        '+49-555-250-30'
        >>> p.to_python('0555 43-1200')
        '+49-555-43-1200'
        >>> p.to_python('(05 55)4 94 33 47')
        '+49-555-49433-47'
        >>> p.to_python('(00 48-555)2 31 72 41')
        '+48-555-23172-41'
        >>> p.to_python('+973-555431')
        '+973-555431'
        >>> p.to_python('1-393-555-3939')
        '+1-393-555-3939'
        >>> p.to_python('+43 (1) 55528/0')
        '+43-1-55528-0'
        >>> p.to_python('+43 5555 429 62-0')
        '+43-5555-42962-0'
        >>> p.to_python('00 218 55 33 50 317 321')
        '+218-55-3350317-321'
        >>> p.to_python('+218 (0)55-3636639/38')
        '+218-55-3636639-38'
        >>> p.to_python('032 555555 367')
        '+49-32-555555-367'
        >>> p.to_python('(+86) 555 3876693')
        '+86-555-3876693'
    """

    strip = True
    # Use if there's a default country code you want to use:
    default_cc = None
    _mark_chars_re = re.compile(r"[_.!~*'/]")
    _preTransformations = [
        (re.compile(r'^(\(?)(?:00\s*)(.+)$'), '%s+%s'),
        (re.compile(r'^\(\s*(\+?\d+)\s*(\d+)\s*\)(.+)$'), '(%s%s)%s'),
        (re.compile(r'^\((\+?[-\d]+)\)\s?(\d.+)$'), '%s-%s'),
        (re.compile(r'^(?:1-)(\d+.+)$'), '+1-%s'),
        (re.compile(r'^(\+\d+)\s+\(0\)\s*(\d+.+)$'), '%s-%s'),
        (re.compile(r'^([0+]\d+)[-\s](\d+)$'), '%s-%s'),
        (re.compile(r'^([0+]\d+)[-\s](\d+)[-\s](\d+)$'), '%s-%s-%s'),
        ]
    _ccIncluder = [
        (re.compile(r'^\(?0([1-9]\d*)[-)](\d.*)$'), '+%d-%s-%s'),
        ]
    _postTransformations = [
        (re.compile(r'^(\+\d+)[-\s]\(?(\d+)\)?[-\s](\d+.+)$'), '%s-%s-%s'),
        (re.compile(r'^(.+)\s(\d+)$'), '%s-%s'),
        ]
    _phoneIsSane = re.compile(r'^(\+[1-9]\d*)-([\d\-]+)$')

    messages = dict(
        phoneFormat=_('Please enter a number, with area code,'
            ' in the form +##-###-#######.'))

    def _perform_rex_transformation(self, value, transformations):
        for rex, trf in transformations:
            match = rex.search(value)
            if match:
                value = trf % match.groups()
        return value

    def _prepend_country_code(self, value, transformations, country_code):
        for rex, trf in transformations:
            match = rex.search(value)
            if match:
                return trf % ((country_code,) + match.groups())
        return value

    def _convert_to_python(self, value, state):
        self.assert_string(value, state)
        try:
            value = value.encode('ascii', 'strict')
        except UnicodeEncodeError:
            raise Invalid(self.message('phoneFormat', state), value, state)
        if unicode is str:  # Python 3
            value = value.decode('ascii')
        value = self._mark_chars_re.sub('-', value)
        for f, t in [('  ', ' '),
                ('--', '-'), (' - ', '-'), ('- ', '-'), (' -', '-')]:
            value = value.replace(f, t)
        value = self._perform_rex_transformation(
            value, self._preTransformations)
        if self.default_cc:
            if callable(self.default_cc):
                cc = self.default_cc()
            else:
                cc = self.default_cc
            value = self._prepend_country_code(value, self._ccIncluder, cc)
        value = self._perform_rex_transformation(
            value, self._postTransformations)
        value = value.replace(' ', '')
        # did we successfully transform that phone number? Thus, is it valid?
        if not self._phoneIsSane.search(value):
            raise Invalid(self.message('phoneFormat', state), value, state)
        return value


############################################################
## language validators
############################################################

class LanguageValidator(FancyValidator):
    """
    Converts a given language into its ISO 639 alpha 2 code, if there is any.
    Returns the language's full name in the reverse.

    Warning: ISO 639 neither differentiates between languages such as Cantonese
    and Mandarin nor does it contain all spoken languages. E.g., Lechitic
    languages are missing.
    Warning: ISO 639 is a smaller subset of ISO 639-2

    @param  key_ok  accept the language's code instead of its name for input
                    defaults to True

    ::

        >>> l = LanguageValidator()
        >>> l.to_python('German')
        u'de'
        >>> l.to_python('Chinese')
        u'zh'
        >>> l.to_python('Klingonian')
        Traceback (most recent call last):
            ...
        Invalid: That language is not listed in ISO 639
        >>> l.from_python('de')
        u'German'
        >>> l.from_python('zh')
        u'Chinese'
    """

    key_ok = True

    messages = dict(
        valueNotFound=_('That language is not listed in ISO 639'))

    def __init__(self, *args, **kw):
        FancyValidator.__init__(self, *args, **kw)
        if no_country:
            warnings.warn(no_country, Warning, 2)

    def _convert_to_python(self, value, state):
        upval = value.upper()
        if self.key_ok:
            try:
                get_language(value)
            except Exception:
                pass
            else:
                return value
        for k, v in get_languages():
            if v.upper() == upval:
                return k
        raise Invalid(self.message('valueNotFound', state), value, state)

    def _convert_from_python(self, value, state):
        try:
            return get_language(value.lower())
        except KeyError:
            return value


def validators():
    """Return the names of all validators in this module."""
    return [name for name, value in globals().items()
        if isinstance(value, type) and issubclass(value, FancyValidator)]

__all__ = ['Invalid'] + validators()
