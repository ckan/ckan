New option `ckan jobs worker --with-scheduler` will schedule jobs
as well as run jobs in the queue.

`datastore_create`, `datastore_upsert` and `datastore_delete` now
schedule a job to patch the corresponding resource's `last_modified`
value for datastore-first resources. A scheduled job is used to
reduce duplicated metadata updates that would slow down these
operations.
