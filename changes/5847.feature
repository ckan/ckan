Allow configuring datastore full text field indexes with new
ckan.datastore.default_fts_index_field_types config option.

The default is "text tsvector" but this can be changed to
"" to avoiding automatically creating separate full text indexes
for any individual columns. The whole-row full text index still
exists for all tables.

After upgrading to ckan 2.12 the default changes to "".

Use the `ckan datastore fts-index` command to remove existing
column indexes to reclaim database space.
