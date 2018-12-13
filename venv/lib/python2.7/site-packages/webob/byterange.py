class Range(object):
    """
        Represents the Range header.

        This only represents ``bytes`` ranges, which are the only kind
        specified in HTTP.  This can represent multiple sets of ranges,
        but no place else is this multi-range facility supported.
    """

    def __init__(self, ranges): # expect non-inclusive
        for begin, end in ranges:
            assert end is None or end >= 0, "Bad ranges: %r" % ranges
        self.ranges = ranges

    def satisfiable(self, length):
        """
            Returns true if this range can be satisfied by the resource
            with the given byte length.
        """
        for begin, end in self.ranges:
            # FIXME: bytes=-100 request on a one-byte entity is not satifiable
            # neither is bytes=100- (spec seems to be unclear on this)
            if end is not None and end >= length:
                return False
        return True

    def range_for_length(self, length):
        """
            *If* there is only one range, and *if* it is satisfiable by
            the given length, then return a (begin, end) non-inclusive range
            of bytes to serve.  Otherwise return None
        """
        if length is None or len(self.ranges) != 1:
            return None
        start, end = self.ranges[0]
        if end is None:
            end = length
            if start < 0:
                start += length
        if _is_content_range_valid(start, end, length):
            stop = min(end, length)
            return (start, stop)
        else:
            return None

    def content_range(self, length):
        """
            Works like range_for_length; returns None or a ContentRange object

            You can use it like::

                response.content_range = req.range.content_range(response.content_length)

            Though it's still up to you to actually serve that content range!
        """
        range = self.range_for_length(length)
        if range is None:
            return None
        return ContentRange(range[0], range[1], length)

    def __str__(self):
        parts = []
        for begin, end in self.ranges:
            if end is None:
                if begin >= 0:
                    parts.append('%s-' % begin)
                else:
                    parts.append(str(begin))
            else:
                if begin < 0:
                    raise ValueError("(%r, %r) should have a non-negative first value"
                                    % (begin, end))
                if end <= 0:
                    raise ValueError("(%r, %r) should have a positive second value"
                                    % (begin, end))
                parts.append('%s-%s' % (begin, end-1))
        return 'bytes=%s' % ','.join(parts)

    def __repr__(self):
        return '<%s ranges=%s>' % (
            self.__class__.__name__,
            ', '.join(map(repr, self.ranges)))

    @classmethod
    def parse(cls, header):
        """
            Parse the header; may return None if header is invalid
        """
        bytes = cls.parse_bytes(header)
        if bytes is None:
            return None
        units, ranges = bytes
        if units != 'bytes' or ranges is None:
            return None
        return cls(ranges)

    @staticmethod
    def parse_bytes(header):
        """
            Parse a Range header into (bytes, list_of_ranges).
            ranges in list_of_ranges are non-inclusive (unlike the HTTP header).

            Will return None if the header is invalid
        """
        if not header:
            raise TypeError("The header must not be empty")
        ranges = []
        last_end = 0
        try:
            (units, range) = header.split("=", 1)
            units = units.strip().lower()
            for item in range.split(","):
                if '-' not in item:
                    raise ValueError()
                if item.startswith('-'):
                    # This is a range asking for a trailing chunk.
                    if last_end < 0:
                        raise ValueError('too many end ranges')
                    begin = int(item)
                    end = None
                    last_end = -1
                else:
                    (begin, end) = item.split("-", 1)
                    begin = int(begin)
                    if begin < last_end or last_end < 0:
                        raise ValueError('begin<last_end, or last_end<0')
                    if end.strip():
                        end = int(end) + 1 # return val is non-inclusive
                        if begin >= end:
                            raise ValueError('begin>end')
                    else:
                        end = None
                    last_end = end
                ranges.append((begin, end))
        except ValueError, e:
            # In this case where the Range header is malformed,
            # section 14.16 says to treat the request as if the
            # Range header was not present.  How do I log this?
            return None
        return (units, ranges)


class ContentRange(object):

    """
    Represents the Content-Range header

    This header is ``start-stop/length``, where start-stop and length
    can be ``*`` (represented as None in the attributes).
    """

    def __init__(self, start, stop, length):
        if not _is_content_range_valid(start, stop, length):
            raise ValueError("Bad start:stop/length: %r-%r/%r" % (start, stop, length))
        self.start = start
        self.stop = stop # this is python-style range end (non-inclusive)
        self.length = length

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self)

    def __str__(self):
        if self.length is None:
            length = '*'
        else:
            length = self.length
        if self.start is None:
            assert self.stop is None
            return 'bytes */%s' % length
        stop = self.stop - 1 # from non-inclusive to HTTP-style
        return 'bytes %s-%s/%s' % (self.start, stop, length)

    def __iter__(self):
        """
            Mostly so you can unpack this, like:

                start, stop, length = res.content_range
        """
        return iter([self.start, self.stop, self.length])

    @classmethod
    def parse(cls, value):
        """
            Parse the header.  May return None if it cannot parse.
        """
        if value is None:
            return None
        value = value.strip()
        if not value.startswith('bytes '):
            # Unparseable
            return None
        value = value[len('bytes '):].strip()
        if '/' not in value:
            # Invalid, no length given
            return None
        range, length = value.split('/', 1)
        if length == '*':
            length = None
        elif length.isdigit():
            length = int(length)
        else:
            return None # invalid length

        if range == '*':
            return cls(None, None, length)
        elif '-' not in range:
            # Invalid, no range
            return None
        else:
            start, stop = range.split('-', 1)
            try:
                start = int(start)
                stop = int(stop)
                stop += 1 # convert to non-inclusive
            except ValueError:
                # Parse problem
                return None
            if _is_content_range_valid(start, stop, length, response=True):
                return cls(start, stop, length)
            return None



def _is_content_range_valid(start, stop, length, response=False):
    if (start is None) != (stop is None):
        return False
    elif start is None:
        return length is None or length >= 0
    elif length is None:
        return 0 <= start < stop
    elif start >= stop:
        return False
    elif response and stop > length:
        # "content-range: bytes 0-50/10" is invalid for a response
        # "range: bytes 0-50" is valid for a request to a 10-bytes entity
        return False
    else:
        return 0 <= start < length
