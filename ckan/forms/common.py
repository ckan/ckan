import re

from formalchemy import helpers as fa_h
import formalchemy
import genshi

from ckan.lib.helpers import literal
import ckan.model as model
import ckan.lib.helpers as h
import ckan.lib.field_types as field_types
import ckan.misc

name_match = re.compile('[a-z0-9_\-]*$')
def name_validator(val, field=None):
    # check basic textual rules
    min_length = 2
    if len(val) < min_length:
        raise formalchemy.ValidationError('Name must be at least %s characters long' % min_length)
    if not name_match.match(val):
        raise formalchemy.ValidationError('Name must be purely lowercase alphanumeric (ascii) characters and these symbols: -_')
        
def package_name_validator(val, field=None):
    name_validator(val, field)
    # we disable autoflush here since may get used in package preview
    pkgs = model.Session.query(model.Package).autoflush(False).filter_by(name=val)
    for pkg in pkgs:
        if pkg != field.parent.model:
            raise formalchemy.ValidationError('Package name already exists in database')

def group_name_validator(val, field=None):
    name_validator(val, field)
    # we disable autoflush here since may get used in package preview
    groups = model.Session.query(model.Group).autoflush(False).filter_by(name=val)
    for group in groups:
        if group != field.parent.model:
            raise formalchemy.ValidationError('Group name already exists in database')

def field_readonly_renderer(key, value, newline_reqd=True):
    if value is None:
        value = ''
    key = key.capitalize().replace('_', ' ').replace('-', ' ')
    if key in ('Url', 'Download url', 'Taxonomy url'):
        key = key.replace(u'Url', u'URL')
        key = key.replace(u'url', u'URL')
        value = literal('<a href="%s">%s</a>') % (value, value)
#        value = '<a href="%s">%s</a>' % (value, value)
    html = literal('<strong>%s:</strong> %s') % (key, value)
    if newline_reqd:
        html += literal('<br/>')
    return html


class TextExtraRenderer(formalchemy.fields.TextFieldRenderer):
    def _get_value(self):
        extras = self.field.parent.model.extras # db
        return self._value or extras.get(self.field.name, u'') or u''

    def render(self, **kwargs):
        value = self._get_value()
        kwargs['size'] = '40'
        return fa_h.text_field(self.name, value=value, maxlength=self.length, **kwargs)

    def render_readonly(self, **kwargs):
        return field_readonly_renderer(self.field.key, self._get_value())


# Common fields paired with their renderer and maybe validator


class ConfiguredField(object):
    '''A parent class for a form field and its configuration.
    Derive specific field classes which should contain:
    * a formalchemy Field class
    * a formalchemy Renderer class
    * possible a field validator method
    * a get_configured method which returns the Field configured to use
      the Renderer (and validator if it is used)
    '''
    def __init__(self, name):
        self.name = name

class DateExtraField(ConfiguredField):
    '''A form field for DateType data stored in an 'extra' field.'''
    def get_configured(self):
        return self.DateExtraFieldField(self.name).with_renderer(self.DateExtraRenderer).validate(field_types.DateType.form_validator)

    class DateExtraFieldField(formalchemy.Field):
        def sync(self):
            if not self.is_readonly():
                pkg = self.model
                form_date = self._deserialize()
                date_db = field_types.DateType.form_to_db(form_date)
                pkg.extras[self.name] = date_db

    class DateExtraRenderer(TextExtraRenderer):
        def __init__(self, field):
            TextExtraRenderer.__init__(self, field)

        def _get_value(self):
            form_date = TextExtraRenderer._get_value(self)
            return field_types.DateType.db_to_form(form_date)

        def render_readonly(self, **kwargs):
            return field_readonly_renderer(self.field.key, self._get_value())

