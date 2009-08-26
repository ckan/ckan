import re

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

class LicenseRenderer(formalchemy.fields.FieldRenderer):
    def render(self, options, **kwargs):
        selected = unicode(kwargs.get('selected', None) or self._value)
        options = [('', None)] + [(x, unicode(model.License.by_name(x).id)) for x in model.LicenseList.all_formatted]
        return h.select(self.name, h.options_for_select(options, selected=selected), **kwargs)


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
        tags = self.field.parent.tags.value or self.field.parent.model.tags or []
        tags_as_string = self._convert_tags(tags)
        return self.tag_field_template % (h.text_field(self.name, value=tags_as_string, size=60, **kwargs), self.field.parent.model.id or '')

    def _convert_tags(self, tags_dict):
        if tags_dict:
            tagnames = [ tag.name for tag in tags_dict ]
        else:
            tagnames = []
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

class PackageFieldSet(formalchemy.FieldSet):
    def __init__(self):
        formalchemy.FieldSet.__init__(self, model.Package)

    def validate_on_edit(self, orig_pkg_name, record_id):
        # If not changing name, don't validate this field (it will think it
        # is not unique because name already exists in db). So change it
        # temporarily to something that will always validate ok.
        temp_name = None
        if self.name.value == orig_pkg_name:
            temp_name = orig_pkg_name
            self.data['Package-%s-name' % record_id] = 'something_unique'
        validation = self.validate()
        if temp_name:
            # restore it
            self.data['Package-%s-name' % record_id] = temp_name
        return validation


package_fs = PackageFieldSet()
package_fs.add(TagField('tags').with_renderer(TagEditRenderer).validate(tag_name_validator))
package_fs.configure(options=[package_fs.name.label('Name (required)').validate(package_name_validator),
                              package_fs.license.with_renderer(LicenseRenderer),
                              ],
                     exclude=[package_fs.package_tags,
                              package_fs.all_revisions,
                              package_fs.revision,
                              package_fs.state,
                              package_fs._extras,])


def get_package_dict(pkg=None):
    indict = {}
    if pkg:
        fs = package_fs.bind(pkg)
    else:
        fs = package_fs

    exclude = ('-id', '-package_tags', '-all_revisions')

    for field in fs._fields.values():
        if not filter(lambda x: field.renderer.name.endswith(x), exclude):
             if field.renderer._value:
                 indict[field.renderer.name] = field.renderer._value
             else:
                 indict[field.renderer.name] = u''
    return indict

def edit_package_dict(_dict, changed_items, id=''):
    prefix = 'Package-%s-' % id
    for key, value in changed_items.items():
        key = prefix + key
        assert _dict.has_key(key), _dict
        _dict[key] = value
    return _dict

def validate_package_on_edit(fs, id):
    # If not changing name, don't validate this field (it will think it
    # is not unique because name already exists in db). So change it
    # temporarily to something that will always validate ok.
    temp_name = None
    if fs.name.value == id:
        temp_name = id
        fs.data['Package-%s-name' % record_id] = 'something_unique'
    validation = fs.validate()
    if temp_name:
        # restore it
        fs.data['Package-%s-name' % record_id] = temp_name
