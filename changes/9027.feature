Advanced datastore filters + fast datastore_search pagination
- `datastore_search` and `datastore_delete` `filters` now accept
  range values and nested AND and OR operations
- `datastore_search` now returns a `next_page` value with
  filters that can be used for fast pagination when records
  are returned sorted by their `_id` field
- datastore dump endpoint now uses fast pagination to more
  quickly stream large datasets as CSV, JSON, etc.

Backwards-incompatible changes:
- previously filters on array fields would use an equality check
  when a list of values was passed instead of an "IN", now
  equality checks for list or dictionary values must use
  `{"eq": ...}` regardless of the field type.
- field names starting with `$` must now be prefixed with one
  extra `$` when used in filters. This avoids conflicts with
  `$and`, `$or` and future custom top-level filters.
