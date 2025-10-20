advanced datastore filters + fast datastore_search pagination
- `datastore_search` and `datastore_delete` `filters` now accept
  range values and nested AND and OR operations
- `datastore_search` now returns a `next_page` value with
  filters that can be used for fast pagination when records
  are returned sorted by their `_id` field
- datastore dump endpoint now uses fast pagination to more
  quickly stream large datasets as CSV, JSON, etc.
