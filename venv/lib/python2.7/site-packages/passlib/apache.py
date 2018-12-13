"""passlib.apache - apache password support"""
# XXX: relocate this to passlib.ext.apache?
#=============================================================================
# imports
#=============================================================================
from __future__ import with_statement
# core
from hashlib import md5
import logging; log = logging.getLogger(__name__)
import os
import sys
from warnings import warn
# site
# pkg
from passlib.context import CryptContext
from passlib.exc import ExpectedStringError
from passlib.hash import htdigest
from passlib.utils import consteq, render_bytes, to_bytes, deprecated_method, is_ascii_codec
from passlib.utils.compat import b, bytes, join_bytes, str_to_bascii, u, \
                                 unicode, BytesIO, iteritems, imap, PY3
# local
__all__ = [
    'HtpasswdFile',
    'HtdigestFile',
]

#=============================================================================
# constants & support
#=============================================================================
_UNSET = object()

_BCOLON = b(":")

# byte values that aren't allowed in fields.
_INVALID_FIELD_CHARS = b(":\n\r\t\x00")

#=============================================================================
# backport of OrderedDict for PY2.5
#=============================================================================
try:
    from collections import OrderedDict
except ImportError:
    # Python 2.5
    class OrderedDict(dict):
        """hacked OrderedDict replacement.

        NOTE: this doesn't provide a full OrderedDict implementation,
        just the minimum needed by the Htpasswd internals.
        """
        def __init__(self):
            self._keys = []

        def __iter__(self):
            return iter(self._keys)

        def __setitem__(self, key, value):
            if key not in self:
                self._keys.append(key)
            super(OrderedDict, self).__setitem__(key, value)

        def __delitem__(self, key):
            super(OrderedDict, self).__delitem__(key)
            self._keys.remove(key)

        def iteritems(self):
            return ((key, self[key]) for key in self)

        # these aren't used or implemented, so disabling them for safety.
        update = pop = popitem = clear = keys = iterkeys = None

