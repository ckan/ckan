IDataDictionaryForm for extending and validating new keys in the `fields`
dicts. Unlike the `info` free-form dict these new keys are possible to
tightly control with a schema. The schema is built by combining schemas
from from all plugins implementing this interface so plugins implementing
different features may all contribute to the same schema.

The underlying storage for data dictionary fields has changed. Use:
`ckan datastore upgrade` after upgrading to this release.
