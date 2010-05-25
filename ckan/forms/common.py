import re

from formalchemy import helpers as fa_h
import formalchemy
import genshi
from pylons.templating import render
from pylons import c
from pylons.i18n import _, ungettext, N_, gettext

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
        raise formalchemy.ValidationError(_('Name must be at least %s characters long') % min_length)
    if not name_match.match(val):
        raise formalchemy.ValidationError(_('Name must be purely lowercase alphanumeric (ascii) characters and these symbols: -_'))
        
def package_name_validator(val, field=None):
    name_validator(val, field)
    # we disable autoflush here since may get used in package preview
    pkgs = model.Session.query(model.Package).autoflush(False).filter_by(name=val)
    for pkg in pkgs:
        if pkg != field.parent.model:
            raise formalchemy.ValidationError(_('Package name already exists in database'))

def group_name_validator(val, field=None):
    name_validator(val, field)
    # we disable autoflush here since may get used in package preview
    groups = model.Session.query(model.Group).autoflush(False).filter_by(name=val)
    for group in groups:
        if group != field.parent.model:
            raise formalchemy.ValidationError(_('Group name already exists in database'))

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
    def __init__(self, name, **kwargs):
        self.name = name
        self.kwargs = kwargs

class RegExValidatingField(ConfiguredField):
    '''Inherit from this for fields that need a regex validator.
    @param validate_re - ("regex", "equivalent format but human readable")
    '''
    def __init__(self, name, validate_re=None, **kwargs):
        super(RegExValidatingField, self).__init__(name, **kwargs)
        self._validate_re = validate_re
        if validate_re:
            assert isinstance(validate_re, tuple)
            assert isinstance(validate_re[0], str) # reg ex
            assert isinstance(validate_re[1], (str, unicode)) # user readable format    

    def get_configured(self, field):
        if self._validate_re:
            field = field.validate(self.validate_re)
        return field

    def validate_re(self, value, field=None):
        if value:
            match = re.match(self._validate_re[0], value)
            if not match:
                raise formalchemy.ValidationError(_('Value does not match required format: %s') % self._validate_re[1])

class RegExRangeValidatingField(RegExValidatingField):
    '''Validates a range field (each value is validated on the same regex)'''
    def validate_re(self, values, field=None):
        for value in values:
            RegExValidatingField.validate_re(self, value, field=field)
            

class TextExtraField(RegExValidatingField):
    '''A form field for basic text in an "extras" field.'''
    def get_configured(self):
        field = self.TextExtraField(self.name).with_renderer(self.TextExtraRenderer, **self.kwargs)
        return RegExValidatingField.get_configured(self, field)

    class TextExtraField(formalchemy.Field):
        def sync(self):
            if not self.is_readonly():
                pkg = self.model
                val = self._deserialize() or u''
                pkg.extras[self.name] = val

    class TextExtraRenderer(TextExtraRenderer):
        pass

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
            super(DateExtraField.DateExtraRenderer, self).__init__(field)

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
            from_html = fa_h.text_field(self.name + '-from', value=from_, class_="medium-width", **kwargs)
            to_html = fa_h.text_field(self.name + '-to', value=to, class_="medium-width", **kwargs)
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
            param_val_from = self.params.get(self.name + '-from', u'')
            param_val_to = self.params.get(self.name + '-to', u'')
            return param_val_from, param_val_to

        def deserialize(self):
            return self._serialized_value()

class TextRangeExtraField(RegExRangeValidatingField):
    '''A form field for two TextType fields, representing a range,
    stored in 'extra' fields.'''
    def get_configured(self):
        field = self.TextRangeField(self.name).with_renderer(self.TextRangeRenderer)
        return RegExRangeValidatingField.get_configured(self, field)

    class TextRangeField(formalchemy.Field):
        def sync(self):
            if not self.is_readonly():
                pkg = self.model
                vals = self._deserialize() or u''
                pkg.extras[self.name + '-from'] = vals[0]
                pkg.extras[self.name + '-to'] = vals[1]

    class TextRangeRenderer(formalchemy.fields.FieldRenderer):
        def _get_value(self):
            extras = self.field.parent.model.extras
            if self._value:
                from_form, to_form = self._value
            else:
                from_ = extras.get(self.field.name + '-from') or u''
                to = extras.get(self.field.name + '-to') or u''
                from_form = from_
                to_form = to
            return (from_form, to_form)

        def render(self, **kwargs):
            from_, to = self._get_value()
            from_html = fa_h.text_field(self.name + '-from', value=from_, class_="medium-width", **kwargs)
            to_html = fa_h.text_field(self.name + '-to', value=to, class_="medium-width", **kwargs)
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
            param_val_from = self.params.get(self.name + '-from', u'')
            param_val_to = self.params.get(self.name + '-to', u'')
            return param_val_from, param_val_to

        def deserialize(self):
            return self._serialized_value()

