from ckan.lib.base import *
import ckan.forms
import ckan.controllers.package

class FormsapiController(BaseController):

    def _assert_is_found(self, entity):
        if entity is None:
            abort(404, '404 Not Found')

    def _assert_is_authorized(self, entity):
        pass

    def package_edit(self, id):
        # Find the entity.
        pkg = self._get_pkg(id)
        self._assert_is_found(pkg)
        # Check user authorization.
        self._assert_is_authorized(pkg)
        # Get the fieldset.
        fieldset = ckan.forms.registry.get_fieldset()
        # Bind the entity to the fieldset.
        bound_fieldset = fieldset.bind(pkg)
        # Render the fields.
        form = bound_fieldset.render()
        # Return the form.
        return h.literal(form)

