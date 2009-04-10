import formencode

import ckan.model as model

class UniquePackageName(formencode.FancyValidator):
    def _to_python(self, value, state):
        exists = model.Package.query.filter_by(name=value).count() > 0
        if exists:
            raise formencode.Invalid(
                'That package name already exists',
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
        formencode.validators.MinLength(2, strip=True, not_empty=True),
        formencode.validators.PlainText(strip=True),
        LowerCase(strip=True),
        )

package_name_validator = formencode.All(
        formencode.validators.MinLength(2, not_empty=True),
        formencode.validators.PlainText(),
        LowerCase(),
        UniquePackageName(),
        )

class PackageNameSchema(formencode.Schema):

    name = package_name_validator
    allow_extra_fields = True


from sqlalchemy.orm import class_mapper
class PackageSchema(object):
    allow_extra_fields = True
    # setting filter_extra_fields seems to mean from_python no longer works
    # filter_extra_fields = True

    def from_python(self, pkg):
        table = class_mapper(model.Package).mapped_table
        value = {}
        for col in table.c:
            value[col.name] = getattr(pkg, col.name, None)
        tags_as_string = self._convert_tags(pkg)
        value['tags'] = tags_as_string
        if pkg.license:
            value['licenses'] = [pkg.license.name]
        else:
            value['licenses'] = []
        return value

    def _convert_tags(self, obj):
        tagnames = [ tag.name for tag in obj.tags ]
        return ' '.join(tagnames)
    
    def to_python(self, indict):
        id = indict.get('id', '')
        name = indict.get('name', '')
        if not id: # new item
            if 'id' in indict:
                del indict['id'] # remove so not set in attributes below
            PackageNameSchema.to_python(indict)
            outobj = model.Package()
        else:
            # TODO: validate name
            # name could have changed ...
            # std_object_name.validate(name)
            outobj = model.Package.query.get(int(id))
        if outobj is None:
            msg = 'Something very wrong: cannot find object to update'
            raise Exception(msg)

        table = class_mapper(model.Package).mapped_table
        for attrname in table.c.keys():
            if attrname in indict:
                setattr(outobj, attrname, indict[attrname])

        # Must do tags/licenses after basic attributes as may result in flush
        # (and flush requires name to be set)
        tags = indict.get('tags', '')
        licenses = indict.get('licenses', [])
        if len(licenses) > 0:
            licenseobj = model.License.query.filter_by(name=licenses[0]).first()
            outobj.license = licenseobj

        outobj = self._update_tags(outobj, tags)
        return outobj

    def _update_tags(self, pkg, tags_as_string):
        # replace all commas with spaces
        if type(tags_as_string) == list:
            taglist = tags_as_string
        else:
            tags_as_string = tags_as_string.replace(',', ' ')
            taglist = tags_as_string.split()
        # validate and normalize
        taglist = [ std_object_name.to_python(name) for name in taglist ]
        current_tags = [ tag.name for tag in pkg.tags ]
        for name in taglist:
            if name not in current_tags:
                try:
                    pkg.add_tag_by_name(name)
                except:
                    pass  # Not good. --jb
        for pkgtag in pkg.package_tags:
            if pkgtag.tag.name not in taglist:
                pkgtag.delete()
        return pkg

