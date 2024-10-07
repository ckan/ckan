Update resources faster by selectively skipping resource validation and
database updating for unchanged resources. Now activities are created and
metadata_modified updated only if there is a real change. metadata_modified
may now be set by sysadmins (useful for harvesting or mirroring).

The allow_partial_update context parameter has been removed, now normal API
users may call package_update without passing resources.

This change will affect custom validation rules that access resource metadata
from dataset or other resource validators:

- now only the changed resources are passed to validation
- flattened data the validators receive won't include skipped resources

This change does not affect validation of resource fields that depend on
package fields because the package fields are always available in flattened
data.
