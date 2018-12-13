"""
Does parsing of ETag-related headers: If-None-Matches, If-Matches

Also If-Range parsing
"""

from webob.datetime_utils import *
from webob.util import rfc_reference

__all__ = ['AnyETag', 'NoETag', 'ETagMatcher', 'IfRange', 'NoIfRange', 'etag_property']


def etag_property(key, default, rfc_section):
    doc = "Gets and sets the %r key in the environment." % key
    doc += rfc_reference(key, rfc_section)
    doc += "  Converts it as a Etag."
    def fget(req):
        value = req.environ.get(key)
        if not value:
            return default
        elif value == '*':
            return AnyETag
        else:
            return ETagMatcher.parse(value)
    def fset(req, val):
        if val is None:
            req.environ[key] = None
        else:
            req.environ[key] = str(val)
    def fdel(req):
        del req.environ[key]
    return property(fget, fset, fdel, doc=doc)


class _AnyETag(object):
    """
    Represents an ETag of *, or a missing ETag when matching is 'safe'
    """

    def __repr__(self):
        return '<ETag *>'

    def __nonzero__(self):
        return False

    def __contains__(self, other):
        return True

    def weak_match(self, other):
        return True

    def __str__(self):
        return '*'

AnyETag = _AnyETag()

class _NoETag(object):
    """
    Represents a missing ETag when matching is unsafe
    """

    def __repr__(self):
        return '<No ETag>'

    def __nonzero__(self):
        return False

    def __contains__(self, other):
        return False

    def weak_match(self, other):
        return False

    def __str__(self):
        return ''

NoETag = _NoETag()

class ETagMatcher(object):

    """
    Represents an ETag request.  Supports containment to see if an
    ETag matches.  You can also use
    ``etag_matcher.weak_contains(etag)`` to allow weak ETags to match
    (allowable for conditional GET requests, but not ranges or other
    methods).
    """

    def __init__(self, etags, weak_etags=()):
        self.etags = etags
        self.weak_etags = weak_etags

    def __contains__(self, other):
        return other in self.etags or other in self.weak_etags

    def weak_match(self, other):
        if other.lower().startswith('w/'):
            other = other[2:]
        return other in self.etags or other in self.weak_etags

    def __repr__(self):
        return '<ETag %s>' % (
            ' or '.join(self.etags))

    def parse(cls, value):
        """
        Parse this from a header value
        """
        results = []
        weak_results = []
        while value:
            if value.lower().startswith('w/'):
                # Next item is weak
                weak = True
                value = value[2:]
            else:
                weak = False
            if value.startswith('"'):
                try:
                    etag, rest = value[1:].split('"', 1)
                except ValueError:
                    etag = value.strip(' ",')
                    rest = ''
                else:
                    rest = rest.strip(', ')
            else:
                if ',' in value:
                    etag, rest = value.split(',', 1)
                    rest = rest.strip()
                else:
                    etag = value
                    rest = ''
            if etag == '*':
                return AnyETag
            if etag:
                if weak:
                    weak_results.append(etag)
                else:
                    results.append(etag)
            value = rest
        return cls(results, weak_results)
    parse = classmethod(parse)

    def __str__(self):
        # FIXME: should I quote these?
        items = list(self.etags)
        for weak in self.weak_etags:
            items.append('W/%s' % weak)
        return ', '.join(items)

class IfRange(object):
    """
    Parses and represents the If-Range header, which can be
    an ETag *or* a date
    """
    def __init__(self, etag=None, date=None):
        self.etag = etag
        self.date = date

    def __repr__(self):
        if self.etag is None:
            etag = '*'
        else:
            etag = str(self.etag)
        if self.date is None:
            date = '*'
        else:
            date = serialize_date(self.date)
        return '<%s etag=%s, date=%s>' % (
            self.__class__.__name__,
            etag, date)

    def __str__(self):
        if self.etag is not None:
            return str(self.etag)
        elif self.date:
            return serialize_date(self.date)
        else:
            return ''

    def match(self, etag=None, last_modified=None):
        """
        Return True if the If-Range header matches the given etag or last_modified
        """
        if self.date is not None:
            if last_modified is None:
                # Conditional with nothing to base the condition won't work
                return False
            return last_modified <= self.date
        elif self.etag is not None:
            if not etag:
                return False
            return etag in self.etag
        return True

    def match_response(self, response):
        """
        Return True if this matches the given ``webob.Response`` instance.
        """
        return self.match(etag=response.etag, last_modified=response.last_modified)

    @classmethod
    def parse(cls, value):
        """
        Parse this from a header value.
        """
        date = etag = None
        if not value:
            etag = NoETag()
        elif value and value.endswith(' GMT'):
            # Must be a date
            date = parse_date(value)
        else:
            etag = ETagMatcher.parse(value)
        return cls(etag=etag, date=date)

class _NoIfRange(object):
    """
    Represents a missing If-Range header
    """

    def __repr__(self):
        return '<Empty If-Range>'

    def __str__(self):
        return ''

    def __nonzero__(self):
        return False

    def match(self, etag=None, last_modified=None):
        return True

    def match_response(self, response):
        return True

NoIfRange = _NoIfRange()


