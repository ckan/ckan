import re

import formencode
import formalchemy
from formalchemy import helpers as h
import ckan.model as model

package_match = re.compile('[a-z0-9_\-]*$')
package_name_err = 'Package must be unique at least %s lowercase alphanumeric (ascii) characters and these symbols: -_'
def package_name_validator(val):
    min_length = 2
    if len(val) < min_length:
        raise formalchemy.ValidationError('Package name must be at least %s characters long' % min_length)
    if not package_match.match(val):
        raise formalchemy.ValidationError('Package must be purely lowercase alphanumeric (ascii) characters and these symbols: -_')
    if model.Package.by_name(val):
        raise formalchemy.ValidationError('Package name already exists in database')
        

tagname_match = re.compile('[\w\-_.]*$', re.UNICODE)
tagname_uppercase = re.compile('[A-Z]')
def tag_name_validator(val):
    for tag in val:
        min_length = 2
        if len(tag.name) < min_length:
            raise formalchemy.ValidationError('Tag "%s" length is less than minimum %s' % (tag, min_length))
        if not tagname_match.match(tag.name):
            raise formalchemy.ValidationError('Tag "%s" must be alphanumeric characters or symbols: -_.' % (tag))
        if tagname_uppercase.search(tag.name):
            raise formalchemy.ValidationError('Tag "%s" must not be uppercase' % (tag))

            
        
# This renderer is used for problematic hidden fields to prevent
# sync problems.
class BlankRenderer(formalchemy.fields.FieldRenderer):
    def render(self, **kwargs):
        return ''

    def deserialize(self):
        return []
    

class TagField(formalchemy.Field):
    def sync(self):
        if not self.is_readonly():
            # NOTE this should work - not sure why not
#            setattr(self.model, self.name, self._deserialize())
            self._update_tags()

    def _update_tags(self):
        pkg = self.model
        tags = self._deserialize()
        taglist = [tag.name for tag in tags]
        current_tags = [ tag.name for tag in pkg.tags ]
        for name in taglist:
            if name not in current_tags:
                pkg.add_tag_by_name(name)
        for pkgtag in pkg.package_tags:
            if pkgtag.tag.name not in taglist:
                pkgtag.delete()

class TagEditRenderer(formalchemy.fields.FieldRenderer):
    tag_field_template = '''
    <div id="tagsAutocomp">
        %s <br />
        <div id="tagsAutocompContainer"></div>
      </div>
      <script type="text/javascript">
        var tagsSchema = ["ResultSet.Result", "Name"];
        var tagsDataSource = new YAHOO.widget.DS_XHR(
          "../../tag/autocomplete", tagsSchema
        );
        tagsDataSource.scriptQueryParam = "incomplete";
        var tagsAutocomp = new YAHOO.widget.AutoComplete(
          "Package-%s-tags","tagsAutocompContainer", tagsDataSource
        );
        tagsAutocomp.delimChar = " ";
        tagsAutocomp.maxResultsDisplayed = 10;
      </script>
      <br/>
      '''
    def render(self, **kwargs):
        tags = self.field.parent.model.tags
        tags_as_string = self._convert_tags(tags)
        return self.tag_field_template % (h.text_field(self.name, content=tags_as_string, size=60, **kwargs), self.field.parent.model.id or '')
    # TODO test by eye

    def _convert_tags(self, tags_dict):
        tagnames = [ tag.name for tag in tags_dict ]
        return ' '.join(tagnames)

    def deserialize(self):
        tags_as_string = self._serialized_value()
        package = self.field.parent.model
        #self._update_tags(package, tags_as_string)

        tags_as_string = tags_as_string.replace(',', ' ')
        taglist = tags_as_string.split()
        def find_or_create_tag(name):
            tag = model.Tag.by_name(name)
            if not tag:
                tag = model.Tag(name=name)
            return tag
        tags = [find_or_create_tag(x) for x in taglist]
        return tags        


license_options = [('', None)] + [(x, model.License.by_name(x).id) for x in model.LicenseList.all_formatted]

package_fs = formalchemy.FieldSet(model.Package)
package_fs.add(TagField('tags').with_renderer(TagEditRenderer).validate(tag_name_validator))
#package_fs.add(formalchemy.Field('log_message').textarea())
package_fs.configure(options=[package_fs.name.label('Name (required)').validate(package_name_validator),
#                              package_fs.revision.with_renderer(BlankRenderer),
#                              package_fs.revision.hidden(),
#                              package_fs.package_tags.with_renderer(BlankRenderer).hidden(),
#                              package_fs.all_revisions.with_renderer(BlankRenderer).hidden(),
#                              package_fs.state.hidden(),
                              package_fs.license.dropdown(options = license_options),
                              ],
                     exclude=[package_fs.package_tags,
                              package_fs.all_revisions,
                              package_fs.revision,
                              package_fs.state])
del package_fs._fields['all_revisions']
#                              package_fs.name.validate(MaxLength(20).to_python),



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

##std_object_name = formencode.All(
##        formencode.validators.MinLength(2, strip=True, not_empty=True),
##        formencode.validators.PlainText(strip=True),
##        LowerCase(strip=True),
##        )

##package_name_validator = formencode.All(
##        formencode.validators.MinLength(2, not_empty=True),
##        formencode.validators.PlainText(),
##        LowerCase(),
##        UniquePackageName(),
##        )

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

