import itertools

from zope.interface import implementer

from repoze.who.interfaces import IAuthenticator
from repoze.who.utils import resolveDotted
from repoze.who._compat import izip_longest


def _padding_for_file_lines():
    yield 'aaaaaa:bbbbbb'


@implementer(IAuthenticator)
class HTPasswdPlugin(object):


    def __init__(self, filename, check):
        self.filename = filename
        self.check = check

    # IAuthenticatorPlugin
    def authenticate(self, environ, identity):
        # NOW HEAR THIS!!!
        #
        # This method is *intentionally* slower than would be ideal because
        # it is trying to avoid leaking information via timing attacks
        # (number of users, length of user IDs, length of passwords, etc.).
        #
        # Do *not* try to optimize anything away here.
        try:
            login = identity['login']
            password = identity['password']
        except KeyError:
            return None

        if hasattr(self.filename, 'seek'):
            # assumed to have a readline
            self.filename.seek(0)
            f = self.filename
            must_close = False
        else:
            try:
                f = open(self.filename, 'r')
                must_close = True
            except IOError:
                environ['repoze.who.logger'].warn('could not open htpasswd '
                                                  'file %s' % self.filename)
                return None

        result = None
        maybe_user = None
        to_check = 'ABCDEF0123456789'

        # Try not to reveal how many users we have.
        # XXX:  the max count here should be configurable ;(
        lines = itertools.chain(f, _padding_for_file_lines())
        for line in itertools.islice(lines, 0, 1000):
            try:
                username, hashed = line.rstrip().split(':', 1)
            except ValueError:
                continue
            if _same_string(username, login):
                # Don't bail early:  leaks information!!
                maybe_user = username
                to_check = hashed

        if must_close:
            f.close()

        # Check *something* here, to mitigate a timing attack.
        password_ok = self.check(password, to_check)

        # Check our flags:  if both are OK, we found a match.
        if password_ok and maybe_user:
            result = maybe_user

        return result

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__,
                            id(self)) #pragma NO COVERAGE

PADDING = ' ' * 1000

def _same_string(x, y):
    # Attempt at isochronous string comparison.
    mismatches = filter(None, [a != b for a, b, ignored
                                    in izip_longest(x, y, PADDING)])
    if type(mismatches) != list: #pragma NO COVER Python >= 3.0
        mismatches = list(mismatches)
    return len(mismatches) == 0

def crypt_check(password, hashed):
    from crypt import crypt
    salt = hashed[:2]
    return _same_string(hashed, crypt(password, salt))

def sha1_check(password, hashed):
    from hashlib import sha1
    from base64 import standard_b64encode
    from repoze.who._compat import must_encode
    encrypted_string = standard_b64encode(sha1(must_encode(password)).digest())
    return _same_string(hashed, "%s%s" % ("{SHA}", encrypted_string))

def plain_check(password, hashed):
    return _same_string(password, hashed)


def make_plugin(filename=None, check_fn=None):
    if filename is None:
        raise ValueError('filename must be specified')
    if check_fn is None:
        raise ValueError('check_fn must be specified')
    check = resolveDotted(check_fn)
    return HTPasswdPlugin(filename, check)
