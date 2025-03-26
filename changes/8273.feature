Faster package/group/organization extras using jsonb storage

PackageExtra and GroupExtra tables have been removed. Code that
accesses these models directly will need to be updated to use
the Package.extras and Group.extras dicts for updating
and JSON queries like
`query(Package, Package.extras['name'] == '"value"')`
