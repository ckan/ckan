from ckan import logic
import ckan.logic.auth.update as _update

package_patch = _update.package_update

resource_patch = _update.resource_update

group_patch = _update.group_update

organization_patch = _update.organization_update
