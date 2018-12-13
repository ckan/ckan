import calendar
from datetime import datetime, timedelta
import os

import hashlib
import hmac


if hasattr(hmac, 'compare_digest'):
    # Python 2.7.7 / 3.3 have a built-in timing independant comparison function
    constant_time_compare = hmac.compare_digest
else:
    def constant_time_compare(actual, expected):
        """
        Returns True if the two strings are equal, False otherwise

        The time taken is dependent on the number of characters provided
        instead of the number of characters that match.
        """
        actual_len = len(actual)
        expected_len = len(expected)
        result = actual_len ^ expected_len
        if expected_len > 0:
            for i in xrange(actual_len):
                result |= ord(actual[i]) ^ ord(expected[i % expected_len])
        return result == 0


def gen_csrf_secret():
    return os.urandom(32)


def generate_csrf_token(secret):
    # Make tokens valid for 3 days
    expiry_dt = datetime.utcnow() + timedelta(days=3)
    expiry_ts = str(calendar.timegm(expiry_dt.utctimetuple()))

    hashed = hmac.new(secret, expiry_ts, hashlib.sha256).hexdigest()
    return ','.join((expiry_ts, hashed))


def valid_csrf_token(secret, token):
    try:
        expiry_ts, hashed = token.split(',')
        expiry_dt = datetime.utcfromtimestamp(int(expiry_ts))
    except ValueError, e:
        return False

    if expiry_dt < datetime.utcnow():
        return False

    expected = hmac.new(secret, expiry_ts, hashlib.sha256).hexdigest()

    return constant_time_compare(str(hashed), expected)
