from ._compat import PY2, pickle, http_cookies, unicode_text, b64encode, b64decode, string_type

import os
import time
from datetime import datetime, timedelta
from beaker.crypto import hmac as HMAC, hmac_sha1 as SHA1, sha1, get_nonce_size, DEFAULT_NONCE_BITS, get_crypto_module
from beaker import crypto, util
from beaker.cache import clsmap
from beaker.exceptions import BeakerException, InvalidCryptoBackendError
from beaker.cookie import SimpleCookie

__all__ = ['SignedCookie', 'Session', 'InvalidSignature']


class _InvalidSignatureType(object):
    """Returned from SignedCookie when the value's signature was invalid."""
    def __nonzero__(self):
        return False

    def __bool__(self):
        return False


InvalidSignature = _InvalidSignatureType()


try:
    import uuid

    def _session_id():
        return uuid.uuid4().hex
except ImportError:
    import random
    if hasattr(os, 'getpid'):
        getpid = os.getpid
    else:
        def getpid():
            return ''

    def _session_id():
        id_str = "%f%s%f%s" % (
                    time.time(),
                    id({}),
                    random.random(),
                    getpid()
                )
        # NB: nothing against second parameter to b64encode, but it seems
        #     to be slower than simple chained replacement
        if not PY2:
            raw_id = b64encode(sha1(id_str.encode('ascii')).digest())
            return str(raw_id.replace(b'+', b'-').replace(b'/', b'_').rstrip(b'='))
        else:
            raw_id = b64encode(sha1(id_str).digest())
            return raw_id.replace('+', '-').replace('/', '_').rstrip('=')


class SignedCookie(SimpleCookie):
    """Extends python cookie to give digital signature support"""
    def __init__(self, secret, input=None):
        self.secret = secret.encode('UTF-8')
        http_cookies.BaseCookie.__init__(self, input)

    def value_decode(self, val):
        val = val.strip('"')
        if not val:
            return None, val

        sig = HMAC.new(self.secret, val[40:].encode('utf-8'), SHA1).hexdigest()

        # Avoid timing attacks
        invalid_bits = 0
        input_sig = val[:40]
        if len(sig) != len(input_sig):
            return InvalidSignature, val

        for a, b in zip(sig, input_sig):
            invalid_bits += a != b

        if invalid_bits:
            return InvalidSignature, val
        else:
            return val[40:], val

    def value_encode(self, val):
        sig = HMAC.new(self.secret, val.encode('utf-8'), SHA1).hexdigest()
        return str(val), ("%s%s" % (sig, val))


