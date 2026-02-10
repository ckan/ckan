The calculate_record_count parameter to datastore_create, datastore_upsert
and datastore_delete now default to the new option "background". This option
schedules a cancelable background job to update the stored count of rows.

The datastore_search total_estimation_threshold parameter now defaults to
20000. This means that for any table with more than 20k rows the stored
count of rows will be returned when possible instead of calculating the
exact value. 20k was chosen because exact values for tables this size can
be calculated in about 20ms. This value can be overridden by setting the new
ckan.datastore.default_total_estimation_threshold configuration option.

Calculating the exact number of rows for large tables dominates the time
required to return results from package_search. These changes ensure that
the stored counts of rows is updated after every modification so that it
can be relied on for datastore_search results, without slowing down
datastore_create, datastore_upsert and datastore_delete calls.

When upgrading the `ckan datastore set-permissions` sql must be run
against an existing datastore database to define the new
`fast_table_row_count` function.
