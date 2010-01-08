import re

from pylons import config
import formalchemy
from formalchemy import helpers as h

import common
import ckan.model as model
import ckan.lib.helpers

__all__ = ['package_fs', 'package_fs_admin', 'get_package_dict', 'edit_package_dict', 'add_to_package_dict', 'get_additional_package_fields', 'get_package_fs_options', 'PackageFieldSet', 'StateRenderer', 'TagEditRenderer', 'get_fieldset']

PACKAGE_FORM_KEY = 'package_form_schema'

def package_name_validator(val, field):
    common.name_validator(val, field)
    if model.Package.by_name(val):
        raise formalchemy.ValidationError('Package name already exists in database')
        

tagname_match = re.compile('[\w\-_.]*$', re.UNICODE)
tagname_uppercase = re.compile('[A-Z]')
def tag_name_validator(val, field):
    for tag in val:
        min_length = 2
        if len(tag.name) < min_length:
            raise formalchemy.ValidationError('Tag "%s" length is less than minimum %s' % (tag.name, min_length))
        if not tagname_match.match(tag.name):
            raise formalchemy.ValidationError('Tag "%s" must be alphanumeric characters or symbols: -_.' % (tag.name))
        if tagname_uppercase.search(tag.name):
            raise formalchemy.ValidationError('Tag "%s" must not be uppercase' % (tag.name))            
        
tagname_match = re.compile('[\w\-_.]*$', re.UNICODE)
tagname_uppercase = re.compile('[A-Z]')
def extras_validator(val, field):
    val_dict = dict(val)
    for key, value in val:
        if value != val_dict[key]:
            raise formalchemy.ValidationError('Duplicate key "%s"' % key)
        if value and not key:
            # Note value is allowed to by None - REST way of deleting fields.
            raise formalchemy.ValidationError('Extra key-value pair: key is not set.')

class ResourcesField(formalchemy.Field):
    def sync(self):
        if not self.is_readonly():
            pkg = self.model
            resources = self._deserialize() or []
            pkg.resources = []
            for url, format, description, hash_ in resources:
                pkg.add_resource(url=url,
                                 format=format,
                                 description=description,
                                 hash=hash_)

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

class ExtrasField(formalchemy.Field):
    def sync(self):
        if not self.is_readonly():
            self._update_extras()

    def _update_extras(self):
        pkg = self.model
        extra_list = self._deserialize()
        current_extra_keys = pkg.extras.keys()
        extra_keys = []
        for key, value in extra_list:
            extra_keys.append(key)
            if key in current_extra_keys:
                if pkg.extras[key] != value:
                    # edit existing extra
                    pkg.extras[key] = value
            else:
                # new extra
                pkg.extras[key] = value
        for key in current_extra_keys:
            if key not in extra_keys:
                del pkg.extras[key]
                