class ResourcesField(ConfiguredField):
    '''A form field for multiple package resources.'''

    def __init__(self, name, hidden_label=False):
        super(ResourcesField, self).__init__(name)
        self._hidden_label = hidden_label

    def url_validator(self, val, field=None):
        resources_data = val
        assert isinstance(resources_data, list)
        url_regex = re.compile('\S') # Todo: Restrict this further?
        errormsg = 'Package resources must have URLs.'
        validator = formalchemy.validators.regex(url_regex, errormsg)
        for resource_data in resources_data:
            assert isinstance(resource_data, dict)
            resource_url = resource_data.get('url', '')
            validator(resource_url, field)

    def get_configured(self):
        field = self.ResourcesField(self.name).with_renderer(self.ResourcesRenderer).validate(self.url_validator)
        field._hidden_label = self._hidden_label
        field.set(multiple=True)
        return field

    class ResourcesField(formalchemy.Field):
        def sync(self):
            if not self.is_readonly():
                pkg = self.model
                res_dicts = self._deserialize() or []
                pkg.update_resources(res_dicts, autoflush=False)

        def requires_label(self):
            return not self._hidden_label
        requires_label = property(requires_label)

        @property
        def raw_value(self):
            # need this because it is a property
            return getattr(self.model, self.name)


    class ResourcesRenderer(formalchemy.fields.FieldRenderer):
        def render(self, **kwargs):
            c.resources = self._value or []
            # [:] does a copy, so we don't change original
            c.resources = c.resources[:]
            c.resources.extend([None])
            c.id = self.name
            return render('package/form_resources')            

        def stringify_value(self, v):
            # actually returns dict here for _value
            # multiple=True means v is a PackageResource
            res_dict = {}
            if v:
                assert isinstance(v, model.PackageResource)
                for col in model.PackageResource.get_columns() + ['id']:
                    res_dict[col] = getattr(v, col)
            return res_dict

        def _serialized_value(self):
            package = self.field.parent.model
            params = dict(self.params)
            new_resources = []
            rest_key = self.name

            # REST param format
            # e.g. 'Package-1-resources': [{u'url':u'http://ww...
            if params.has_key(rest_key) and isinstance(params[rest_key], (list, tuple)):
                new_resources = params[rest_key][:] # copy, so don't edit orig

            # formalchemy form param format
            # e.g. 'Package-1-resources-0-url': u'http://ww...'
            row = 0
            while True:
                if not params.has_key('%s-%i-url' % (self.name, row)):
                    break
                new_resource = {}
                blank_row = True
                for col in model.PackageResource.get_columns() + ['id']:
                    value = params.get('%s-%i-%s' % (self.name, row, col), u'')
                    new_resource[col] = value
                    if col != 'id' and value:
                        blank_row = False
                if not blank_row:
                    new_resources.append(new_resource)
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
        def render(self, **kwargs):
            pkg_id = self.field.parent.model.id or ''
            kwargs['value'] = self._tags_string()
            kwargs['size'] = 60
            kwargs['data-tagcomplete-url'] = h.url_for(controller='tag', action='autocomplete', id=None)
            kwargs['data-tagcomplete-queryparam'] = 'incomplete'
            kwargs['class'] = 'long tagComplete'
            html = literal(fa_h.text_field(self.name, **kwargs))
            return html
                           
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
                raise formalchemy.ValidationError(_('Tag "%s" length is less than minimum %s') % (tag.name, min_length))
            if not self.tagname_match.match(tag.name):
                raise formalchemy.ValidationError(_('Tag "%s" must be alphanumeric characters or symbols: -_.') % (tag.name))
            if self.tagname_uppercase.search(tag.name):
                raise formalchemy.ValidationError(_('Tag "%s" must not be uppercase' % (tag.name)))