class Session(dict):
    """Session object that uses container package for storage.

    :param invalidate_corrupt: How to handle corrupt data when loading. When
                               set to True, then corrupt data will be silently
                               invalidated and a new session created,
                               otherwise invalid data will cause an exception.
    :type invalidate_corrupt: bool
    :param use_cookies: Whether or not cookies should be created. When set to
                        False, it is assumed the user will handle storing the
                        session on their own.
    :type use_cookies: bool
    :param type: What data backend type should be used to store the underlying
                 session data
    :param key: The name the cookie should be set to.
    :param timeout: How long session data is considered valid. This is used
                    regardless of the cookie being present or not to determine
                    whether session data is still valid. Can be set to None to
                    disable session time out.
    :type timeout: int or None
    :param save_accessed_time: Whether beaker should save the session's access
                               time (True) or only modification time (False).
                               Defaults to True.
    :param cookie_expires: Expiration date for cookie
    :param cookie_domain: Domain to use for the cookie.
    :param cookie_path: Path to use for the cookie.
    :param data_serializer: If ``"json"`` or ``"pickle"`` should be used
                              to serialize data. Can also be an object with
                              ``loads` and ``dumps`` methods. By default
                              ``"pickle"`` is used.
    :param secure: Whether or not the cookie should only be sent over SSL.
    :param httponly: Whether or not the cookie should only be accessible by
                     the browser not by JavaScript.
    :param encrypt_key: The key to use for the local session encryption, if not
                        provided the session will not be encrypted.
    :param validate_key: The key used to sign the local encrypted session
    :param encrypt_nonce_bits: Number of bits used to generate nonce for encryption key salt.
                               For security reason this is 128bits be default. If you want
                               to keep backward compatibility with sessions generated before 1.8.0
                               set this to 48.
    :param crypto_type: encryption module to use
    :param samesite: SameSite value for the cookie -- should be either 'Lax',
                     'Strict', or None.
    """
    def __init__(self, request, id=None, invalidate_corrupt=False,
                 use_cookies=True, type=None, data_dir=None,
                 key='beaker.session.id', timeout=None, save_accessed_time=True,
                 cookie_expires=True, cookie_domain=None, cookie_path='/',
                 data_serializer='pickle', secret=None,
                 secure=False, namespace_class=None, httponly=False,
                 encrypt_key=None, validate_key=None, encrypt_nonce_bits=DEFAULT_NONCE_BITS,
                 crypto_type='default', samesite='Lax',
                 **namespace_args):
        if not type:
            if data_dir:
                self.type = 'file'
            else:
                self.type = 'memory'
        else:
            self.type = type

        self.namespace_class = namespace_class or clsmap[self.type]

        self.namespace_args = namespace_args

        self.request = request
        self.data_dir = data_dir
        self.key = key

        if timeout and not save_accessed_time:
            raise BeakerException("timeout requires save_accessed_time")
        self.timeout = timeout

        # If a timeout was provided, forward it to the backend too, so the backend
        # can automatically expire entries if it's supported.
        if self.timeout is not None:
            # The backend expiration should always be a bit longer than the
            # session expiration itself to prevent the case where the backend data expires while
            # the session is being read (PR#153). 2 Minutes seems a reasonable time.
            self.namespace_args['timeout'] = self.timeout + 60 * 2

        self.save_atime = save_accessed_time
        self.use_cookies = use_cookies
        self.cookie_expires = cookie_expires

        self._set_serializer(data_serializer)

        # Default cookie domain/path
        self._domain = cookie_domain
        self._path = cookie_path
        self.was_invalidated = False
        self.secret = secret
        self.secure = secure
        self.httponly = httponly
        self.samesite = samesite
        self.encrypt_key = encrypt_key
        self.validate_key = validate_key
        self.encrypt_nonce_size = get_nonce_size(encrypt_nonce_bits)
        self.crypto_module = get_crypto_module(crypto_type)
        self.id = id
        self.accessed_dict = {}
        self.invalidate_corrupt = invalidate_corrupt

        if self.use_cookies:
            cookieheader = request.get('cookie', '')
            if secret:
                try:
                    self.cookie = SignedCookie(
                        secret,
                        input=cookieheader,
                    )
                except http_cookies.CookieError:
                    self.cookie = SignedCookie(
                        secret,
                        input=None,
                    )
            else:
                self.cookie = SimpleCookie(input=cookieheader)

            if not self.id and self.key in self.cookie:
                cookie_data = self.cookie[self.key].value
                # Should we check invalidate_corrupt here?
                if cookie_data is InvalidSignature:
                    cookie_data = None
                self.id = cookie_data

        self.is_new = self.id is None
        if self.is_new:
            self._create_id()
            self['_accessed_time'] = self['_creation_time'] = time.time()
        else:
            try:
                self.load()
            except Exception as e:
                if self.invalidate_corrupt:
                    util.warn(
                        "Invalidating corrupt session %s; "
                        "error was: %s.  Set invalidate_corrupt=False "
                        "to propagate this exception." % (self.id, e))
                    self.invalidate()
                else:
                    raise

    def _set_serializer(self, data_serializer):
        self.data_serializer = data_serializer
        if self.data_serializer == 'json':
            self.serializer = util.JsonSerializer()
        elif self.data_serializer == 'pickle':
            self.serializer = util.PickleSerializer()
        elif isinstance(self.data_serializer, string_type):
            raise BeakerException('Invalid value for data_serializer: %s' % data_serializer)
        else:
            self.serializer = data_serializer

    def has_key(self, name):
        return name in self

    def _set_cookie_values(self, expires=None):
        self.cookie[self.key] = self.id
        if self._domain:
            self.cookie[self.key]['domain'] = self._domain
        if self.secure:
            self.cookie[self.key]['secure'] = True
        if self.samesite:
            self.cookie[self.key]['samesite'] = self.samesite
        self._set_cookie_http_only()
        self.cookie[self.key]['path'] = self._path

        self._set_cookie_expires(expires)

    def _set_cookie_expires(self, expires):
        if expires is None:
            expires = self.cookie_expires
        if expires is False:
            expires_date = datetime.fromtimestamp(0x7FFFFFFF)
        elif isinstance(expires, timedelta):
            expires_date = datetime.utcnow() + expires
        elif isinstance(expires, datetime):
            expires_date = expires
        elif expires is not True:
            raise ValueError("Invalid argument for cookie_expires: %s"
                             % repr(self.cookie_expires))
        self.cookie_expires = expires
        if not self.cookie or self.key not in self.cookie:
            self.cookie[self.key] = self.id
        if expires is True:
            self.cookie[self.key]['expires'] = ''
            return True
        self.cookie[self.key]['expires'] = \
            expires_date.strftime("%a, %d-%b-%Y %H:%M:%S GMT")
        return expires_date

    def _update_cookie_out(self, set_cookie=True):
        self._set_cookie_values()
        self.request['cookie_out'] = self.cookie[self.key].output(header='')
        self.request['set_cookie'] = set_cookie

    def _set_cookie_http_only(self):
        try:
            if self.httponly:
                self.cookie[self.key]['httponly'] = True
        except http_cookies.CookieError as e:
            if 'Invalid Attribute httponly' not in str(e):
                raise
            util.warn('Python 2.6+ is required to use httponly')

    def _create_id(self, set_new=True):
        self.id = _session_id()

        if set_new:
            self.is_new = True
            self.last_accessed = None
        if self.use_cookies:
            sc = set_new is False
            self._update_cookie_out(set_cookie=sc)

    @property
    def created(self):
        return self['_creation_time']

    def _set_domain(self, domain):
        self['_domain'] = self._domain = domain
        self._update_cookie_out()

    def _get_domain(self):
        return self._domain

    domain = property(_get_domain, _set_domain)

    def _set_path(self, path):
        self['_path'] = self._path = path
        self._update_cookie_out()

    def _get_path(self):
        return self._path

    path = property(_get_path, _set_path)

    def _encrypt_data(self, session_data=None):
        """Serialize, encipher, and base64 the session dict"""
        session_data = session_data or self.copy()
        if self.encrypt_key:
            nonce_len, nonce_b64len = self.encrypt_nonce_size
            nonce = b64encode(os.urandom(nonce_len))[:nonce_b64len]
            encrypt_key = crypto.generateCryptoKeys(self.encrypt_key,
                                                    self.validate_key + nonce,
                                                    1,
                                                    self.crypto_module.getKeyLength())
            data = self.serializer.dumps(session_data)
            return nonce + b64encode(self.crypto_module.aesEncrypt(data, encrypt_key))
        else:
            data = self.serializer.dumps(session_data)
            return b64encode(data)

    def _decrypt_data(self, session_data):
        """Base64, decipher, then un-serialize the data for the session
        dict"""
        if self.encrypt_key:
            __, nonce_b64len = self.encrypt_nonce_size
            nonce = session_data[:nonce_b64len]
            encrypt_key = crypto.generateCryptoKeys(self.encrypt_key,
                                                    self.validate_key + nonce,
                                                    1,
                                                    self.crypto_module.getKeyLength())
            payload = b64decode(session_data[nonce_b64len:])
            data = self.crypto_module.aesDecrypt(payload, encrypt_key)
        else:
            data = b64decode(session_data)

        return self.serializer.loads(data)

    def _delete_cookie(self):
        self.request['set_cookie'] = True
        expires = datetime.utcnow() - timedelta(365)
        self._set_cookie_values(expires)
        self._update_cookie_out()

    def delete(self):
        """Deletes the session from the persistent storage, and sends
        an expired cookie out"""
        if self.use_cookies:
            self._delete_cookie()
        self.clear()

    def invalidate(self):
        """Invalidates this session, creates a new session id, returns
        to the is_new state"""
        self.clear()
        self.was_invalidated = True
        self._create_id()
        self.load()

    def load(self):
        "Loads the data from this session from persistent storage"
        self.namespace = self.namespace_class(self.id,
            data_dir=self.data_dir,
            digest_filenames=False,
            **self.namespace_args)
        now = time.time()
        if self.use_cookies:
            self.request['set_cookie'] = True

        self.namespace.acquire_read_lock()
        timed_out = False
        try:
            self.clear()
            try:
                session_data = self.namespace['session']

                if (session_data is not None and self.encrypt_key):
                    session_data = self._decrypt_data(session_data)

                # Memcached always returns a key, its None when its not
                # present
                if session_data is None:
                    session_data = {
                        '_creation_time': now,
                        '_accessed_time': now
                    }
                    self.is_new = True
            except (KeyError, TypeError):
                session_data = {
                    '_creation_time': now,
                    '_accessed_time': now
                }
                self.is_new = True

            if session_data is None or len(session_data) == 0:
                session_data = {
                    '_creation_time': now,
                    '_accessed_time': now
                }
                self.is_new = True

            if self.timeout is not None and \
               now - session_data['_accessed_time'] > self.timeout:
                timed_out = True
            else:
                # Properly set the last_accessed time, which is different
                # than the *currently* _accessed_time
                if self.is_new or '_accessed_time' not in session_data:
                    self.last_accessed = None
                else:
                    self.last_accessed = session_data['_accessed_time']

                # Update the current _accessed_time
                session_data['_accessed_time'] = now

                # Set the path if applicable
                if '_path' in session_data:
                    self._path = session_data['_path']
                self.update(session_data)
                self.accessed_dict = session_data.copy()
        finally:
            self.namespace.release_read_lock()
        if timed_out:
            self.invalidate()

    def save(self, accessed_only=False):
        """Saves the data for this session to persistent storage

        If accessed_only is True, then only the original data loaded
        at the beginning of the request will be saved, with the updated
        last accessed time.

        """
        # Look to see if its a new session that was only accessed
        # Don't save it under that case
        if accessed_only and (self.is_new or not self.save_atime):
            return None

        # this session might not have a namespace yet or the session id
        # might have been regenerated
        if not hasattr(self, 'namespace') or self.namespace.namespace != self.id:
            self.namespace = self.namespace_class(
                                    self.id,
                                    data_dir=self.data_dir,
                                    digest_filenames=False,
                                    **self.namespace_args)

        self.namespace.acquire_write_lock(replace=True)
        try:
            if accessed_only:
                data = dict(self.accessed_dict.items())
            else:
                data = dict(self.items())

            if self.encrypt_key:
                data = self._encrypt_data(data)

            # Save the data
            if not data and 'session' in self.namespace:
                del self.namespace['session']
            else:
                self.namespace['session'] = data
        finally:
            self.namespace.release_write_lock()
        if self.use_cookies and self.is_new:
            self.request['set_cookie'] = True

    def revert(self):
        """Revert the session to its original state from its first
        access in the request"""
        self.clear()
        self.update(self.accessed_dict)

    def regenerate_id(self):
        """
            creates a new session id, retains all session data

            Its a good security practice to regnerate the id after a client
            elevates privileges.

        """
        self._create_id(set_new=False)

    # TODO: I think both these methods should be removed.  They're from
    # the original mod_python code i was ripping off but they really
    # have no use here.
    def lock(self):
        """Locks this session against other processes/threads.  This is
        automatic when load/save is called.

        ***use with caution*** and always with a corresponding 'unlock'
        inside a "finally:" block, as a stray lock typically cannot be
        unlocked without shutting down the whole application.

        """
        self.namespace.acquire_write_lock()

    def unlock(self):
        """Unlocks this session against other processes/threads.  This
        is automatic when load/save is called.

        ***use with caution*** and always within a "finally:" block, as
        a stray lock typically cannot be unlocked without shutting down
        the whole application.

        """
        self.namespace.release_write_lock()


