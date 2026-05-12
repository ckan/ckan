`ckan jobs worker` CLI now runs a scheduler by default to enqueue
scheduled jobs. Use `--no-scheduler` to disable the scheduler on this
worker. Only one worker can run as a scheduler for each queue so this
option may be used on secondary workers.

`datastore_create`, `datastore_upsert` and `datastore_delete` now
schedule a job to patch the corresponding resource's `last_modified`
value for datastore-first resources. A scheduled job is used to
reduce duplicated metadata updates that would slow down these
operations.
