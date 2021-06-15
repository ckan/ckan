``datastore_info`` now returns more detailed info. It returns database-level metadata in addition
to rowcount (aliases, id, size, index_size, db_size and table_type), and the data dictionary with
database-level schemata (native_type, index_name, is_index, notnull & uniquekey).
See the documentation at :py:func:`~ckanext.datastore.logic.action.datastore_info`