#=============================================================================
# common helpers
#=============================================================================
class _CommonFile(object):
    """common framework for HtpasswdFile & HtdigestFile"""
    #===================================================================
    # instance attrs
    #===================================================================

    # charset encoding used by file (defaults to utf-8)
    encoding = None

    # whether users() and other public methods should return unicode or bytes?
    # (defaults to False under PY2, True under PY3)
    return_unicode = None

    # if bound to local file, these will be set.
    _path = None # local file path
    _mtime = None # mtime when last loaded, or 0

    # if true, automatically save to local file after changes are made.
    autosave = False

    # ordered dict mapping key -> value for all records in database.
    # (e.g. user => hash for Htpasswd)
    _records = None

    #===================================================================
    # alt constuctors
    #===================================================================
    @classmethod
    def from_string(cls, data, **kwds):
        """create new object from raw string.

        :type data: unicode or bytes
        :arg data:
            database to load, as single string.

        :param \*\*kwds:
            all other keywords are the same as in the class constructor
        """
        if 'path' in kwds:
            raise TypeError("'path' not accepted by from_string()")
        self = cls(**kwds)
        self.load_string(data)
        return self

    @classmethod
    def from_path(cls, path, **kwds):
        """create new object from file, without binding object to file.

        :type path: str
        :arg path:
            local filepath to load from

        :param \*\*kwds:
            all other keywords are the same as in the class constructor
        """
        self = cls(**kwds)
        self.load(path)
        return self

    #===================================================================
    # init
    #===================================================================
    def __init__(self, path=None, new=False, autoload=True, autosave=False,
                 encoding="utf-8", return_unicode=PY3,
                 ):
        # set encoding
        if not encoding:
            warn("``encoding=None`` is deprecated as of Passlib 1.6, "
                 "and will cause a ValueError in Passlib 1.8, "
                 "use ``return_unicode=False`` instead.",
                 DeprecationWarning, stacklevel=2)
            encoding = "utf-8"
            return_unicode = False
        elif not is_ascii_codec(encoding):
            # htpasswd/htdigest files assumes 1-byte chars, and use ":" separator,
            # so only ascii-compatible encodings are allowed.
            raise ValueError("encoding must be 7-bit ascii compatible")
        self.encoding = encoding

        # set other attrs
        self.return_unicode = return_unicode
        self.autosave = autosave
        self._path = path
        self._mtime = 0

        # init db
        if not autoload:
            warn("``autoload=False`` is deprecated as of Passlib 1.6, "
                 "and will be removed in Passlib 1.8, use ``new=True`` instead",
                 DeprecationWarning, stacklevel=2)
            new = True
        if path and not new:
            self.load()
        else:
            self._records = OrderedDict()

    def __repr__(self):
        tail = ''
        if self.autosave:
            tail += ' autosave=True'
        if self._path:
            tail += ' path=%r' % self._path
        if self.encoding != "utf-8":
            tail += ' encoding=%r' % self.encoding
        return "<%s 0x%0x%s>" % (self.__class__.__name__, id(self), tail)

    # NOTE: ``path`` is a property so that ``_mtime`` is wiped when it's set.
    def _get_path(self):
        return self._path
    def _set_path(self, value):
        if value != self._path:
            self._mtime = 0
        self._path = value
    path = property(_get_path, _set_path)

    @property
    def mtime(self):
        """modify time when last loaded (if bound to a local file)"""
        return self._mtime

    #===================================================================
    # loading
    #===================================================================
    def load_if_changed(self):
        """Reload from ``self.path`` only if file has changed since last load"""
        if not self._path:
            raise RuntimeError("%r is not bound to a local file" % self)
        if self._mtime and self._mtime == os.path.getmtime(self._path):
            return False
        self.load()
        return True

    def load(self, path=None, force=True):
        """Load state from local file.
        If no path is specified, attempts to load from ``self.path``.

        :type path: str
        :arg path: local file to load from

        :type force: bool
        :param force:
            if ``force=False``, only load from ``self.path`` if file
            has changed since last load.

            .. deprecated:: 1.6
                This keyword will be removed in Passlib 1.8;
                Applications should use :meth:`load_if_changed` instead.
        """
        if path is not None:
            with open(path, "rb") as fh:
                self._mtime = 0
                self._load_lines(fh)
        elif not force:
            warn("%(name)s.load(force=False) is deprecated as of Passlib 1.6,"
                 "and will be removed in Passlib 1.8; "
                 "use %(name)s.load_if_changed() instead." %
                 dict(name=self.__class__.__name__),
                 DeprecationWarning, stacklevel=2)
            return self.load_if_changed()
        elif self._path:
            with open(self._path, "rb") as fh:
                self._mtime = os.path.getmtime(self._path)
                self._load_lines(fh)
        else:
            raise RuntimeError("%s().path is not set, an explicit path is required" %
                               self.__class__.__name__)
        return True

    def load_string(self, data):
        """Load state from unicode or bytes string, replacing current state"""
        data = to_bytes(data, self.encoding, "data")
        self._mtime = 0
        self._load_lines(BytesIO(data))

    def _load_lines(self, lines):
        """load from sequence of lists"""
        # XXX: found reference that "#" comment lines may be supported by
        #      htpasswd, should verify this, and figure out how to handle them.
        #      if true, this would also affect what can be stored in user field.
        # XXX: if multiple entries for a key, should we use the first one
        #      or the last one? going w/ first entry for now.
        # XXX: how should this behave if parsing fails? currently
        #      it will contain everything that was loaded up to error.
        #      could clear / restore old state instead.
        parse = self._parse_record
        records = self._records = OrderedDict()
        for idx, line in enumerate(lines):
            key, value = parse(line, idx+1)
            if key not in records:
                records[key] = value

    def _parse_record(self, record, lineno): # pragma: no cover - abstract method
        """parse line of file into (key, value) pair"""
        raise NotImplementedError("should be implemented in subclass")

    #===================================================================
    # saving
    #===================================================================
    def _autosave(self):
        """subclass helper to call save() after any changes"""
        if self.autosave and self._path:
            self.save()

    def save(self, path=None):
        """Save current state to file.
        If no path is specified, attempts to save to ``self.path``.
        """
        if path is not None:
            with open(path, "wb") as fh:
                fh.writelines(self._iter_lines())
        elif self._path:
            self.save(self._path)
            self._mtime = os.path.getmtime(self._path)
        else:
            raise RuntimeError("%s().path is not set, cannot autosave" %
                               self.__class__.__name__)

    def to_string(self):
        """Export current state as a string of bytes"""
        return join_bytes(self._iter_lines())

    def _iter_lines(self):
        """iterator yielding lines of database"""
        return (self._render_record(key,value) for key,value in iteritems(self._records))

    def _render_record(self, key, value): # pragma: no cover - abstract method
        """given key/value pair, encode as line of file"""
        raise NotImplementedError("should be implemented in subclass")

    #===================================================================
    # field encoding
    #===================================================================
    def _encode_user(self, user):
        """user-specific wrapper for _encode_field()"""
        return self._encode_field(user, "user")

    def _encode_realm(self, realm): # pragma: no cover - abstract method
        """realm-specific wrapper for _encode_field()"""
        return self._encode_field(realm, "realm")

    def _encode_field(self, value, param="field"):
        """convert field to internal representation.

        internal representation is always bytes. byte strings are left as-is,
        unicode strings encoding using file's default encoding (or ``utf-8``
        if no encoding has been specified).

        :raises UnicodeEncodeError:
            if unicode value cannot be encoded using default encoding.

        :raises ValueError:
            if resulting byte string contains a forbidden character,
            or is too long (>255 bytes).

        :returns:
            encoded identifer as bytes
        """
        if isinstance(value, unicode):
            value = value.encode(self.encoding)
        elif not isinstance(value, bytes):
            raise ExpectedStringError(value, param)
        if len(value) > 255:
            raise ValueError("%s must be at most 255 characters: %r" %
                             (param, value))
        if any(c in _INVALID_FIELD_CHARS for c in value):
            raise ValueError("%s contains invalid characters: %r" %
                             (param, value,))
        return value

    def _decode_field(self, value):
        """decode field from internal representation to format
        returns by users() method, etc.

        :raises UnicodeDecodeError:
            if unicode value cannot be decoded using default encoding.
            (usually indicates wrong encoding set for file).

        :returns:
            field as unicode or bytes, as appropriate.
        """
        assert isinstance(value, bytes), "expected value to be bytes"
        if self.return_unicode:
            return value.decode(self.encoding)
        else:
            return value

    # FIXME: htpasswd doc says passwords limited to 255 chars under Windows & MPE,
    # and that longer ones are truncated. this may be side-effect of those
    # platforms supporting the 'plaintext' scheme. these classes don't currently
    # check for this.

    #===================================================================
    # eoc
    #===================================================================

