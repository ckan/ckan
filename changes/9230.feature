Added a `ckan.site_lockdown` config option which disables actions causing side effects,
such as `*_create`, `*_update`, and `*_delete`, for non-sysadmin users.

This setting does not prevent updates to the database from sysadmin users or updates
that skip the action API, such as collecting page view tracking data.
