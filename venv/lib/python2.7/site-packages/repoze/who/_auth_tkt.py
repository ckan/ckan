# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
##########################################################################
#
# Copyright (c) 2005 Imaginary Landscape LLC and Contributors.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
##########################################################################
"""
Implementation of cookie signing as done in `mod_auth_tkt
<http://www.openfusion.com.au/labs/mod_auth_tkt/>`_.

mod_auth_tkt is an Apache module that looks for these signed cookies
and sets ``REMOTE_USER``, ``REMOTE_USER_TOKENS`` (a comma-separated
list of groups) and ``REMOTE_USER_DATA`` (arbitrary string data).

This module is an alternative to the ``paste.auth.cookie`` module;
it's primary benefit is compatibility with mod_auth_tkt, which in turn
makes it possible to use the same authentication process with
non-Python code run under Apache.
"""
import hashlib
import time as time_mod

from repoze.who._compat import encodestring
from repoze.who._compat import SimpleCookie
from repoze.who._compat import url_quote
from repoze.who._compat import url_unquote

DEFAULT_DIGEST = hashlib.md5


class AuthTicket(object):

    """
    This class represents an authentication token.  You must pass in
    the shared secret, the userid, and the IP address.  Optionally you
    can include tokens (a list of strings, representing role names),
    'user_data', which is arbitrary data available for your own use in
    later scripts.  Lastly, you can override the timestamp, cookie name,
    whether to secure the cookie and the digest algorithm (for details
    look at ``AuthTKTMiddleware``).

    Once you provide all the arguments, use .cookie_value() to
    generate the appropriate authentication ticket.  .cookie()
    generates a Cookie object, the str() of which is the complete
    cookie header to be sent.

    CGI usage::

        token = auth_tkt.AuthTick('sharedsecret', 'username',
            os.environ['REMOTE_ADDR'], tokens=['admin'])
        print('Status: 200 OK')
        print('Content-type: text/html')
        print(token.cookie())
        print("")
        ... redirect HTML ...

    Webware usage::

        token = auth_tkt.AuthTick('sharedsecret', 'username',
            self.request().environ()['REMOTE_ADDR'], tokens=['admin'])
        self.response().setCookie('auth_tkt', token.cookie_value())

    Be careful not to do an HTTP redirect after login; use meta
    refresh or Javascript -- some browsers have bugs where cookies
    aren't saved when set on a redirect.
    """

    def __init__(self, secret, userid, ip, tokens=(), user_data='',
                 time=None, cookie_name='auth_tkt',
                 secure=False, digest_algo=DEFAULT_DIGEST):
        self.secret = secret
        self.userid = userid
        self.ip = ip
        self.tokens = ','.join(tokens)
        self.user_data = user_data
        if time is None:
            self.time = time_mod.time()
        else:
            self.time = time
        self.cookie_name = cookie_name
        self.secure = secure
        if isinstance(digest_algo, str):
            # correct specification of digest from hashlib or fail
            self.digest_algo = getattr(hashlib, digest_algo)
        else:
            self.digest_algo = digest_algo

    def digest(self):
        return calculate_digest(
            self.ip, self.time, self.secret, self.userid, self.tokens,
            self.user_data, self.digest_algo)

    def cookie_value(self):
        v = '%s%08x%s!' % (self.digest(), int(self.time),
                           url_quote(self.userid))
        if self.tokens:
            v += self.tokens + '!'
        v += self.user_data
        return v

    def cookie(self):
        c = SimpleCookie()
        c_val = encodestring(self.cookie_value())
        c_val = c_val.strip().replace('\n', '')
        c[self.cookie_name] = c_val
        c[self.cookie_name]['path'] = '/'
        if self.secure:
            c[self.cookie_name]['secure'] = 'true'
        return c


class BadTicket(Exception):
    """
    Exception raised when a ticket can't be parsed.  If we get
    far enough to determine what the expected digest should have
    been, expected is set.  This should not be shown by default,
    but can be useful for debugging.
    """
    def __init__(self, msg, expected=None):
        self.expected = expected
        Exception.__init__(self, msg)


def parse_ticket(secret, ticket, ip, digest_algo=DEFAULT_DIGEST):
    """
    Parse the ticket, returning (timestamp, userid, tokens, user_data).

    If the ticket cannot be parsed, ``BadTicket`` will be raised with
    an explanation.
    """
    if isinstance(digest_algo, str):
        # correct specification of digest from hashlib or fail
        digest_algo = getattr(hashlib, digest_algo)
    digest_hexa_size = digest_algo().digest_size * 2
    ticket = ticket.strip('"')
    digest = ticket[:digest_hexa_size]
    try:
        timestamp = int(ticket[digest_hexa_size:digest_hexa_size + 8], 16)
    except ValueError as e:
        raise BadTicket('Timestamp is not a hex integer: %s' % e)
    try:
        userid, data = ticket[digest_hexa_size + 8:].split('!', 1)
    except ValueError:
        raise BadTicket('userid is not followed by !')
    userid = url_unquote(userid)
    if '!' in data:
        tokens, user_data = data.split('!', 1)
    else:
        # @@: Is this the right order?
        tokens = ''
        user_data = data

    expected = calculate_digest(ip, timestamp, secret,
                                userid, tokens, user_data,
                                digest_algo)

    if expected != digest:
        raise BadTicket('Digest signature is not correct',
                        expected=(expected, digest))

    tokens = tokens.split(',')

    return (timestamp, userid, tokens, user_data)


def calculate_digest(ip, timestamp, secret, userid, tokens, user_data,
                     digest_algo):
    secret = maybe_encode(secret)
    userid = maybe_encode(userid)
    tokens = maybe_encode(tokens)
    user_data = maybe_encode(user_data)
    digest0 = digest_algo(
        encode_ip_timestamp(ip, timestamp) + secret + userid + b'\0'
        + tokens + b'\0' + user_data).hexdigest()
    digest = digest_algo(maybe_encode(digest0) + secret).hexdigest()
    return digest


if type(chr(1)) == type(b''): #pragma NO COVER Python < 3.0
    def ints2bytes(ints):
        return b''.join(map(chr, ints))
else: #pragma NO COVER Python >= 3.0
    def ints2bytes(ints):
        return bytes(ints)

def encode_ip_timestamp(ip, timestamp):
    ip_chars = ints2bytes(map(int, ip.split('.')))
    t = int(timestamp)
    ts = ((t & 0xff000000) >> 24,
          (t & 0xff0000) >> 16,
          (t & 0xff00) >> 8,
          t & 0xff)
    ts_chars = ints2bytes(ts)
    return ip_chars + ts_chars


def maybe_encode(s, encoding='utf8'):
    if not isinstance(s, type(b'')):
        s = s.encode(encoding)
    return s


# Original Paste AuthTktMiddleware stripped:  we don't have a use for it.
