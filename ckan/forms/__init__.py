import formencode
import formencode.sqlschema

import ckan.models

class UniquePackageName(formencode.FancyValidator):
    def _to_python(self, value, state):
        exists = False
        rev = ckan.models.repo.youngest_revision()
        try:
            rev.model.packages.get(value)
            exists = True
        except:
            pass
        if exists:
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

std_object_name = formencode.All(
        formencode.validators.MinLength(2, strip=True),
        formencode.validators.PlainText(strip=True),
        LowerCase(strip=True),
        )

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
        tagnames = [ pkg2tag.tag.name for pkg2tag in obj.tags ]
        return ' '.join(tagnames)

    def get_current(self, obj, state):
        # single super is a mess, see:
        # http://groups.google.co.uk/group/comp.lang.python/browse_thread/thread/6d94ebc1016b7ddb/34684c138cf9f3%2334684c138cf9f3 
        # not sure why it is in the example code ...
        # value = super(PackageSchema).get_current(obj, state)
        value = formencode.sqlschema.SQLSchema.get_current(self, obj, state)
        for name in obj.versioned_attributes:
            value[name] = getattr(obj, name)
        tags_as_string = self._convert_tags(obj)
        value['tags'] = tags_as_string
        # convert licenses
        del value['license']
        licenses = []
        if obj.license is not None:
            licenses.append(obj.license.name)
        value['licenses'] = licenses
        return value

    def _update_tags(self, pkg, tags_as_string):
        # replace all commas with spaces
        if type(tags_as_string) == list:
            taglist = tags_as_string
        else:
            tags_as_string = tags_as_string.replace(',', ' ')
            taglist = tags_as_string.split()
        # validate and normalize
        taglist = [ std_object_name.to_python(name) for name in taglist ]
        current_tags = [ pkg2tag.tag.name for pkg2tag in pkg.tags ]
        for name in taglist:
            if name not in current_tags:
                pkg.add_tag_by_name(name)
        for pkg2tag in pkg.tags:
            if pkg2tag.tag.name not in taglist:
                pkg2tag.delete()
        return pkg

    def update_object(self, columns, extra, state):
        txn = state
        tags = extra.pop('tags', '')
        licenses = extra.pop('licenses', [])
        # TODO: create the object if it does not already exist
        outobj = txn.model.packages.get(columns['name'])
        columns.pop('name')
        if len(licenses) > 0:
            licenseobj = ckan.models.License.byName(licenses[0])
            columns['license'] = licenseobj
        for key in columns:
            setattr(outobj, key, columns[key])
        for key in extra:
            setattr(outobj, key, extra[key])
        outobj = self._update_tags(outobj, tags)
        return outobj