class DateRangeExtraField(ConfiguredField):
    '''A form field for two DateType fields, representing a date range,
    stored in 'extra' fields.'''
    def get_configured(self):
        return self.DateRangeField(self.name).with_renderer(self.DateRangeRenderer).validate(field_types.DateType.form_validator)

    class DateRangeField(formalchemy.Field):
        def sync(self):
            if not self.is_readonly():
                pkg = self.model
                vals = self._deserialize() or u''
                pkg.extras[self.name + '-from'] = field_types.DateType.form_to_db(vals[0])
                pkg.extras[self.name + '-to'] = field_types.DateType.form_to_db(vals[1])

    class DateRangeRenderer(formalchemy.fields.FieldRenderer):
        def _get_value(self):
            extras = self.field.parent.model.extras
            if self._value:
                from_form, to_form = self._value
            else:
                from_ = extras.get(self.field.name + '-from') or u''
                to = extras.get(self.field.name + '-to') or u''
                from_form = field_types.DateType.db_to_form(from_)
                to_form = field_types.DateType.db_to_form(to)
            return (from_form, to_form)

        def render(self, **kwargs):
            from_, to = self._get_value()
            from_html = fa_h.text_field(self.name + '-from', value=from_, **kwargs)
            to_html = fa_h.text_field(self.name + '-to', value=to, **kwargs)
            html = '%s - %s' % (from_html, to_html)
            return html

        def render_readonly(self, **kwargs):
            val = self._get_value()
            if not val:
                val = u'', u''
            from_, to = val
            if to:
                val_str = '%s - %s' % (from_, to)
            else:            
                val_str = '%s' % from_
            return field_readonly_renderer(self.field.key, val_str)

        def _serialized_value(self):
            # interpret params like this:
            # 'Package--temporal_coverage-from', u'4/12/2009'
            param_val_from = self._params.get(self.name + '-from', u'')
            param_val_to = self._params.get(self.name + '-to', u'')
            return param_val_from, param_val_to

        def deserialize(self):
            return self._serialized_value()

class ResourcesField(ConfiguredField):
    '''A form field for multiple package resources.'''
    def get_configured(self):
        return self.ResourcesField(self.name).with_renderer(self.ResourcesRenderer)

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

    class ResourcesRenderer(formalchemy.fields.FieldRenderer):
        table_template = literal('''
          <table id="flexitable" prefix="%(id)s" class="no-margin">
            <tr> <th>URL</th><th>Format</th><th>Description</th><th>Hash</th> </tr>
    %(rows)s
          </table>
          <a href="javascript:addRowToTable()" id="add_resource"><img src="/images/icons/add.png"></a>
          ''')
        table_template_readonly = literal('''
          <table id="flexitable" prefix="%(id)s">
            <tr> <th>URL</th><th>Format</th><th>Description</th><th>Hash</th> </tr>
    %(rows)s
          </table>
          ''')
        # NB row_template needs to be kept in-step with flexitable's row creation.
        row_template = literal('''
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
        ''')
        row_template_readonly = literal('''
            <tr> <td><a href="%(url)s">%(url)s</a></td><td>%(format)s</td><td>%(description)s</td><td>%(description)s</td><td>%(hash)s</td> </tr>
        ''')

        def render(self, **kwargs):
            return self._render(readonly=False)

        def render_readonly(self, **kwargs):
            value_str = self._render(readonly=True)
            return field_readonly_renderer(self.field.key, value_str, newline_reqd=False)
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
                                         'rows':literal(''.join(rows))}
            else:
                html = ''
            return unicode(html)

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

