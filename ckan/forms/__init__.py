import formencode
import formencode.sqlschema

import ckan.models

class UniquePackageName(formencode.FancyValidator):
    def _to_python(self, value, state):
        error = False
        try:
            ckan.models.dm.packages.get(value)
            error = True
        except:
            pass
        if error:
            raise formencode.Invalid(
                'That username already exists',
                value, state)
        else:
            return value

class LowerCase(formencode.FancyValidator):

     def _to_python(self, value, state):
         lower = value.strip().lower()
         if value != lower:
             raise formencode.Invalid(
                 'Please use only lower case characters', value, state)
         return value

package_name_validator = formencode.All(
        formencode.validators.MinLength(2),
        formencode.validators.PlainText(),
        LowerCase(),
        UniquePackageName(),
        )

class PackageNameSchema(formencode.Schema):

    name = package_name_validator
    allow_extra_fields = True

class PackageSchema(formencode.sqlschema.SQLSchema):
    wrap = ckan.models.Package
    allow_extra_fields = True
    # setting filter_extra_fields seems to mean from_python no longer works
    # filter_extra_fields = True

    def _convert_tags(self, obj):
        tagnames = [ tag.name for tag in obj.tags ]
        return ' '.join(tagnames)

    def get_current(self, obj, state):
        # single super is a mess, see:
        # http://groups.google.co.uk/group/comp.lang.python/browse_thread/thread/6d94ebc1016b7ddb/34684c138cf9f3%2334684c138cf9f3 
        # not sure why it is in the example code ...
        # value = super(PackageSchema).get_current(obj, state)
        value = formencode.sqlschema.SQLSchema.get_current(self, obj, state)
        tags_as_string = self._convert_tags(obj)
        value['tags'] = tags_as_string
        licenses = [ license.name for license in obj.licenses ]
        value['licenses'] = licenses
        return value

    def _update_tags(self, pkg, tags_as_string):
        taglist = tags_as_string.split()
        for name in taglist:
            pkg.add_tag_by_name(name)
        for tag in pkg.tags:
            if tag.name not in taglist:
                pkg.removeTag(tag)
        return pkg

    def _update_licenses(self, pkg, licenses):
        # sort of lame but what would be more efficient ...
        for name in licenses:
            license = ckan.models.License.byName(name)
            if license not in pkg.licenses:
                pkg.addLicense(license)
        for license in pkg.licenses:
            if license.name not in licenses:
                pkg.removeLicense(license)
        return pkg

    def update_object(self, columns, extra, state):
        tags = extra.pop('tags', '')
        licenses = extra.pop('licenses', [])
        # update_object requires existence of id to do updates
        if 'id' not in columns:
            tmp = ckan.models.dm.packages.get(columns['name'])
            columns['id'] = tmp.id
        # discard rest of extra so as not to get errors
        extra = {}
        outobj = super(PackageSchema, self).update_object(
            columns, extra, state)
        outobj = self._update_tags(outobj, tags)
        outobj = self._update_licenses(outobj, licenses)
        return outobj