#=============================================================================
# htpasswd editing
#=============================================================================

#: default CryptContext used by HtpasswdFile
# TODO: update this to support everything in host_context (where available),
#       and note in the documentation that the default is no longer guaranteed to be portable
#       across platforms.
#       c.f. http://httpd.apache.org/docs/2.2/programs/htpasswd.html
htpasswd_context = CryptContext([
    # man page notes supported everywhere; is default on Windows, Netware, TPF
    "apr_md5_crypt",

    # [added in passlib 1.6.3]
    # apache requires host crypt() support; but can generate natively
    # (as of https://bz.apache.org/bugzilla/show_bug.cgi?id=49288)
    "bcrypt",

    # [added in passlib 1.6.3]
    # apache requires host crypt() support; and can't generate natively
    "sha256_crypt",
    "sha512_crypt",

    # man page notes apache does NOT support this on Windows, Netware, TPF
    "des_crypt",

    # man page notes intended only for transitioning htpasswd <-> ldap
    "ldap_sha1",

    # man page notes apache ONLY supports this on Windows, Netware, TPF
    "plaintext"
    ])

#: scheme that will be used when 'portable' is requested.
portable_scheme = "apr_md5_crypt"


class HtpasswdFile(_CommonFile):
    """class for reading & writing Htpasswd files.

    The class constructor accepts the following arguments:

    :type path: filepath
    :param path:

        Specifies path to htpasswd file, use to implicitly load from and save to.

        This class has two modes of operation:

        1. It can be "bound" to a local file by passing a ``path`` to the class
           constructor. In this case it will load the contents of the file when
           created, and the :meth:`load` and :meth:`save` methods will automatically
           load from and save to that file if they are called without arguments.

        2. Alternately, it can exist as an independant object, in which case
           :meth:`load` and :meth:`save` will require an explicit path to be
           provided whenever they are called. As well, ``autosave`` behavior
           will not be available.

           This feature is new in Passlib 1.6, and is the default if no
           ``path`` value is provided to the constructor.

        This is also exposed as a readonly instance attribute.

    :type new: bool
    :param new:

        Normally, if *path* is specified, :class:`HtpasswdFile` will
        immediately load the contents of the file. However, when creating
        a new htpasswd file, applications can set ``new=True`` so that
        the existing file (if any) will not be loaded.

        .. versionadded:: 1.6
            This feature was previously enabled by setting ``autoload=False``.
            That alias has been deprecated, and will be removed in Passlib 1.8

    :type autosave: bool
    :param autosave:

        Normally, any changes made to an :class:`HtpasswdFile` instance
        will not be saved until :meth:`save` is explicitly called. However,
        if ``autosave=True`` is specified, any changes made will be
        saved to disk immediately (assuming *path* has been set).

        This is also exposed as a writeable instance attribute.

    :type encoding: str
    :param encoding:

        Optionally specify character encoding used to read/write file
        and hash passwords. Defaults to ``utf-8``, though ``latin-1``
        is the only other commonly encountered encoding.

        This is also exposed as a readonly instance attribute.

    :type default_scheme: str
    :param default_scheme:
        Optionally specify default scheme to use when encoding new passwords.
        May be any of ``"bcrypt"``, ``"sha256_crypt"``, ``"apr_md5_crypt"``, ``"des_crypt"``,
        ``"ldap_sha1"``, ``"plaintext"``. It defaults to ``"apr_md5_crypt"``.

        .. note::

            Some hashes are only supported by apache / htpasswd on certain operating systems
            (e.g. bcrypt on BSD, sha256_crypt on linux).  To get the strongest
            hash that's still portable, applications can specify ``default_scheme="portable"``.

        .. versionadded:: 1.6
            This keyword was previously named ``default``. That alias
            has been deprecated, and will be removed in Passlib 1.8.

        .. versionchanged:: 1.6.3

            Added support for ``"bcrypt"``, ``"sha256_crypt"``, and ``"portable"``.

    :type context: :class:`~passlib.context.CryptContext`
    :param context:
        :class:`!CryptContext` instance used to encrypt
        and verify the hashes found in the htpasswd file.
        The default value is a pre-built context which supports all
        of the hashes officially allowed in an htpasswd file.

        This is also exposed as a readonly instance attribute.

        .. warning::

            This option may be used to add support for non-standard hash
            formats to an htpasswd file. However, the resulting file
            will probably not be usable by another application,
            and particularly not by Apache.

    :param autoload:
        Set to ``False`` to prevent the constructor from automatically
        loaded the file from disk.

        .. deprecated:: 1.6
            This has been replaced by the *new* keyword.
            Instead of setting ``autoload=False``, you should use
            ``new=True``. Support for this keyword will be removed
            in Passlib 1.8.

    :param default:
        Change the default algorithm used to encrypt new passwords.

        .. deprecated:: 1.6
            This has been renamed to *default_scheme* for clarity.
            Support for this alias will be removed in Passlib 1.8.

    Loading & Saving
    ================
    .. automethod:: load
    .. automethod:: load_if_changed
    .. automethod:: load_string
    .. automethod:: save
    .. automethod:: to_string

    Inspection
    ================
    .. automethod:: users
    .. automethod:: check_password
    .. automethod:: get_hash

    Modification
    ================
    .. automethod:: set_password
    .. automethod:: delete

    Alternate Constructors
    ======================
    .. automethod:: from_string

    Attributes
    ==========
    .. attribute:: path

        Path to local file that will be used as the default
        for all :meth:`load` and :meth:`save` operations.
        May be written to, initialized by the *path* constructor keyword.

    .. attribute:: autosave

        Writeable flag indicating whether changes will be automatically
        written to *path*.

    Errors
    ======
    :raises ValueError:
        All of the methods in this class will raise a :exc:`ValueError` if
        any user name contains a forbidden character (one of ``:\\r\\n\\t\\x00``),
        or is longer than 255 characters.
    """
    #===================================================================
    # instance attrs
    #===================================================================

    # NOTE: _records map stores <user> for the key, and <hash> for the value,
    # both in bytes which use self.encoding

    #===================================================================
    # init & serialization
    #===================================================================
    def __init__(self, path=None, default_scheme=None, context=htpasswd_context,
                 **kwds):
        if 'default' in kwds:
            warn("``default`` is deprecated as of Passlib 1.6, "
                 "and will be removed in Passlib 1.8, it has been renamed "
                 "to ``default_scheem``.",
                 DeprecationWarning, stacklevel=2)
            default_scheme = kwds.pop("default")
        if default_scheme:
            if default_scheme == "portable":
                default_scheme = portable_scheme
            context = context.copy(default=default_scheme)
        self.context = context
        super(HtpasswdFile, self).__init__(path, **kwds)

    def _parse_record(self, record, lineno):
        # NOTE: should return (user, hash) tuple
        result = record.rstrip().split(_BCOLON)
        if len(result) != 2:
            raise ValueError("malformed htpasswd file (error reading line %d)"
                             % lineno)
        return result

    def _render_record(self, user, hash):
        return render_bytes("%s:%s\n", user, hash)

    #===================================================================
    # public methods
    #===================================================================

    def users(self):
        """Return list of all users in database"""
        return [self._decode_field(user) for user in self._records]

    ##def has_user(self, user):
    ##    "check whether entry is present for user"
    ##    return self._encode_user(user) in self._records

    ##def rename(self, old, new):
    ##    """rename user account"""
    ##    old = self._encode_user(old)
    ##    new = self._encode_user(new)
    ##    hash = self._records.pop(old)
    ##    self._records[new] = hash
    ##    self._autosave()

    def set_password(self, user, password):
        """Set password for user; adds user if needed.

        :returns:
            * ``True`` if existing user was updated.
            * ``False`` if user account was added.

        .. versionchanged:: 1.6
            This method was previously called ``update``, it was renamed
            to prevent ambiguity with the dictionary method.
            The old alias is deprecated, and will be removed in Passlib 1.8.
        """
        user = self._encode_user(user)
        hash = self.context.encrypt(password)
        if PY3:
            hash = hash.encode(self.encoding)
        existing = (user in self._records)
        self._records[user] = hash
        self._autosave()
        return existing

    @deprecated_method(deprecated="1.6", removed="1.8",
                       replacement="set_password")
    def update(self, user, password):
        """set password for user"""
        return self.set_password(user, password)

    def get_hash(self, user):
        """Return hash stored for user, or ``None`` if user not found.

        .. versionchanged:: 1.6
            This method was previously named ``find``, it was renamed
            for clarity. The old name is deprecated, and will be removed
            in Passlib 1.8.
        """
        try:
            return self._records[self._encode_user(user)]
        except KeyError:
            return None

    @deprecated_method(deprecated="1.6", removed="1.8",
                       replacement="get_hash")
    def find(self, user):
        """return hash for user"""
        return self.get_hash(user)

    # XXX: rename to something more explicit, like delete_user()?
    def delete(self, user):
        """Delete user's entry.

        :returns:
            * ``True`` if user deleted.
            * ``False`` if user not found.
        """
        try:
            del self._records[self._encode_user(user)]
        except KeyError:
            return False
        self._autosave()
        return True

    def check_password(self, user, password):
        """Verify password for specified user.

        :returns:
            * ``None`` if user not found.
            * ``False`` if user found, but password does not match.
            * ``True`` if user found and password matches.

        .. versionchanged:: 1.6
            This method was previously called ``verify``, it was renamed
            to prevent ambiguity with the :class:`!CryptContext` method.
            The old alias is deprecated, and will be removed in Passlib 1.8.
        """
        user = self._encode_user(user)
        hash = self._records.get(user)
        if hash is None:
            return None
        if isinstance(password, unicode):
            # NOTE: encoding password to match file, making the assumption
            # that server will use same encoding to hash the password.
            password = password.encode(self.encoding)
        ok, new_hash = self.context.verify_and_update(password, hash)
        if ok and new_hash is not None:
            # rehash user's password if old hash was deprecated
            self._records[user] = new_hash
            self._autosave()
        return ok

    @deprecated_method(deprecated="1.6", removed="1.8",
                       replacement="check_password")
    def verify(self, user, password):
        """verify password for user"""
        return self.check_password(user, password)

    #===================================================================
    # eoc
    #===================================================================

