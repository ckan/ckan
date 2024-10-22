Update resources faster by selectively skipping resource validation and
database updating for unchanged resources.

This change will affect custom validation rules that access resource metadata
from dataset or other resource validators:

- now only the changed resources are passed to validation
- flattened data the validators receive won't include skipped resources

This change does not affect validation of resource fields that depend on
package fields because the package fields are always available in flattened
data.
