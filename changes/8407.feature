Faster dataset metadata updates by detecting changes and only updating resource
metadata when dataset fields defined by IDatasetForm.resource_validation_dependencies
have changed (default: none)

Now activities are created and metadata_modified updated only if there is a real change.

metadata_modified may now be set by sysadmins which is useful for harvesting or mirroring.

The allow_partial_update context parameter has been removed, now normal API
users may call package_update without passing resources. In this case the existing
resources will remain untouched instead of being deleted.

package_update and actions that call it now report whether there was a real change by
adding the package id to a new changed_entities context value or changed_entities
envelope value for API calls.
