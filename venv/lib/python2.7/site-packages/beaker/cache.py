"""This package contains the "front end" classes and functions
for Beaker caching.

Included are the :class:`.Cache` and :class:`.CacheManager` classes,
as well as the function decorators :func:`.region_decorate`,
:func:`.region_invalidate`.

"""
import warnings
from itertools import chain

from beaker._compat import u_, unicode_text, func_signature, bindfuncargs
import beaker.container as container
import beaker.util as util
from beaker.crypto.util import sha1
from beaker.exceptions import BeakerException, InvalidCacheBackendError
from beaker.synchronization import _threading

import beaker.ext.memcached as memcached
import beaker.ext.database as database
import beaker.ext.sqla as sqla
import beaker.ext.google as google
import beaker.ext.mongodb as mongodb
import beaker.ext.redisnm as redisnm
from functools import wraps

# Initialize the cache region dict
cache_regions = {}
"""Dictionary of 'region' arguments.

A "region" is a string name that refers to a series of cache
configuration arguments.    An application may have multiple
"regions" - one which stores things in a memory cache, one
which writes data to files, etc.

The dictionary stores string key names mapped to dictionaries
of configuration arguments.  Example::

    from beaker.cache import cache_regions
    cache_regions.update({
        'short_term':{
            'expire':60,
            'type':'memory'
        },
        'long_term':{
            'expire':1800,
            'type':'dbm',
            'data_dir':'/tmp',
        }
    })
"""


cache_managers = {}


class _backends(object):
    initialized = False

    def __init__(self, clsmap):
        self._clsmap = clsmap
        self._mutex = _threading.Lock()

    def __getitem__(self, key):
        try:
            return self._clsmap[key]
        except KeyError as e:
            if not self.initialized:
                self._mutex.acquire()
                try:
                    if not self.initialized:
                        self._init()
                        self.initialized = True

                    return self._clsmap[key]
                finally:
                    self._mutex.release()

            raise e

    def _init(self):
        try:
            import pkg_resources

            # Load up the additional entry point defined backends
            for entry_point in pkg_resources.iter_entry_points('beaker.backends'):
                try:
                    namespace_manager = entry_point.load()
                    name = entry_point.name
                    if name in self._clsmap:
                        raise BeakerException("NamespaceManager name conflict,'%s' "
                                              "already loaded" % name)
                    self._clsmap[name] = namespace_manager
                except (InvalidCacheBackendError, SyntaxError):
                    # Ignore invalid backends
                    pass
                except:
                    import sys
                    from pkg_resources import DistributionNotFound
                    # Warn when there's a problem loading a NamespaceManager
                    if not isinstance(sys.exc_info()[1], DistributionNotFound):
                        import traceback
                        try:
                            from StringIO import StringIO  # Python2
                        except ImportError:
                            from io import StringIO        # Python3

                        tb = StringIO()
                        traceback.print_exc(file=tb)
                        warnings.warn(
                            "Unable to load NamespaceManager "
                            "entry point: '%s': %s" % (
                                        entry_point,
                                        tb.getvalue()),
                                        RuntimeWarning, 2)
        except ImportError:
            pass

# Initialize the basic available backends
clsmap = _backends({
    'memory': container.MemoryNamespaceManager,
    'dbm': container.DBMNamespaceManager,
    'file': container.FileNamespaceManager,
    'ext:memcached': memcached.MemcachedNamespaceManager,
    'ext:database': database.DatabaseNamespaceManager,
    'ext:sqla': sqla.SqlaNamespaceManager,
    'ext:google': google.GoogleNamespaceManager,
    'ext:mongodb': mongodb.MongoNamespaceManager,
    'ext:redis': redisnm.RedisNamespaceManager
})