class TagField(ConfiguredField):
    '''A form field for tags'''
    def get_configured(self):
        return self.TagField(self.name).with_renderer(self.TagEditRenderer).validate(self.tag_name_validator)

    class TagField(formalchemy.Field):
        def sync(self):
            if not self.is_readonly():
                # NOTE this should work - not sure why not
    #            setattr(self.model, self.name, self._deserialize())
                self._update_tags()

        def _update_tags(self):
            pkg = self.model
            tags = self._deserialize()
            # discard duplicates
            taglist = list(set([tag.name for tag in tags]))
            current_tags = [ tag.name for tag in pkg.tags ]
            for name in taglist:
                if name not in current_tags:
                    pkg.add_tag_by_name(name, autoflush=False)
            for pkgtag in pkg.package_tags:
                if pkgtag.tag.name not in taglist:
                    pkgtag.delete()

    class TagEditRenderer(formalchemy.fields.FieldRenderer):
        tag_field_template = literal('''
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
          ''')
        def render(self, **kwargs):
            tags_as_string = self._tags_string()
            return self.tag_field_template % (literal(fa_h.text_field(self.name, value=tags_as_string, size=60, **kwargs)), self.field.parent.model.id or '')

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
            return literal(' '.join([literal('<a href="/tag/read/%s">%s</a>' % (str(tag), str(tag))) for tag in tagnames]))

        def render_readonly(self, **kwargs):
            tags_as_string = self._tag_links()
            return field_readonly_renderer(self.field.key, tags_as_string)

        # Looks remarkably similar to _update_tags above
        def deserialize(self):
            tags_as_string = self._serialized_value() # space separated string
            package = self.field.parent.model
            #self._update_tags(package, tags_as_string)

            tags_as_string = tags_as_string.replace(',', ' ').lower()
            taglist = tags_as_string.split()
            def find_or_create_tag(name):
                tag = model.Tag.by_name(name, autoflush=False)
                if not tag:
                    tag = model.Tag(name=name)
                return tag
            tags = [find_or_create_tag(x) for x in taglist]
            return tags

    tagname_match = re.compile('[\w\-_.]*$', re.UNICODE)
    tagname_uppercase = re.compile('[A-Z]')
    def tag_name_validator(self, val, field):
        for tag in val:
            min_length = 2
            if len(tag.name) < min_length:
                raise formalchemy.ValidationError('Tag "%s" length is less than minimum %s' % (tag.name, min_length))
            if not self.tagname_match.match(tag.name):
                raise formalchemy.ValidationError('Tag "%s" must be alphanumeric characters or symbols: -_.' % (tag.name))
            if self.tagname_uppercase.search(tag.name):
                raise formalchemy.ValidationError('Tag "%s" must not be uppercase' % (tag.name))            

class ExtrasField(ConfiguredField):
    '''A form field for arbitrary "extras" package data.'''
    def get_configured(self):
        return self.ExtrasField(self.name).with_renderer(self.ExtrasRenderer).validate(self.extras_validator)

    def extras_validator(self, val, field=None):
        val_dict = dict(val)
        for key, value in val:
            if value != val_dict[key]:
                raise formalchemy.ValidationError('Duplicate key "%s"' % key)
            if value and not key:
                # Note value is allowed to by None - REST way of deleting fields.
                raise formalchemy.ValidationError('Extra key-value pair: key is not set.')

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
        extra_field_template = literal('''
        <div>
          <label class="field_opt" for="%(name)s">%(key)s</label>
          <input id="%(name)s" name="%(name)s" size="20" type="text" value="%(value)s">
          <input type=checkbox name="%(name)s-checkbox">Delete</input>
        </div>
        ''')
        blank_extra_field_template = literal('''
        <div class="extras-new-field">
          <label class="field_opt">New key</label>
          <input id="%(name)s-key" name="%(name)s-key" size="20" type="text">
          <label class="field_opt">Value</label>
          <input id="%(name)s-value" name="%(name)s-value" size="20" type="text">
        </div>
        ''')

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
                html_items.append(field_readonly_renderer(key, value))
            return html_items

        def deserialize(self):
            # Example params:
            # ('Package-1-extras', {...}) (via REST i/f)
            # ('Package-1-extras-genre', u'romantic novel'), (Package-1-extras-1-checkbox', 'on')
            # ('Package-1-extras-newfield0-key', u'aaa'), ('Package-1-extras-newfield0-value', u'bbb'),
            if not hasattr(self, 'extras_re'):
                self.extras_re = re.compile('Package-([a-f0-9-]*)-extras(?:-(\w+))?(?:-(\w+))?$')
            extra_fields = []
            for key, value in self._params.items():
                extras_match = self.extras_re.match(key)
                if not extras_match:
                    continue
                key_parts = extras_match.groups()
                package_id = key_parts[0]
                if key_parts[1] is None:
                    if isinstance(value, dict):
                        # simple dict passed into 'Package-1-extras' e.g. via REST i/f
                        extra_fields.extend(value.items())
                elif key_parts[2] is None:
                    # existing field
                    key = key_parts[1]
                    checkbox_key = 'Package-%s-extras-%s-checkbox' % (package_id, key)
                    delete = self._params.get(checkbox_key, '') == 'on'
                    if not delete:
                        extra_fields.append((key, value))
                elif key_parts[1].startswith('newfield'):
                    new_field_index = key_parts[1][len('newfield'):]
                    if key_parts[2] == u'key':
                        new_key = value
                        value_key = 'Package-%s-extras-newfield%s-value' % (package_id, new_field_index)
                        new_value = self._params.get(value_key, '')
                        if new_key or new_value:
                            extra_fields.append((new_key, new_value))
                    elif key_parts[2] == u'value':
                        # if it doesn't have a matching key, add it to extra_fields anyway for
                        # validation to fail
                        key_key = 'Package-%s-extras-newfield%s-key' % (package_id, new_field_index)
                        if not self._params.has_key(key_key):
                            extra_fields.append(('', value))                

            return extra_fields

