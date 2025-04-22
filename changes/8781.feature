feature: Enable etag and better cache control header settings
* ckan.private_cache_expires: optional int
* ckan.cache_private_enabled: default True
* ckan.cache_etags: default True
* ckan.cache_etags_notModified: default True
* fix: ckan.cache_enabled now treated as bool instead of just not set