class ExtrasField(ConfiguredField):
    '''A form field for arbitrary "extras" package data.'''
    def __init__(self, name, hidden_label=False):
        super(ExtrasField, self).__init__(name)
        self._hidden_label = hidden_label

    def get_configured(self):
        field = self.ExtrasField(self.name).with_renderer(self.ExtrasRenderer).validate(self.extras_validator)
        field._hidden_label = self._hidden_label
        return field

    def extras_validator(self, val, field=None):
        val_dict = dict(val)
        for key, value in val:
            if value != val_dict[key]:
                raise formalchemy.ValidationError(_('Duplicate key "%s"') % key)
            if value and not key:
                # Note value is allowed to be None - REST way of deleting fields.
                raise formalchemy.ValidationError(_('Extra key-value pair: key is not set for value "%s".') % value)

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

        def requires_label(self):
            return not self._hidden_label
        requires_label = property(requires_label)


    class ExtrasRenderer(formalchemy.fields.FieldRenderer):
        def _get_value(self):
            extras = self.field.parent.extras.value
            if extras is None:
                extras = self.field.parent.model.extras.items() or []
            return extras

        def render(self, **kwargs):
            extras = self._get_value()
            html = ''
            field_values = []
            for key, value in extras:
                field_values.append({
                    'name':self.name + '-' + key,
                    'key':key.capitalize(),
                    'value':value,})
            for i in range(3):
                field_values.append({
                    'name':'%s-newfield%s' % (self.name, i)})
            c.fields = field_values
            html = render('package/form_extra_fields')
            return h.literal(html)

        def render_readonly(self, **kwargs):
            html_items = []
            extras = self._get_value()
            for key, value in extras:
                html_items.append(field_readonly_renderer(key, value))
            return html_items

        def deserialize(self):
            # Example params:
            # ('Package-1-extras', {...}) (via REST i/f)
            # ('Package-1-extras-genre', u'romantic novel'),
            # ('Package-1-extras-genre-checkbox', 'on')
            # ('Package-1-extras-newfield0-key', u'aaa'),
            # ('Package-1-extras-newfield0-value', u'bbb'),
            # TODO: This method is run multiple times per edit - cache results?
            if not hasattr(self, 'extras_re'):
                self.extras_re = re.compile('Package-([a-f0-9-]*)-extras(?:-(.+))?$')
                self.newfield_re = re.compile('newfield(\d+)-(.*)')
            extra_fields = []
            for key, value in self.params.items():
                extras_match = self.extras_re.match(key)
                if not extras_match:
                    continue
                key_parts = extras_match.groups()
                package_id = key_parts[0]
                if key_parts[1] is None:
                    if isinstance(value, dict):
                        # simple dict passed into 'Package-1-extras' e.g. via REST i/f
                        extra_fields.extend(value.items())
                elif key_parts[1].startswith('newfield'):
                    newfield_match = self.newfield_re.match(key_parts[1])
                    if not newfield_match:
                        print 'Warning: did not parse newfield correctly: ', ney_parts
                        continue
                    new_field_index, key_or_value = newfield_match.groups()
                    if key_or_value == 'key':
                        new_key = value
                        value_key = 'Package-%s-extras-newfield%s-value' % (package_id, new_field_index)
                        new_value = self.params.get(value_key, '')
                        if new_key or new_value:
                            extra_fields.append((new_key, new_value))
                    elif key_or_value == 'value':
                        # if it doesn't have a matching key, add it to extra_fields anyway for
                        # validation to fail
                        key_key = 'Package-%s-extras-newfield%s-key' % (package_id, new_field_index)
                        if not self.params.has_key(key_key):
                            extra_fields.append(('', value))
                    else:
                        print 'Warning: expected key or value for newfield: ', key
                elif key_parts[1].endswith('-checkbox'):
                    continue
                else:
                    # existing field
                    key = key_parts[1].decode('utf8')
                    checkbox_key = 'Package-%s-extras-%s-checkbox' % (package_id, key)
                    delete = self.params.get(checkbox_key, '') == 'on'
                    if not delete:
                        extra_fields.append((key, value))
            return extra_fields

class SuggestedTextExtraField(TextExtraField):
    '''A form field for text suggested from from a list of options, that is
    stored in an "extras" field.'''
    def __init__(self, name, options):
        self.options = options[:]
        # ensure options have key and value, not just a value
        for i, option in enumerate(self.options):
            if not isinstance(option, (tuple, list)):
                self.options[i] = (option, option)
        super(SuggestedTextExtraField, self).__init__(name)

    def get_configured(self):
        return self.TextExtraField(self.name, options=self.options).with_renderer(self.SelectRenderer)

    class SelectRenderer(formalchemy.fields.FieldRenderer):
        def _get_value(self, **kwargs):
            extras = self.field.parent.model.extras
            return unicode(kwargs.get('selected', '') or self._value or extras.get(self.field.name, ''))

        def render(self, options, **kwargs):
            selected = self._get_value()
            options = [('', '')] + options + [(_('other - please specify'), 'other')]
            option_keys = [key for value, key in options]
            if selected in option_keys:
                select_field_selected = selected
                text_field_value = u''
            elif selected:
                select_field_selected = u'other'
                text_field_value = selected or u''
            else:
                select_field_selected = u''
                text_field_value = u''
            fa_version_nums = formalchemy.__version__.split('.')
            # Requires FA 1.3.2 onwards for this select i/f
            html = literal(fa_h.select(self.name, select_field_selected, options, class_="short", **kwargs))
                
            other_name = self.name+'-other'
            html += literal('<label class="inline" for="%s">%s: %s</label>') % (other_name, _('Other'), literal(fa_h.text_field(other_name, value=text_field_value, class_="medium-width", **kwargs)))
            return html

        def render_readonly(self, **kwargs):
            return field_readonly_renderer(self.field.key, self._get_value())

        def _serialized_value(self):
            main_value = self.params.get(self.name, u'')
            other_value = self.params.get(self.name + '-other', u'')
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
            param_val = self.params.get(self.name, u'')
            val = param_val == 'True'
            return val

        def deserialize(self):
            return u'yes' if self._serialized_value() else u'no'

def prettify(field_name):
    '''Generates a field label based on the field name.
    Used by the FormBuilder in method set_label_prettifier.
    Also does i18n.'''
    field_name = field_name.capitalize()
    field_name = field_name.replace('_', ' ')
    return _(field_name)