def cache_region(region, *args):
    """Decorate a function such that its return result is cached,
    using a "region" to indicate the cache arguments.

    Example::

        from beaker.cache import cache_regions, cache_region

        # configure regions
        cache_regions.update({
            'short_term':{
                'expire':60,
                'type':'memory'
            }
        })

        @cache_region('short_term', 'load_things')
        def load(search_term, limit, offset):
            '''Load from a database given a search term, limit, offset.'''
            return database.query(search_term)[offset:offset + limit]

    The decorator can also be used with object methods.  The ``self``
    argument is not part of the cache key.  This is based on the
    actual string name ``self`` being in the first argument
    position (new in 1.6)::

        class MyThing(object):
            @cache_region('short_term', 'load_things')
            def load(self, search_term, limit, offset):
                '''Load from a database given a search term, limit, offset.'''
                return database.query(search_term)[offset:offset + limit]

    Classmethods work as well - use ``cls`` as the name of the class argument,
    and place the decorator around the function underneath ``@classmethod``
    (new in 1.6)::

        class MyThing(object):
            @classmethod
            @cache_region('short_term', 'load_things')
            def load(cls, search_term, limit, offset):
                '''Load from a database given a search term, limit, offset.'''
                return database.query(search_term)[offset:offset + limit]

    :param region: String name of the region corresponding to the desired
      caching arguments, established in :attr:`.cache_regions`.

    :param \*args: Optional ``str()``-compatible arguments which will uniquely
      identify the key used by this decorated function, in addition
      to the positional arguments passed to the function itself at call time.
      This is recommended as it is needed to distinguish between any two functions
      or methods that have the same name (regardless of parent class or not).

    .. note::

        The function being decorated must only be called with
        positional arguments, and the arguments must support
        being stringified with ``str()``.  The concatenation
        of the ``str()`` version of each argument, combined
        with that of the ``*args`` sent to the decorator,
        forms the unique cache key.

    .. note::

        When a method on a class is decorated, the ``self`` or ``cls``
        argument in the first position is
        not included in the "key" used for caching.   New in 1.6.

    """
    return _cache_decorate(args, None, None, region)


def region_invalidate(namespace, region, *args):
    """Invalidate a cache region corresponding to a function
    decorated with :func:`.cache_region`.

    :param namespace: The namespace of the cache to invalidate.  This is typically
      a reference to the original function (as returned by the :func:`.cache_region`
      decorator), where the :func:`.cache_region` decorator applies a "memo" to
      the function in order to locate the string name of the namespace.

    :param region: String name of the region used with the decorator.  This can be
     ``None`` in the usual case that the decorated function itself is passed,
     not the string name of the namespace.

    :param args: Stringifyable arguments that are used to locate the correct
     key.  This consists of the ``*args`` sent to the :func:`.cache_region`
     decorator itself, plus the ``*args`` sent to the function itself
     at runtime.

    Example::

        from beaker.cache import cache_regions, cache_region, region_invalidate

        # configure regions
        cache_regions.update({
            'short_term':{
                'expire':60,
                'type':'memory'
            }
        })

        @cache_region('short_term', 'load_data')
        def load(search_term, limit, offset):
            '''Load from a database given a search term, limit, offset.'''
            return database.query(search_term)[offset:offset + limit]

        def invalidate_search(search_term, limit, offset):
            '''Invalidate the cached storage for a given search term, limit, offset.'''
            region_invalidate(load, 'short_term', 'load_data', search_term, limit, offset)

    Note that when a method on a class is decorated, the first argument ``cls``
    or ``self`` is not included in the cache key.  This means you don't send
    it to :func:`.region_invalidate`::

        class MyThing(object):
            @cache_region('short_term', 'some_data')
            def load(self, search_term, limit, offset):
                '''Load from a database given a search term, limit, offset.'''
                return database.query(search_term)[offset:offset + limit]

            def invalidate_search(self, search_term, limit, offset):
                '''Invalidate the cached storage for a given search term, limit, offset.'''
                region_invalidate(self.load, 'short_term', 'some_data', search_term, limit, offset)

    """
    if callable(namespace):
        if not region:
            region = namespace._arg_region
        namespace = namespace._arg_namespace

    if not region:
        raise BeakerException("Region or callable function "
                                    "namespace is required")
    else:
        region = cache_regions[region]

    cache = Cache._get_cache(namespace, region)
    _cache_decorator_invalidate(cache,
                                region.get('key_length', util.DEFAULT_CACHE_KEY_LENGTH),
                                args)


