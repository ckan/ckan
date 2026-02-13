Calculating the exact number of rows for large tables dominates the time
required to return results from package_search. These changes ensure that
the stored counts of rows is updated after every modification so that it
can be relied on for datastore_search results, without slowing down
datastore_create, datastore_upsert and datastore_delete calls.

When upgrading the `ckan datastore set-permissions` sql must be run
against an existing datastore database to define the new
`fast_table_row_count` function.