class ExtrasRenderer(formalchemy.fields.FieldRenderer):
    extra_field_template = '''
    <div>
      <label class="field_opt" for="%(name)s">%(key)s</label>
      <input id="%(name)s" name="%(name)s" size="20" type="text" value="%(value)s">
      <input type=checkbox name="%(name)s-checkbox">Delete</input>
    </div>
    '''
    blank_extra_field_template = '''
    <div class="extras-new-field">
      <label class="field_opt">New key</label>
      <input id="%(name)s-key" name="%(name)s-key" size="20" type="text">
      <label class="field_opt">Value</label>
      <input id="%(name)s-value" name="%(name)s-value" size="20" type="text">
    </div>
    '''

    def _get_value(self):
        extras = self.field.parent.extras.value
        if extras is None:
            extras = self.field.parent.model.extras.items() or []
        return extras

    def render(self, **kwargs):
        extras = self._get_value()
        html = ''
        for key, value in extras:
            html += self.extra_field_template % {
                'name':self.name + '-%s' % key,
                'key':key.capitalize(),
                'value':value,}
        for i in range(3):
            html += self.blank_extra_field_template % {
                'name':'%s-newfield%s' % (self.name, i)}
                                                   
        return html

    def render_readonly(self, **kwargs):
        html_items = []
        extras = self._get_value()
        for key, value in extras:
            html_items.append(common.field_readonly_renderer(key, value))
        return html_items

    def deserialize(self):
        # Example params:
        # ('Package-1-extras-genre', u'romantic novel'), (Package-1-extras-1-checkbox', 'on')
        # ('Package-1-extras-newfield0-key', u'aaa'), ('Package-1-extras-newfield0-value', u'bbb'), 
        extra_fields = []
        for key, value in self._params.items():
            key_parts = key.split('-')
            if len(key_parts) < 3 or key_parts[0] != 'Package' or key_parts[2] != 'extras':
                continue
            package_id = key_parts[1]
            if len(key_parts) == 3 and isinstance(value, dict):
                # simple dict passed into 'Package-1-extras' e.g. via REST i/f
                extra_fields.extend(value.items())
            elif len(key_parts) == 4:
                # existing field
                key = key_parts[3]
                checkbox_key = 'Package-%s-extras-%s-checkbox' % (package_id, key)
                delete = self._params.get(checkbox_key, '') == 'on'
                if not delete:
                    extra_fields.append((key, value))
            elif len(key_parts) == 5 and key_parts[3].startswith('newfield'):
                new_field_index = key_parts[3][len('newfield'):]
                if key_parts[4] == u'key':
                    new_key = value
                    value_key = 'Package-%s-extras-newfield%s-value' % (package_id, new_field_index)
                    new_value = self._params.get(value_key, '')
                    if new_key or new_value:
                        extra_fields.append((new_key, new_value))
                elif key_parts[4] == u'value':
                    # if it doesn't have a matching key, add it to extra_fields anyway for
                    # validation to fail
                    key_key = 'Package-%s-extras-newfield%s-key' % (package_id, new_field_index)
                    if not self._params.has_key(key_key):
                        extra_fields.append(('', value))                

        return extra_fields
    
class LicenseRenderer(formalchemy.fields.FieldRenderer):
    def render(self, options, **kwargs):
        selected = unicode(kwargs.get('selected', None) or self._value)
        options = [('', None)] + [(x, unicode(model.License.by_name(x).id)) for x in model.LicenseList.all_formatted]
        return h.select(self.name, h.options_for_select(options, selected=selected), **kwargs)

    def render_readonly(self, **kwargs):
        if self._value:
            license_name = model.License.query.get(int(self._value)).name
        else:
            license_name = ''
        return common.field_readonly_renderer(self.field.key, license_name)


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
        tags_as_string = self._tags_string()
        return self.tag_field_template % (h.text_field(self.name, value=tags_as_string, size=60, **kwargs), self.field.parent.model.id or '')

    def _tags_string(self):
        tags = self.field.parent.tags.value or self.field.parent.model.tags or []
        if tags:
            tagnames = [ tag.name for tag in tags ]
        else:
            tagnames = []
        return ' '.join(tagnames)

    def _tag_links(self):
        tags = self.field.parent.tags.value or self.field.parent.model.tags or []
        if tags:
            tagnames = [ tag.name for tag in tags ]
        else:
            tagnames = []
        return ' '.join(['<a href="/tag/read/%s">%s</a>' % (str(tag), str(tag)) for tag in tagnames])

    def render_readonly(self, **kwargs):
        tags_as_string = self._tag_links()
        return common.field_readonly_renderer(self.field.key, tags_as_string)

    def deserialize(self):
        tags_as_string = self._serialized_value() # space separated string
        package = self.field.parent.model
        #self._update_tags(package, tags_as_string)

        tags_as_string = tags_as_string.replace(',', ' ').lower()
        taglist = tags_as_string.split()
        def find_or_create_tag(name):
            tag = model.Tag.by_name(name)
            if not tag:
                tag = model.Tag(name=name)
            return tag
        tags = [find_or_create_tag(x) for x in taglist]
        return tags        

