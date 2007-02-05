import formencode.sqlschema

import ckan.models

class PackageSchema(formencode.sqlschema.SQLSchema):
    wrap = ckan.models.Package

class PackageRevisionSchema(formencode.sqlschema.SQLSchema):
    wrap = ckan.models.PackageRevision