#=============================================================================
# htdigest editing
#=============================================================================
class HtdigestFile(_CommonFile):
    """class for reading & writing Htdigest files.

    The class constructor accepts the following arguments:

    :type path: filepath
    :param path:

        Specifies path to htdigest file, use to implicitly load from and save to.

        This class has two modes of operation:

        1. It can be "bound" to a local file by passing a ``path`` to the class
           constructor. In this case it will load the contents of the file when
           created, and the :meth:`load` and :meth:`save` methods will automatically
           load from and save to that file if they are called without arguments.

        2. Alternately, it can exist as an independant object, in which case
           :meth:`load` and :meth:`save` will require an explicit path to be
           provided whenever they are called. As well, ``autosave`` behavior
           will not be available.

           This feature is new in Passlib 1.6, and is the default if no
           ``path`` value is provided to the constructor.

        This is also exposed as a readonly instance attribute.

    :type default_realm: str
    :param default_realm:

        If ``default_realm`` is set, all the :class:`HtdigestFile`
        methods that require a realm will use this value if one is not
        provided explicitly. If unset, they will raise an error stating
        that an explicit realm is required.

        This is also exposed as a writeable instance attribute.

        .. versionadded:: 1.6

    :type new: bool
    :param new:

        Normally, if *path* is specified, :class:`HtdigestFile` will
        immediately load the contents of the file. However, when creating
        a new htpasswd file, applications can set ``new=True`` so that
        the existing file (if any) will not be loaded.

        .. versionadded:: 1.6
            This feature was previously enabled by setting ``autoload=False``.
            That alias has been deprecated, and will be removed in Passlib 1.8

    :type autosave: bool
    :param autosave:

        Normally, any changes made to an :class:`HtdigestFile` instance
        will not be saved until :meth:`save` is explicitly called. However,
        if ``autosave=True`` is specified, any changes made will be
        saved to disk immediately (assuming *path* has been set).

        This is also exposed as a writeable instance attribute.

    :type encoding: str
    :param encoding:

        Optionally specify character encoding used to read/write file
        and hash passwords. Defaults to ``utf-8``, though ``latin-1``
        is the only other commonly encountered encoding.

        This is also exposed as a readonly instance attribute.

    :param autoload:
        Set to ``False`` to prevent the constructor from automatically
        loaded the file from disk.

        .. deprecated:: 1.6
            This has been replaced by the *new* keyword.
            Instead of setting ``autoload=False``, you should use
            ``new=True``. Support for this keyword will be removed
            in Passlib 1.8.

    Loading & Saving
    ================
    .. automethod:: load
    .. automethod:: load_if_changed
    .. automethod:: load_string
    .. automethod:: save
    .. automethod:: to_string

    Inspection
    ==========
    .. automethod:: realms
    .. automethod:: users
    .. automethod:: check_password(user[, realm], password)
    .. automethod:: get_hash

    Modification
    ============
    .. automethod:: set_password(user[, realm], password)
    .. automethod:: delete
    .. automethod:: delete_realm

    Alternate Constructors
    ======================
    .. automethod:: from_string

    Attributes
    ==========
    .. attribute:: default_realm

        The default realm that will be used if one is not provided
        to methods that require it. By default this is ``None``,
        in which case an explicit realm must be provided for every
        method call. Can be written to.

    .. attribute:: path

        Path to local file that will be used as the default
        for all :meth:`load` and :meth:`save` operations.
        May be written to, initialized by the *path* constructor keyword.

    .. attribute:: autosave

        Writeable flag indicating whether changes will be automatically
        written to *path*.

    Errors
    ======
    :raises ValueError:
        All of the methods in this class will raise a :exc:`ValueError` if
        any user name or realm contains a forbidden character (one of ``:\\r\\n\\t\\x00``),
        or is longer than 255 characters.
    """
    #===================================================================
    # instance attrs
    #===================================================================

    # NOTE: _records map stores (<user>,<realm>) for the key,
    # and <hash> as the value, all as <self.encoding> bytes.

    # NOTE: unlike htpasswd, this class doesn't use a CryptContext,
    # as only one hash format is supported: htdigest.

    # optionally specify default realm that will be used if none
    # is provided to a method call. otherwise realm is always required.
    default_realm = None

    #===================================================================
    # init & serialization
    #===================================================================
    def __init__(self, path=None, default_realm=None, **kwds):
        self.default_realm = default_realm
        super(HtdigestFile, self).__init__(path, **kwds)

    def _parse_record(self, record, lineno):
        result = record.rstrip().split(_BCOLON)
        if len(result) != 3:
            raise ValueError("malformed htdigest file (error reading line %d)"
                             % lineno)
        user, realm, hash = result
        return (user, realm), hash

    def _render_record(self, key, hash):
        user, realm = key
        return render_bytes("%s:%s:%s\n", user, realm, hash)

    def _encode_realm(self, realm):
        # override default _encode_realm to fill in default realm field
        if realm is None:
            realm = self.default_realm
            if realm is None:
                raise TypeError("you must specify a realm explicitly, "
                                  "or set the default_realm attribute")
        return self._encode_field(realm, "realm")

    #===================================================================
    # public methods
    #===================================================================

    def realms(self):
        """Return list of all realms in database"""
        realms = set(key[1] for key in self._records)
        return [self._decode_field(realm) for realm in realms]

    def users(self, realm=None):
        """Return list of all users in specified realm.

        * uses ``self.default_realm`` if no realm explicitly provided.
        * returns empty list if realm not found.
        """
        realm = self._encode_realm(realm)
        return [self._decode_field(key[0]) for key in self._records
                if key[1] == realm]

    ##def has_user(self, user, realm=None):
    ##    "check if user+realm combination exists"
    ##    user = self._encode_user(user)
    ##    realm = self._encode_realm(realm)
    ##    return (user,realm) in self._records

    ##def rename_realm(self, old, new):
    ##    """rename all accounts in realm"""
    ##    old = self._encode_realm(old)
    ##    new = self._encode_realm(new)
    ##    keys = [key for key in self._records if key[1] == old]
    ##    for key in keys:
    ##        hash = self._records.pop(key)
    ##        self._records[key[0],new] = hash
    ##    self._autosave()
    ##    return len(keys)

    ##def rename(self, old, new, realm=None):
    ##    """rename user account"""
    ##    old = self._encode_user(old)
    ##    new = self._encode_user(new)
    ##    realm = self._encode_realm(realm)
    ##    hash = self._records.pop((old,realm))
    ##    self._records[new,realm] = hash
    ##    self._autosave()

    def set_password(self, user, realm=None, password=_UNSET):
        """Set password for user; adds user & realm if needed.

        If ``self.default_realm`` has been set, this may be called
        with the syntax ``set_password(user, password)``,
        otherwise it must be called with all three arguments:
        ``set_password(user, realm, password)``.

        :returns:
            * ``True`` if existing user was updated
            * ``False`` if user account added.
        """
        if password is _UNSET:
            # called w/ two args - (user, password), use default realm
            realm, password = None, realm
        user = self._encode_user(user)
        realm = self._encode_realm(realm)
        key = (user, realm)
        existing = (key in self._records)
        hash = htdigest.encrypt(password, user, realm, encoding=self.encoding)
        if PY3:
            hash = hash.encode(self.encoding)
        self._records[key] = hash
        self._autosave()
        return existing

    @deprecated_method(deprecated="1.6", removed="1.8",
                       replacement="set_password")
    def update(self, user, realm, password):
        """set password for user"""
        return self.set_password(user, realm, password)

    # XXX: rename to something more explicit, like get_hash()?
    def get_hash(self, user, realm=None):
        """Return :class:`~passlib.hash.htdigest` hash stored for user.

        * uses ``self.default_realm`` if no realm explicitly provided.
        * returns ``None`` if user or realm not found.

        .. versionchanged:: 1.6
            This method was previously named ``find``, it was renamed
            for clarity. The old name is deprecated, and will be removed
            in Passlib 1.8.
        """
        key = (self._encode_user(user), self._encode_realm(realm))
        hash = self._records.get(key)
        if hash is None:
            return None
        if PY3:
            hash = hash.decode(self.encoding)
        return hash

    @deprecated_method(deprecated="1.6", removed="1.8",
                       replacement="get_hash")
    def find(self, user, realm):
        """return hash for user"""
        return self.get_hash(user, realm)

    # XXX: rename to something more explicit, like delete_user()?
    def delete(self, user, realm=None):
        """Delete user's entry for specified realm.

        if realm is not specified, uses ``self.default_realm``.

        :returns:
            * ``True`` if user deleted,
            * ``False`` if user not found in realm.
        """
        key = (self._encode_user(user), self._encode_realm(realm))
        try:
            del self._records[key]
        except KeyError:
            return False
        self._autosave()
        return True

    def delete_realm(self, realm):
        """Delete all users for specified realm.

        if realm is not specified, uses ``self.default_realm``.

        :returns: number of users deleted (0 if realm not found)
        """
        realm = self._encode_realm(realm)
        records = self._records
        keys = [key for key in records if key[1] == realm]
        for key in keys:
            del records[key]
        self._autosave()
        return len(keys)

    def check_password(self, user, realm=None, password=_UNSET):
        """Verify password for specified user + realm.

        If ``self.default_realm`` has been set, this may be called
        with the syntax ``check_password(user, password)``,
        otherwise it must be called with all three arguments:
        ``check_password(user, realm, password)``.

        :returns:
            * ``None`` if user or realm not found.
            * ``False`` if user found, but password does not match.
            * ``True`` if user found and password matches.

        .. versionchanged:: 1.6
            This method was previously called ``verify``, it was renamed
            to prevent ambiguity with the :class:`!CryptContext` method.
            The old alias is deprecated, and will be removed in Passlib 1.8.
        """
        if password is _UNSET:
            # called w/ two args - (user, password), use default realm
            realm, password = None, realm
        user = self._encode_user(user)
        realm = self._encode_realm(realm)
        hash = self._records.get((user,realm))
        if hash is None:
            return None
        return htdigest.verify(password, hash, user, realm,
                               encoding=self.encoding)

    @deprecated_method(deprecated="1.6", removed="1.8",
                       replacement="check_password")
    def verify(self, user, realm, password):
        """verify password for user"""
        return self.check_password(user, realm, password)

    #===================================================================
    # eoc
    #===================================================================

#=============================================================================
# eof
#=============================================================================