class StateRenderer(formalchemy.fields.FieldRenderer):
    def render(self, options, **kwargs):
        selected = int(kwargs.get('selected', None) or self._value)
        options = [(s.name, s.id) for s in model.State.query.all()]
        return h.select(self.name, h.options_for_select(options, selected=selected), **kwargs)

    def render_readonly(self, **kwargs):
        value_str = model.State.query.get(int(self._value)).name
        return common.field_readonly_renderer(self.field.key, value_str)

class ResourcesRenderer(formalchemy.fields.FieldRenderer):
    table_template = '''
      <table id="flexitable" prefix="%(id)s" class="no-margin">
        <tr> <th>URL</th><th>Format</th><th>Description</th><th>Hash</th> </tr>
%(rows)s
      </table>
      <a href="javascript:addRowToTable()" id="add_resource"><img src="/images/icons/add.png"></a>
      '''
    table_template_readonly = '''
      <table id="flexitable" prefix="%(id)s">
        <tr> <th>URL</th><th>Format</th><th>Description</th><th>Hash</th> </tr>
%(rows)s
      </table>
      '''
    # NB row_template needs to be kept in-step with flexitable's row creation.
    row_template = '''
        <tr>
          <td><input name="%(id)s-%(res_index)s-url" size="40" id="%(id)s-%(res_index)s-url" type="text" value="%(url)s" /></td>
          <td><input name="%(id)s-%(res_index)s-format" size="5" id="%(id)s-%(res_index)s-format" type="text" value="%(format)s" /></td>
          <td><input name="%(id)s-%(res_index)s-description" size="25" id="%(id)s-%(res_index)s-description" type="text" value="%(description)s" /></td>
          <td><input name="%(id)s-%(res_index)s-hash" size="10" id="%(id)s-%(res_index)s-hash" type="text" value="%(hash)s" /></td>
          <td>
            <a href="javascript:moveRowUp(%(res_index)s)"><img src="/images/icons/arrow_up.png"></a>
            <a href="javascript:moveRowDown(%(res_index)s)"><img src="/images/icons/arrow_down.png"></a>
            <a href="javascript:removeRowFromTable(%(res_index)s);"><img src="http://m.okfn.org/kforge/images/icon-delete.png" class="icon"></a>
          </td>
        </tr>
    '''
    row_template_readonly = '''
        <tr> <td><a href="%(url)s">%(url)s</a></td><td>%(format)s</td><td>%(description)s</td><td>%(description)s</td><td>%(hash)s</td> </tr>
    '''

    def render(self, **kwargs):
        return self._render(readonly=False)

    def render_readonly(self, **kwargs):
        value_str = self._render(readonly=True)
        return common.field_readonly_renderer(self.field.key, value_str, newline_reqd=False)
#        return self._render(readonly=True)

    def _render(self, readonly=False):
        row_template = self.row_template_readonly if readonly else self.row_template
        table_template = self.table_template_readonly if readonly else self.table_template
        resources = self.field.parent.resources.value or \
                    self.field.parent.model.resources or []
        # Start an edit with empty resources
        if not readonly:
            # copy so we don't change original
            resources = resources[:]
            resources.extend([None, None, None])
        rows = []
        for index, res in enumerate(resources):
            if isinstance(res, model.PackageResource):
                url = res.url
                format = res.format
                description = res.description
                hash_ = res.hash
            elif isinstance(res, tuple):
                url, format, description, hash_ = res
            elif res == None:
                url = format = description = hash_ = u''
            rows.append(row_template % {'url':url,
                                        'format':format,
                                        'description':description,
                                        'hash':hash_ or u'',
                                        'id':self.name,
                                        'res_index':index,
                                        })
        if rows:
            html = table_template % {'id':self.name,
                                     'rows':''.join(rows)}
        else:
            html = ''
        return html

    def _serialized_value(self):
        package = self.field.parent.model
        params = dict(self._params)
        new_resources = []
        rest_key = self.name

        # REST param format
        # e.g. 'Package-1-resources': [{u'url':u'http://ww...
        if params.has_key(rest_key) and isinstance(params[rest_key], (list, tuple)):
            new_resources = params[rest_key]

        # formalchemy form param format
        # e.g. 'Package-1-resources-0-url': u'http://ww...'
        row = 0
        while True:
            if not params.has_key('%s-%i-url' % (self.name, row)):
                break
            url = params.get('%s-%i-url' % (self.name, row), u'')
            format = params.get('%s-%i-format' % (self.name, row), u'')
            description = params.get('%s-%i-description' % (self.name, row), u'')
            hash_ = params.get('%s-%i-hash' % (self.name, row), u'')
            if url or format or description or hash_:
                resource = (url, format, description, hash_)
                new_resources.append(resource)
            row += 1
        return new_resources

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
            self.data['Package-%s-name' % record_id] = u'something_unique'
        validation = self.validate()
        if temp_name:
            # restore it
            self.data['Package-%s-name' % record_id] = temp_name
        return validation


