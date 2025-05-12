feature: Enable etag and better cache control header settings


config altered keys:
* ``ckan.cache_expires`` renamed to ``ckan.cache.expires``
  default value set to 3600
* ``ckan.cache_enabled`` renamed to ``ckan.cache.public.enabled``
  ckan.cache.public.enabled is boolean, default True

config new keys:

* ckan.cache.private.enabled: default True
* ckan.cache.private.expires: int
* ckan.cache.stale_while_revalidates: default 0
* ckan.cache.stale_if_error: default 0
* ckan.cache.no_transform: default False
* ckan.etags.enabled: default True

plugin etag, md5 content hashing plugin


When ``ckan.cache.public.enabled`` is set to ``False`` all requests
include the ``Cache-control: private`` header. If ``ckan.cache.public.enabled`` is
set to ``True``, when the user is not logged in and there is no session data,
a ``Cache-Control: public`` header will be added.
When ``ckan.cache.private.enabled`` is set to ''False`` all requests
which were meant to be private is configured for at least ``Cache-control: no-cache``
When session is modified or ``Set-Cookie`` is found in response, then ``Cache-control``
is set to ``no-store`` to ensure cookies never end up in cache.