class CookieSession(Session):
    """Pure cookie-based session

    Options recognized when using cookie-based sessions are slightly
    more restricted than general sessions.

    :param key: The name the cookie should be set to.
    :param timeout: How long session data is considered valid. This is used
                    regardless of the cookie being present or not to determine
                    whether session data is still valid.
    :type timeout: int
    :param save_accessed_time: Whether beaker should save the session's access
                               time (True) or only modification time (False).
                               Defaults to True.
    :param cookie_expires: Expiration date for cookie
    :param cookie_domain: Domain to use for the cookie.
    :param cookie_path: Path to use for the cookie.
    :param data_serializer: If ``"json"`` or ``"pickle"`` should be used
                              to serialize data. Can also be an object with
                              ``loads` and ``dumps`` methods. By default
                              ``"pickle"`` is used.
    :param secure: Whether or not the cookie should only be sent over SSL.
    :param httponly: Whether or not the cookie should only be accessible by
                     the browser not by JavaScript.
    :param encrypt_key: The key to use for the local session encryption, if not
                        provided the session will not be encrypted.
    :param validate_key: The key used to sign the local encrypted session
    :param invalidate_corrupt: How to handle corrupt data when loading. When
                               set to True, then corrupt data will be silently
                               invalidated and a new session created,
                               otherwise invalid data will cause an exception.
    :type invalidate_corrupt: bool
    :param crypto_type: The crypto module to use.
    :param samesite: SameSite value for the cookie -- should be either 'Lax',
                     'Strict', or None.
    """
    def __init__(self, request, key='beaker.session.id', timeout=None,
                 save_accessed_time=True, cookie_expires=True, cookie_domain=None,
                 cookie_path='/', encrypt_key=None, validate_key=None, secure=False,
                 httponly=False, data_serializer='pickle',
                 encrypt_nonce_bits=DEFAULT_NONCE_BITS, invalidate_corrupt=False,
                 crypto_type='default', samesite='Lax',
                 **kwargs):

        self.crypto_module = get_crypto_module(crypto_type)

        if encrypt_key and not self.crypto_module.has_aes:
            raise InvalidCryptoBackendError("No AES library is installed, can't generate "
                                            "encrypted cookie-only Session.")

        self.request = request
        self.key = key
        self.timeout = timeout
        self.save_atime = save_accessed_time
        self.cookie_expires = cookie_expires
        self.encrypt_key = encrypt_key
        self.validate_key = validate_key
        self.encrypt_nonce_size = get_nonce_size(encrypt_nonce_bits)
        self.request['set_cookie'] = False
        self.secure = secure
        self.httponly = httponly
        self.samesite = samesite
        self._domain = cookie_domain
        self._path = cookie_path
        self.invalidate_corrupt = invalidate_corrupt
        self._set_serializer(data_serializer)

        try:
            cookieheader = request['cookie']
        except KeyError:
            cookieheader = ''

        if validate_key is None:
            raise BeakerException("No validate_key specified for Cookie only "
                                  "Session.")
        if timeout and not save_accessed_time:
            raise BeakerException("timeout requires save_accessed_time")

        try:
            self.cookie = SignedCookie(
                validate_key,
                input=cookieheader,
            )
        except http_cookies.CookieError:
            self.cookie = SignedCookie(
                validate_key,
                input=None,
            )

        self['_id'] = _session_id()
        self.is_new = True

        # If we have a cookie, load it
        if self.key in self.cookie and self.cookie[self.key].value is not None:
            self.is_new = False
            try:
                cookie_data = self.cookie[self.key].value
                if cookie_data is InvalidSignature:
                    raise BeakerException("Invalid signature")
                self.update(self._decrypt_data(cookie_data))
                self._path = self.get('_path', '/')
            except Exception as e:
                if self.invalidate_corrupt:
                    util.warn(
                        "Invalidating corrupt session %s; "
                        "error was: %s.  Set invalidate_corrupt=False "
                        "to propagate this exception." % (self.id, e))
                    self.invalidate()
                else:
                    raise

            if self.timeout is not None:
                now = time.time()
                last_accessed_time = self.get('_accessed_time', now)
                if now - last_accessed_time > self.timeout:
                    self.clear()

            self.accessed_dict = self.copy()
            self._create_cookie()

    def created(self):
        return self['_creation_time']
    created = property(created)

    def id(self):
        return self['_id']
    id = property(id)

    def _set_domain(self, domain):
        self['_domain'] = domain
        self._domain = domain

    def _get_domain(self):
        return self._domain

    domain = property(_get_domain, _set_domain)

    def _set_path(self, path):
        self['_path'] = self._path = path

    def _get_path(self):
        return self._path

    path = property(_get_path, _set_path)

    def save(self, accessed_only=False):
        """Saves the data for this session to persistent storage"""
        if accessed_only and (self.is_new or not self.save_atime):
            return
        if accessed_only:
            self.clear()
            self.update(self.accessed_dict)
        self._create_cookie()

    def expire(self):
        """Delete the 'expires' attribute on this Session, if any."""

        self.pop('_expires', None)

    def _create_cookie(self):
        if '_creation_time' not in self:
            self['_creation_time'] = time.time()
        if '_id' not in self:
            self['_id'] = _session_id()
        self['_accessed_time'] = time.time()

        val = self._encrypt_data()
        if len(val) > 4064:
            raise BeakerException("Cookie value is too long to store")

        self.cookie[self.key] = val

        if '_expires' in self:
            expires = self['_expires']
        else:
            expires = None
        expires = self._set_cookie_expires(expires)
        if expires is not None:
            self['_expires'] = expires

        if '_domain' in self:
            self.cookie[self.key]['domain'] = self['_domain']
        elif self._domain:
            self.cookie[self.key]['domain'] = self._domain
        if self.secure:
            self.cookie[self.key]['secure'] = True
        self._set_cookie_http_only()

        self.cookie[self.key]['path'] = self.get('_path', '/')

        self.request['cookie_out'] = self.cookie[self.key].output(header='')
        self.request['set_cookie'] = True

    def delete(self):
        """Delete the cookie, and clear the session"""
        # Send a delete cookie request
        self._delete_cookie()
        self.clear()

    def invalidate(self):
        """Clear the contents and start a new session"""
        self.clear()
        self['_id'] = _session_id()


