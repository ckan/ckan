Allow configuring datastore full text field indexes with new
ckan.datastore.default_fts_index_field_types config option.

The default is an empty list, avoiding automatically creating
separate full text indexes for any individual columns. The
whole-row full text index still exists for all tables.