class TextExtraField(ConfiguredField):
    '''A form field for basic text in an "extras" field.'''
    def get_configured(self):
        return self.TextExtraField(self.name).with_renderer(self.TextExtraRenderer)

    class TextExtraField(formalchemy.Field):
        def sync(self):
            if not self.is_readonly():
                pkg = self.model
                val = self._deserialize() or u''
                pkg.extras[self.name] = val

    class TextExtraRenderer(TextExtraRenderer):
        pass

class SuggestedTextExtraField(TextExtraField):
    '''A form field for text suggested from from a list of options, that is
    stored in an "extras" field.'''
    def __init__(self, name, options):
        self.options = options
        TextExtraField.__init__(self, name)

    def get_configured(self):
        return self.TextExtraField(self.name, options=self.options).with_renderer(self.SelectRenderer)

    class SelectRenderer(formalchemy.fields.FieldRenderer):
        def _get_value(self, **kwargs):
            extras = self.field.parent.model.extras
            return unicode(kwargs.get('selected', '') or self._value or extras.get(self.field.name, ''))

        def render(self, options, **kwargs):
            selected = self._get_value()
            options = [('', None)] + options + [('other - please specify', 'other')]
            if selected in options:
                select_field_selected = selected
                text_field_value = u''
            elif selected:
                select_field_selected = u'other'
                text_field_value = selected or u''
            else:
                select_field_selected = u''
                text_field_value = u''            
            html = literal(fa_h.select(self.name, fa_h.options_for_select(options, selected=select_field_selected, **kwargs)))
            other_name = self.name+'-other'
            html += literal('<label class="inline" for="%s">Other: %s</label>') % (other_name, literal(fa_h.text_field(other_name, value=text_field_value, **kwargs)))
            return html

        def render_readonly(self, **kwargs):
            return field_readonly_renderer(self.field.key, self._get_value())

        def _serialized_value(self):
            main_value = self._params.get(self.name, u'')
            other_value = self._params.get(self.name + '-other', u'')
            return other_value if main_value in ('', 'other') else main_value

class CheckboxExtraField(TextExtraField):
    '''A form field for a checkbox value, stored in an "extras" field as
    "yes" or "no".'''
    def get_configured(self):
        return self.TextExtraField(self.name).with_renderer(self.CheckboxExtraRenderer)

    class CheckboxExtraRenderer(formalchemy.fields.CheckBoxFieldRenderer):
        def _get_value(self):
            extras = self.field.parent.model.extras
            return bool(self._value or extras.get(self.field.name) == u'yes')

        def render(self, **kwargs):
            value = self._get_value()
            kwargs['size'] = '40'
            return fa_h.check_box(self.name, True, checked=value, **kwargs)
            return fa_h.text_field(self.name, value=value, maxlength=self.length, **kwargs)

        def render_readonly(self, **kwargs):
            value = u'yes' if self._get_value() else u'no'
            return field_readonly_renderer(self.field.key, value)

        def _serialized_value(self):
            # interpret params like this:
            # 'Package--some_field', u'True'
            param_val = self._params.get(self.name, u'')
            val = param_val == 'True'
            return val

        def deserialize(self):
            return u'yes' if self._serialized_value() else u'no'

def prettify(field_name):
    '''Generates a field label based on the field name.
    Used by the FormBuilder in method set_label_prettifier.'''
    field_name = field_name.capitalize()
    field_name = field_name.replace('_', ' ')
    return field_name