class Cache(object):
    """Front-end to the containment API implementing a data cache.

    :param namespace: the namespace of this Cache

    :param type: type of cache to use

    :param expire: seconds to keep cached data

    :param expiretime: seconds to keep cached data (legacy support)

    :param starttime: time when cache was cache was

    """
    def __init__(self, namespace, type='memory', expiretime=None,
                 starttime=None, expire=None, **nsargs):
        try:
            cls = clsmap[type]
            if isinstance(cls, InvalidCacheBackendError):
                raise cls
        except KeyError:
            raise TypeError("Unknown cache implementation %r" % type)

        if expire is not None:
            expire = int(expire)

        self.namespace_name = namespace
        self.namespace = cls(namespace, **nsargs)
        self.expiretime = expiretime or expire
        self.starttime = starttime
        self.nsargs = nsargs

    @classmethod
    def _get_cache(cls, namespace, kw):
        key = namespace + str(kw)
        try:
            return cache_managers[key]
        except KeyError:
            cache_managers[key] = cache = cls(namespace, **kw)
            return cache

    def put(self, key, value, **kw):
        self._get_value(key, **kw).set_value(value)
    set_value = put

    def get(self, key, **kw):
        """Retrieve a cached value from the container"""
        return self._get_value(key, **kw).get_value()
    get_value = get

    def remove_value(self, key, **kw):
        mycontainer = self._get_value(key, **kw)
        mycontainer.clear_value()
    remove = remove_value

    def _get_value(self, key, **kw):
        if isinstance(key, unicode_text):
            key = key.encode('ascii', 'backslashreplace')

        if 'type' in kw:
            return self._legacy_get_value(key, **kw)

        kw.setdefault('expiretime', self.expiretime)
        kw.setdefault('starttime', self.starttime)

        return container.Value(key, self.namespace, **kw)

    @util.deprecated("Specifying a "
            "'type' and other namespace configuration with cache.get()/put()/etc. "
            "is deprecated. Specify 'type' and other namespace configuration to "
            "cache_manager.get_cache() and/or the Cache constructor instead.")
    def _legacy_get_value(self, key, type, **kw):
        expiretime = kw.pop('expiretime', self.expiretime)
        starttime = kw.pop('starttime', None)
        createfunc = kw.pop('createfunc', None)
        kwargs = self.nsargs.copy()
        kwargs.update(kw)
        c = Cache(self.namespace.namespace, type=type, **kwargs)
        return c._get_value(key, expiretime=expiretime, createfunc=createfunc,
                            starttime=starttime)

    def clear(self):
        """Clear all the values from the namespace"""
        self.namespace.remove()

    # dict interface
    def __getitem__(self, key):
        return self.get(key)

    def __contains__(self, key):
        return self._get_value(key).has_current_value()

    def has_key(self, key):
        return key in self

    def __delitem__(self, key):
        self.remove_value(key)

    def __setitem__(self, key, value):
        self.put(key, value)


class CacheManager(object):
    def __init__(self, **kwargs):
        """Initialize a CacheManager object with a set of options

        Options should be parsed with the
        :func:`~beaker.util.parse_cache_config_options` function to
        ensure only valid options are used.

        """
        self.kwargs = kwargs
        self.regions = kwargs.pop('cache_regions', {})

        # Add these regions to the module global
        cache_regions.update(self.regions)

    def get_cache(self, name, **kwargs):
        kw = self.kwargs.copy()
        kw.update(kwargs)
        return Cache._get_cache(name, kw)

    def get_cache_region(self, name, region):
        if region not in self.regions:
            raise BeakerException('Cache region not configured: %s' % region)
        kw = self.regions[region]
        return Cache._get_cache(name, kw)

    def region(self, region, *args):
        """Decorate a function to cache itself using a cache region

        The region decorator requires arguments if there are more than
        two of the same named function, in the same module. This is
        because the namespace used for the functions cache is based on
        the functions name and the module.


        Example::

            # Assuming a cache object is available like:
            cache = CacheManager(dict_of_config_options)


            def populate_things():

                @cache.region('short_term', 'some_data')
                def load(search_term, limit, offset):
                    return load_the_data(search_term, limit, offset)

                return load('rabbits', 20, 0)

        .. note::

            The function being decorated must only be called with
            positional arguments.

        """
        return cache_region(region, *args)

    def region_invalidate(self, namespace, region, *args):
        """Invalidate a cache region namespace or decorated function

        This function only invalidates cache spaces created with the
        cache_region decorator.

        :param namespace: Either the namespace of the result to invalidate, or the
           cached function

        :param region: The region the function was cached to. If the function was
            cached to a single region then this argument can be None

        :param args: Arguments that were used to differentiate the cached
            function as well as the arguments passed to the decorated
            function

        Example::

            # Assuming a cache object is available like:
            cache = CacheManager(dict_of_config_options)

            def populate_things(invalidate=False):

                @cache.region('short_term', 'some_data')
                def load(search_term, limit, offset):
                    return load_the_data(search_term, limit, offset)

                # If the results should be invalidated first
                if invalidate:
                    cache.region_invalidate(load, None, 'some_data',
                                            'rabbits', 20, 0)
                return load('rabbits', 20, 0)


        """
        return region_invalidate(namespace, region, *args)

    def cache(self, *args, **kwargs):
        """Decorate a function to cache itself with supplied parameters

        :param args: Used to make the key unique for this function, as in region()
            above.

        :param kwargs: Parameters to be passed to get_cache(), will override defaults

        Example::

            # Assuming a cache object is available like:
            cache = CacheManager(dict_of_config_options)


            def populate_things():

                @cache.cache('mycache', expire=15)
                def load(search_term, limit, offset):
                    return load_the_data(search_term, limit, offset)

                return load('rabbits', 20, 0)

        .. note::

            The function being decorated must only be called with
            positional arguments.

        """
        return _cache_decorate(args, self, kwargs, None)

    def invalidate(self, func, *args, **kwargs):
        """Invalidate a cache decorated function

        This function only invalidates cache spaces created with the
        cache decorator.

        :param func: Decorated function to invalidate

        :param args: Used to make the key unique for this function, as in region()
            above.

        :param kwargs: Parameters that were passed for use by get_cache(), note that
            this is only required if a ``type`` was specified for the
            function

        Example::

            # Assuming a cache object is available like:
            cache = CacheManager(dict_of_config_options)


            def populate_things(invalidate=False):

                @cache.cache('mycache', type="file", expire=15)
                def load(search_term, limit, offset):
                    return load_the_data(search_term, limit, offset)

                # If the results should be invalidated first
                if invalidate:
                    cache.invalidate(load, 'mycache', 'rabbits', 20, 0, type="file")
                return load('rabbits', 20, 0)

        """
        namespace = func._arg_namespace

        cache = self.get_cache(namespace, **kwargs)
        if hasattr(func, '_arg_region'):
            cachereg = cache_regions[func._arg_region]
            key_length = cachereg.get('key_length', util.DEFAULT_CACHE_KEY_LENGTH)
        else:
            key_length = kwargs.pop('key_length', util.DEFAULT_CACHE_KEY_LENGTH)
        _cache_decorator_invalidate(cache, key_length, args)


