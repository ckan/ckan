feature/performance: Improved caching and ETag handling

- Webassets (static files) now support configurable ETag and Cache-Control headers.
  See `ckan.cache.*` and `ckan.etag.enabled` for included configuration options.
  By default, assets will use strong ETags and try to not include vary on cookie unless session was modified prior to render.

- **Config changes:**
  - Renamed:
    - `ckan.cache_expires` → `ckan.cache.expires` (default: 3600)
    - `ckan.cache_enabled` → `ckan.cache.public.enabled` (boolean, default: True)
  - New config keys:
    - `ckan.cache.private.enabled` (default: True)
    - `ckan.cache.shared.expires` (default: 7200)
    - `ckan.cache.private.expires` (default: 60)
    - `ckan.cache.stale_while_revalidates` (default: 3600)
    - `ckan.cache.stale_if_error` (default: 86400)
    - `ckan.cache.no_transform` (default: False)
    - `ckan.etags.enabled` (default: True)

- **Cache-Control Header Behavior:**
  - If `ckan.cache.public.enabled` is `False`, all responses include `Cache-Control: private`.
  - If `ckan.cache.public.enabled` is `True` and the user is not logged in, `Cache-Control: public` is set.
  - If `ckan.cache.private.enabled` is `False`, private responses use at least `Cache-Control: no-cache`.
  - When the session is modified or a `Set-Cookie` is present, `Cache-Control: no-store` prevents caching.
  - Incoming `Cache-Control` headers are respected in responses.

- **New core helpers:**
  - `cache_level`, `set_cache_level`: Get/set cache type (in Flask's `g` context).
  - `limit_cache_for_page`, `set_limit_cache_for_page`: Control per-page cache limits.
  - `etag_append`, `set_etag_replace`, `set_etag_modified_time`: Advanced ETag customization.

- **Plugin Example:**
  - Added `example_etags` plugin demonstrating MD5 content hashing with the new interface.

- **Interface Updates (`IMiddleware`):**
  - New methods for plugins to override response headers:
    - `set_cors_headers_for_response(self, response)`
    - `set_cache_control_headers_for_response(self, response)`
    - `set_etag_for_response(self, response)`

---

**Summary:**
These changes improve caching flexibility, allow for fine-grained ETag and Cache-Control behavior, and introduce new helpers and plugin interfaces for advanced cache/header control.