package_fs = PackageFieldSet()
package_fs_admin = PackageFieldSet()
def get_package_fs_options(fs):
    return [
        fs.name.label('Short Unique Name (required)'
            ).with_renderer(common.CustomTextFieldRenderer
                ).validate(package_name_validator),
        fs.license.with_renderer(LicenseRenderer),
        fs.title.with_renderer(common.CustomTextFieldRenderer),
        fs.version.with_renderer(common.CustomTextFieldRenderer),
        fs.url.with_renderer(common.CustomTextFieldRenderer),
        fs.author.with_renderer(common.CustomTextFieldRenderer),
        fs.author_email.with_renderer(common.CustomTextFieldRenderer),
        fs.maintainer.with_renderer(common.CustomTextFieldRenderer),
        fs.maintainer_email.with_renderer(common.CustomTextFieldRenderer),
        fs.notes.with_renderer(common.TextAreaRenderer),
        ]
def get_package_fs_include(fs, extras=True, is_admin=False):
    pkgs = [fs.name, fs.title, fs.version, fs.url, fs.resources,
            fs.author, fs.author_email, fs.maintainer, fs.maintainer_email,
            fs.license, fs.tags, fs.notes, ]
    if is_admin:
        pkgs.append(fs.state)
    if extras:
        pkgs.append(fs.extras)
    return pkgs

def get_additional_package_fields():
    return [ResourcesField('resources').with_renderer(ResourcesRenderer),
            TagField('tags').with_renderer(TagEditRenderer).validate(tag_name_validator).label('Tags (space separated list)'),
            ExtrasField('extras').with_renderer(ExtrasRenderer).validate(extras_validator),
            ]

for fs in (package_fs, package_fs_admin):
    for field in get_additional_package_fields():
        fs.append(field)

package_fs.configure(options=get_package_fs_options(package_fs),
                     include=get_package_fs_include(package_fs))
package_fs_admin.configure(options=get_package_fs_options(package_fs_admin) + \
                           [package_fs_admin.state.with_renderer(StateRenderer)],
                           include=get_package_fs_include(package_fs_admin, is_admin=True))

def get_package_dict(pkg=None, blank=False, fs=None):
    '''
    Creates a package dictionary suitable for use with edit_package_dict and
    deserialization.
    @param pkg  Package this dict relates to. id is extracted to go into the
                key prefixes and the package data is used. If None, the dict
                is for a new package.
    @param blank  Whether or not you supply a package, this ensures that the
                  values of the resulting dict are blank.
    @param fs  Fieldset to use - sets the fields.
    Resulting dict has keys with a formalchemy prefix, and it should work
    binding it to a fs and syncing. But whereas formalchemy forms produce a
    param dicts with "package--extras-0-key":extra-key etc, this method creates
    a param dict with iterators in thIn contrast toe values, so you get something like:
    "package--extras":{extra-key:extra-value} instead.
    '''
    indict = {}
    if fs is None:
        fs = get_fieldset(is_admin=False, basic=False)

    if pkg:
        fs = fs.bind(pkg)

    exclude = ('-id', '-package_tags', '-all_revisions', '-_extras', '-roles', '-ratings')

    for field in fs._fields.values():
        if not filter(lambda x: field.renderer.name.endswith(x), exclude):
            if blank:
                indict[field.renderer.name] = u''
            else:
                if field.renderer._value:
                    indict[field.renderer.name] = field.renderer._value
                else:
                    indict[field.renderer.name] = u''

                # some fields don't bind in this way, so do it manually
                if field.renderer.name.endswith('-extras'):
                    indict[field.renderer.name] = dict(pkg.extras) if pkg else {}
                if field.renderer.name.endswith('-tags'):
                    indict[field.renderer.name] = ' '.join([tag.name for tag in pkg.tags]) if pkg else ''
                if field.renderer.name.endswith('-resources'):
                    indict[field.renderer.name] = [{'url':res.url, 'format':res.format, 'description':res.description, 'hash':res.hash} for res in pkg.resources] if pkg else []
        
    return indict