def _cache_decorate(deco_args, manager, options, region):
    """Return a caching function decorator."""

    cache = [None]

    def decorate(func):
        namespace = util.func_namespace(func)
        skip_self = util.has_self_arg(func)
        signature = func_signature(func)

        @wraps(func)
        def cached(*args, **kwargs):
            if not cache[0]:
                if region is not None:
                    if region not in cache_regions:
                        raise BeakerException(
                            'Cache region not configured: %s' % region)
                    reg = cache_regions[region]
                    if not reg.get('enabled', True):
                        return func(*args, **kwargs)
                    cache[0] = Cache._get_cache(namespace, reg)
                elif manager:
                    cache[0] = manager.get_cache(namespace, **options)
                else:
                    raise Exception("'manager + kwargs' or 'region' "
                                    "argument is required")

            cache_key_kwargs = []
            if kwargs:
                # kwargs provided, merge them in positional args
                # to avoid having different cache keys.
                args, kwargs = bindfuncargs(signature, args, kwargs)
                cache_key_kwargs = [u_(':').join((u_(key), u_(value))) for key, value in kwargs.items()]

            cache_key_args = args
            if skip_self:
                cache_key_args = args[1:]

            cache_key = u_(" ").join(map(u_, chain(deco_args, cache_key_args, cache_key_kwargs)))

            if region:
                cachereg = cache_regions[region]
                key_length = cachereg.get('key_length', util.DEFAULT_CACHE_KEY_LENGTH)
            else:
                key_length = options.pop('key_length', util.DEFAULT_CACHE_KEY_LENGTH)

            # TODO: This is probably a bug as length is checked before converting to UTF8
            # which will cause cache_key to grow in size.
            if len(cache_key) + len(namespace) > int(key_length):
                cache_key = sha1(cache_key.encode('utf-8')).hexdigest()

            def go():
                return func(*args, **kwargs)
            # save org function name
            go.__name__ = '_cached_%s' % (func.__name__,)

            return cache[0].get_value(cache_key, createfunc=go)
        cached._arg_namespace = namespace
        if region is not None:
            cached._arg_region = region
        return cached
    return decorate


def _cache_decorator_invalidate(cache, key_length, args):
    """Invalidate a cache key based on function arguments."""

    cache_key = u_(" ").join(map(u_, args))
    if len(cache_key) + len(cache.namespace_name) > key_length:
        cache_key = sha1(cache_key.encode('utf-8')).hexdigest()
    cache.remove_value(cache_key)
