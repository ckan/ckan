import formencode.sqlschema

import ckan.models

class PackageSchema(formencode.sqlschema.SQLSchema):
    wrap = ckan.models.Package
    allow_extra_fields = True
    # setting filter_extra_fields seems to mean from_python no longer works
    # filter_extra_fields = True

