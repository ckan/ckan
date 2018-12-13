# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Create random secrets.
"""

import base64
import os
import random
import six
from six.moves import range

def random_bytes(length):
    """
    Return a string of the given length.  Uses ``os.urandom`` if it
    can, or just pseudo-random numbers otherwise.
    """
    try:
        return os.urandom(length)
    except AttributeError:
        return b''.join([
            six.int2byte(random.randrange(256)) for i in range(length)])

def secret_string(length=25):
    """
    Returns a random string of the given length.  The string
    is a base64-encoded version of a set of random bytes, truncated
    to the given length (and without any newlines).
    """
    s = random_bytes(length)
    s = base64.b64encode(s)
    if six.PY3:
        s = s.decode('ascii')
    for badchar in '\n\r=':
        s = s.replace(badchar, '')
    # We're wasting some characters here.  But random characters are
    # cheap ;)
    return s[:length]