class SessionObject(object):
    """Session proxy/lazy creator

    This object proxies access to the actual session object, so that in
    the case that the session hasn't been used before, it will be
    setup. This avoid creating and loading the session from persistent
    storage unless its actually used during the request.

    """
    def __init__(self, environ, **params):
        self.__dict__['_params'] = params
        self.__dict__['_environ'] = environ
        self.__dict__['_sess'] = None
        self.__dict__['_headers'] = {}

    def _session(self):
        """Lazy initial creation of session object"""
        if self.__dict__['_sess'] is None:
            params = self.__dict__['_params']
            environ = self.__dict__['_environ']
            self.__dict__['_headers'] = req = {'cookie_out': None}
            req['cookie'] = environ.get('HTTP_COOKIE')
            session_cls = params.get('session_class', None)
            if session_cls is None:
                if params.get('type') == 'cookie':
                    session_cls = CookieSession
                else:
                    session_cls = Session
            else:
                assert issubclass(session_cls, Session),\
                    "Not a Session: " + session_cls
            self.__dict__['_sess'] = session_cls(req, **params)
        return self.__dict__['_sess']

    def __getattr__(self, attr):
        return getattr(self._session(), attr)

    def __setattr__(self, attr, value):
        setattr(self._session(), attr, value)

    def __delattr__(self, name):
        self._session().__delattr__(name)

    def __getitem__(self, key):
        return self._session()[key]

    def __setitem__(self, key, value):
        self._session()[key] = value

    def __delitem__(self, key):
        self._session().__delitem__(key)

    def __repr__(self):
        return self._session().__repr__()

    def __iter__(self):
        """Only works for proxying to a dict"""
        return iter(self._session().keys())

    def __contains__(self, key):
        return key in self._session()

    def has_key(self, key):
        return key in self._session()

    def get_by_id(self, id):
        """Loads a session given a session ID"""
        params = self.__dict__['_params']
        session = Session({}, use_cookies=False, id=id, **params)
        if session.is_new:
            return None
        return session

    def save(self):
        self.__dict__['_dirty'] = True

    def delete(self):
        self.__dict__['_dirty'] = True
        self._session().delete()

    def persist(self):
        """Persist the session to the storage

        Always saves the whole session if save() or delete() have been called.
        If they haven't:

        - If autosave is set to true, saves the the entire session regardless.
        - If save_accessed_time is set to true or unset, only saves the updated
          access time.
        - If save_accessed_time is set to false, doesn't save anything.

        """
        if self.__dict__['_params'].get('auto'):
            self._session().save()
        elif self.__dict__['_params'].get('save_accessed_time', True):
            if self.dirty():
                self._session().save()
            else:
                self._session().save(accessed_only=True)
        else:  # save_accessed_time is false
            if self.dirty():
                self._session().save()

    def dirty(self):
        """Returns True if save() or delete() have been called"""
        return self.__dict__.get('_dirty', False)

    def accessed(self):
        """Returns whether or not the session has been accessed"""
        return self.__dict__['_sess'] is not None