def edit_package_dict(dict_, changed_items, id=''):
    '''
    Edits package dictionary obtained by "get_package_dict" ready for
    deserializing.
    
    @param dict_ Package dict to be edited
    @param changed_items Package dict with the changes to be made
           (keys do not need the "Package-<id>-" prefix)
    @return Edited dict
    '''
    prefix = 'Package-%s-' % id
    extras_key = prefix + 'extras'
    tags_key = prefix + 'tags'
    resources_key = prefix + 'resources'
    download_url_key = prefix + 'download_url'
    for key, value in changed_items.items():
        if key:
            if not key.startswith(prefix):
                key = prefix + key
            if dict_.has_key(key):
                if key == extras_key and isinstance(value, dict):
                    extras = dict_[extras_key]
                    for e_key, e_value in value.items():
                        if e_value == None:
                            if extras.has_key(e_key):
                                del extras[e_key]
                            #else:
                            #    print 'Ignoring deletion - incorrect key'
                        else:
                            extras[e_key] = e_value
                elif key == resources_key and isinstance(value, list):
                    # REST edit
                    resources = []
                    for res in value:
                        resources.append((res['url'], res['format'], res['description'], res['hash']))
                    dict_[resources_key] = resources
                elif key == tags_key and isinstance(value, list):
                    dict_[key] = ' '.join(value)
                else:
                    dict_[key] = value
            elif key == download_url_key:
                dict_[resources_key].insert(0, (value, '', '', ''))
                # blank format, description and hash
    return dict_

def add_to_package_dict(dict_, changed_items, id=''):
    '''
    Takes a package dictionary (usually with all fields, but blank content)
    and adds the changed_items dictionary.
    '''
    prefix = 'Package-%s-' % id
    for key, value in changed_items.items():
        if key:
            if not key.startswith(prefix):
                key = prefix + key
            dict_[key] = value
    return dict_

def validate_package_on_edit(fs, id):
    # If not changing name, don't validate this field (it will think it
    # is not unique because name already exists in db). So change it
    # temporarily to something that will always validate ok.
    temp_name = None
    if fs.name.value == id:
        temp_name = id
        fs.data['Package-%s-name' % record_id] = u'something_unique'
    validation = fs.validate()
    if temp_name:
        # restore it
        fs.data['Package-%s-name' % record_id] = temp_name

def get_fieldset(is_admin=False, basic=False, package_form=None):
    ''' Returns the appropriate fieldset (maybe depending on permissions for
    the package supplied).
    @param basic: demand the "basic" fieldset, ignoring config specifying
                  a particular package_form.
    @param package_form: specify a particular package_form. Otherwise it
                  is taken from the config file.
    '''
    fs = None
    if not basic:
        if package_form is None:
            package_form = config.get(PACKAGE_FORM_KEY)
        if package_form == 'gov':
            if is_admin:
                fs = ckan.forms.package_gov_fs_admin
            else:
                fs = ckan.forms.package_gov_fs
    if not fs:
        if is_admin:
            fs = ckan.forms.package_fs_admin
        else:
            fs = ckan.forms.package_fs
#    print "FS admin=%s package_form=%s basic=%s" % (is_admin, package_form, basic)
    return fs
