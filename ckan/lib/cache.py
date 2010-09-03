from time import gmtime, mktime, strftime, time
from decorator import decorator

from paste.deploy.converters import asbool
from pylons.decorators.cache import beaker_cache, create_cache_key, _make_dict_from_args
import pylons

def cache(test=lambda: 0,
          key="cache_default",
          expires=900,
          type=None,
          query_args=False,
          cache_headers=('content-type', 'content-length',),
          **cache_kwargs):
    cache_headers = set(cache_headers)
    def wrapper(func, *args, **kwargs):
        enabled = pylons.config.get("cache_enabled", "True")
        if not asbool(enabled):
            return func(*args, **kwargs)

        # this section copies entirely too much from beaker cache
        if key:
            if query_args:
                key_dict = request.GET.mixed()
            else:
                key_dict = kwargs.copy()
                key_dict.update(_make_dict_from_args(func, args))
            if key != "cache_default":
                if isinstance(key, list):
                    key_dict = dict((k, key_dict[k]) for k in key)
                else:
                    key_dict = {key: key_dict[key]}
            else:
                key_dict = None

        self = None
        if args:
            self = args[0]

        namespace, cache_key = create_cache_key(func, key_dict, self)

        if type:
            cache_kwargs["type"] = type
        my_cache = pylons.cache.get_cache(namespace, **cache_kwargs)

        ## end copy from beaker_cache
        
        last_modified = test()
        cache_miss = list()
        
        def render():
            result = func(*args, **kwargs)
            glob_response = pylons.response
            headers = glob_response.headers
            status = glob_response.status
            full_response = dict(headers=headers, status=status,
                                 cookies=None, content=result,
                                 timestamp=last_modified)
            cache_miss.append(True)
            return full_response

        response = my_cache.get_value(cache_key, createfunc=render)
        timestamp = response["timestamp"]
        if timestamp < last_modified:
            my_cache.remove(cache_key)
        response = my_cache.get_value(cache_key, createfunc=render)
        
        glob_response = pylons.response
        headers = dict(glob_response.headerlist)
        headers.update(header for header in response["headers"]
                       if header[0].lower() in cache_headers)

        if "Pragma" in headers: del headers["Pragma"]
        if "Cache-Control" in headers: del headers["Cache-Control"]
        headers["Last-Modified"] = strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime(last_modified))
        if cache_miss:
            headers["X-CKAN-Cache"] = "MISS"
        else:
            headers["X-CKAN-Cache"] = "HIT"

        glob_response.headerlist = headers.items()

        glob_response.cache_expires(seconds=expires)
        cc = glob_response.headers["Cache-Control"]
        glob_response.headers["Cache-Control"] = "%s, must-revalidate" % cc
        
        glob_response.status = response['status']

        return response["content"]

    return decorator(wrapper)
