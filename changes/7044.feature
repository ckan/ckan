Added `list-orphans` and `clear-orphans` sub-commands to the `search-index` command.

`list-orphans` will list all public package IDs which exist in the solr index, but do not exist in the database.

`clear-orphans` will clear the search index for all the public orphaned packages.
