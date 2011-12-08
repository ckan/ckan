import re
import logging

from formalchemy import helpers as fa_h
import formalchemy
import genshi
from pylons.templating import render_genshi as render
from pylons import c, config
from pylons.i18n import _, ungettext, N_, gettext

from ckan.lib.helpers import literal
from ckan.authz import Authorizer
import ckan.model as model
import ckan.lib.helpers as h
import ckan.lib.field_types as field_types
import ckan.misc
import ckan.lib.dictization.model_save as model_save

log = logging.getLogger(__name__)

name_match = re.compile('[a-z0-9_\-]*$')
def name_validator(val, field=None):
    # check basic textual rules
    min_length = 2
    if len(val) < min_length:
        raise formalchemy.ValidationError(_('Name must be at least %s characters long') % min_length)
    if not name_match.match(val):
        raise formalchemy.ValidationError(_('Name must be purely lowercase alphanumeric (ascii) characters and these symbols: -_'))

def package_exists(val):
    if model.Session.query(model.Package).autoflush(False).filter_by(name=val).count():
        return True
    return False

def package_name_validator(val, field=None):
    name_validator(val, field)
    # we disable autoflush here since may get used in dataset preview
    pkgs = model.Session.query(model.Package).autoflush(False).filter_by(name=val)
    for pkg in pkgs:
        if pkg != field.parent.model:
            raise formalchemy.ValidationError(_('Dataset name already exists in database'))

def group_exists(val):
    if model.Session.query(model.Group).autoflush(False).filter_by(name=val).count():
        return True
    return False

def group_name_validator(val, field=None):
    name_validator(val, field)
    # we disable autoflush here since may get used in dataset preview
    groups = model.Session.query(model.Group).autoflush(False).filter_by(name=val)
    for group in groups:
        if group != field.parent.model:
            raise formalchemy.ValidationError(_('Group name already exists in database'))


def field_readonly_renderer(key, value, newline_reqd=False):
    if value is None:
        value = ''
    html = literal('<p>%s</p>') % value
    if newline_reqd:
        html += literal('<br/>')
    return html

class CoreField(formalchemy.fields.Field):
    '''A field which can sync to a core field in the model.
    Use this for overriding AttributeFields when you want to be able
    to set a default value without having to change the sqla Column default.'''
    def sync(self):
        if not self.is_readonly():
            setattr(self.model, self.name, self._deserialize())
    

class DateTimeFieldRenderer(formalchemy.fields.DateTimeFieldRenderer):
    def render_readonly(self, **kwargs):
        return field_readonly_renderer(self.field.key,
                formalchemy.fields.DateTimeFieldRenderer.render_readonly(self, **kwargs))

class CheckboxFieldRenderer(formalchemy.fields.CheckBoxFieldRenderer):
    def render_readonly(self, **kwargs):
        value = u'yes' if self.raw_value else u'no'
        return field_readonly_renderer(self.field.key, value)

class TextRenderer(formalchemy.fields.TextFieldRenderer):
    def render_readonly(self, **kwargs):
        return field_readonly_renderer(self.field.key, self.raw_value)

class SelectFieldRenderer(formalchemy.fields.SelectFieldRenderer):
    def render_readonly(self, **kwargs):
        return field_readonly_renderer(self.field.key,
                formalchemy.fields.SelectFieldRenderer.render_readonly(self, **kwargs))

class TextAreaRenderer(formalchemy.fields.TextAreaFieldRenderer):
    def render_readonly(self, **kwargs):
        return field_readonly_renderer(self.field.key, self.raw_value)

class TextExtraRenderer(formalchemy.fields.TextFieldRenderer):
    def render(self, **kwargs):
        kwargs['size'] = '40'
        return fa_h.text_field(self.name, value=self.value, maxlength=self.length, **kwargs)

    def render_readonly(self, **kwargs):
        return field_readonly_renderer(self.field.key, self.value)


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
        def __init__(self, *args, **kwargs):
            self._null_option = (_('(None)'), u'')
            super(self.__class__, self).__init__(*args, **kwargs)

        @property
        def raw_value(self):
            return self.model.extras.get(self.name)
            
        def sync(self):
            if not self.is_readonly():
                pkg = self.model
                val = self._deserialize() or u''
                pkg.extras[self.name] = val

    class TextExtraRenderer(TextExtraRenderer):
        pass

class TextAreaExtraField(RegExValidatingField):
    '''A form field for basic text in an "extras" field.'''
    def get_configured(self):
        field = self.TextAreaExtraField(self.name).with_renderer(self.TextAreaRenderer, **self.kwargs)
        return RegExValidatingField.get_configured(self, field)

    class TextAreaExtraField(formalchemy.Field):
        def __init__(self, *args, **kwargs):
            super(self.__class__, self).__init__(*args, **kwargs)

        @property
        def raw_value(self):
            return self.model.extras.get(self.name)
            
        def sync(self):
            if not self.is_readonly():
                pkg = self.model
                val = self._deserialize() or u''
                pkg.extras[self.name] = val

    class TextAreaRenderer(TextAreaRenderer):
        pass

class DateExtraField(ConfiguredField):
    '''A form field for DateType data stored in an 'extra' field.'''
    def get_configured(self):
        return self.DateExtraFieldField(self.name).with_renderer(self.DateExtraRenderer).validate(field_types.DateType.form_validator)

    class DateExtraFieldField(formalchemy.Field):
        @property
        def raw_value(self):
            db_date = self.model.extras.get(self.name)
            if db_date:
                return field_types.DateType.db_to_form(db_date)
            else:
                return None
            
        def sync(self):
            if not self.is_readonly():
                form_date = self._deserialize()
                date_db = field_types.DateType.form_to_db(form_date, may_except=False)
                self.model.extras[self.name] = date_db

    class DateExtraRenderer(TextExtraRenderer):
        def __init__(self, field):
            super(DateExtraField.DateExtraRenderer, self).__init__(field)

        def render_readonly(self, **kwargs):
            return field_readonly_renderer(self.field.key, self.value)

class DateRangeExtraField(ConfiguredField):
    '''A form field for two DateType fields, representing a date range,
    stored in 'extra' fields.'''
    def get_configured(self):
        return self.DateRangeField(self.name).with_renderer(self.DateRangeRenderer).validate(self.validator)

    def validator(self, form_date_tuple, field=None):
        assert isinstance(form_date_tuple, (tuple, list)), form_date_tuple
        from_, to_ = form_date_tuple
        return field_types.DateType.form_validator(from_) and \
               field_types.DateType.form_validator(to_)

    class DateRangeField(formalchemy.Field):
        @property
        def raw_value(self):
            extras = self.model.extras
            from_ = extras.get(self.name + '-from', u'')
            to = extras.get(self.name + '-to', u'')
            from_form = field_types.DateType.db_to_form(from_)
            to_form = field_types.DateType.db_to_form(to)
            return (from_form, to_form)

        @property
        def is_collection(self):
            # Become a collection to allow two values to be passed around.
            return True

        def sync(self):
            if not self.is_readonly():
                pkg = self.model
                vals = self._deserialize() or u''
                pkg.extras[self.name + '-from'] = field_types.DateType.form_to_db(vals[0], may_except=False)
                pkg.extras[self.name + '-to'] = field_types.DateType.form_to_db(vals[1], may_except=False)

    class DateRangeRenderer(formalchemy.fields.FieldRenderer):
        def render(self, **kwargs):
            from_, to = self.value
            from_html = fa_h.text_field(self.name + '-from', value=from_, class_="medium-width", **kwargs)
            to_html = fa_h.text_field(self.name + '-to', value=to, class_="medium-width", **kwargs)
            html = '%s - %s' % (from_html, to_html)
            return html

        def render_readonly(self, **kwargs):
            from_, to = self.value or (u'', u'')
            if to:
                val_str = '%s - %s' % (from_, to)
            else:            
                val_str = '%s' % from_
            return field_readonly_renderer(self.field.key, val_str)

        def _serialized_value(self):
            # interpret params like this:
            # 'Dataset--temporal_coverage-from', u'4/12/2009'
            param_val_from = self.params.get(self.name + '-from', u'')
            param_val_to = self.params.get(self.name + '-to', u'')
            return param_val_from, param_val_to


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
            #TODO Refactor this into field raw_value, like in DateRangeExtraField
            extras = self.field.parent.model.extras
            if self.value:
                from_form, to_form = self.value
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
    '''A form field for multiple dataset resources.'''

    def __init__(self, name, hidden_label=False, fields_required=None):
        super(ResourcesField, self).__init__(name)
        self._hidden_label = hidden_label
        self.fields_required = fields_required or set(['url'])
        assert isinstance(self.fields_required, set)

    def resource_validator(self, val, field=None):
        resources_data = val
        assert isinstance(resources_data, list)
        not_nothing_regex = re.compile('\S')
        errormsg = _('Dataset resource(s) incomplete.')
        not_nothing_validator = formalchemy.validators.regex(not_nothing_regex,
                                                             errormsg)
        for resource_data in resources_data:
            assert isinstance(resource_data, dict)
            for field in self.fields_required:
                value = resource_data.get(field, '')
                not_nothing_validator(value, field)
            
    def get_configured(self):
        field = self.ResourcesField(self.name).with_renderer(self.ResourcesRenderer).validate(self.resource_validator)
        field._hidden_label = self._hidden_label
        field.fields_required = self.fields_required
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

        def is_required(self, field_name=None):
            if not field_name:
                return False
            else:
                return field_name in self.fields_required


    class ResourcesRenderer(formalchemy.fields.FieldRenderer):
        def render(self, **kwargs):
            c.resources = self.value or []
            # [:] does a copy, so we don't change original
            c.resources = c.resources[:]
            c.resources.extend([None])
            c.id = self.name
            c.columns = model.Resource.get_columns()
            c.field = self.field
            c.fieldset = self.field.parent
            return render('package/form_resources.html')            

        def stringify_value(self, v):
            # actually returns dict here for _value
            # multiple=True means v is a Resource
            res_dict = {}
            if v:
                assert isinstance(v, model.Resource)
                for col in model.Resource.get_columns() + ['id']:
                    res_dict[col] = getattr(v, col)
            return res_dict

        def _serialized_value(self):
            package = self.field.parent.model
            params = self.params
            new_resources = []
            rest_key = self.name

            # REST param format
            # e.g. 'Dataset-1-resources': [{u'url':u'http://ww...
            if params.has_key(rest_key) and any(params.getall(rest_key)):
                new_resources = params.getall(rest_key)[:] # copy, so don't edit orig

            # formalchemy form param format
            # e.g. 'Dataset-1-resources-0-url': u'http://ww...'
            row = 0
            # The base columns historically defaulted to empty strings
            # not None (Null). This is why they are seperate here.
            base_columns = ['url', 'format', 'description', 'hash', 'id']
            while True:
                if not params.has_key('%s-%i-url' % (self.name, row)):
                    break
                new_resource = {}
                blank_row = True
                for col in model.Resource.get_columns() + ['id']:
                    if col in base_columns:
                        value = params.get('%s-%i-%s' % (self.name, row, col), u'')
                    else:
                        value = params.get('%s-%i-%s' % (self.name, row, col))
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
        @property
        def raw_value(self):
            tag_objects = self.model.tags
            tag_names = [tag.name for tag in tag_objects]
            return tag_names
        
        def sync(self):
            if not self.is_readonly():
                # Note: You might think that you could just assign
                # self.model.tags with tag objects, but the model 
                # (add_stateful_versioned_m2m) doesn't support this -
                # you must edit each PackageTag individually.
                self._update_tags()

        def _update_tags(self):
            pkg = self.model
            updated_tags = set(self._deserialize())
            existing_tags = set(self.raw_value)
            for tag in updated_tags - existing_tags:
                pkg.add_tag_by_name(tag, autoflush=False)
            tags_to_delete = existing_tags - updated_tags
            for pkgtag in pkg.package_tags:
                if pkgtag.tag.name in tags_to_delete:
                    pkgtag.delete()

        @property
        def is_collection(self):
            # Become a collection to allow value to be a list of tag strings
            return True

    class TagEditRenderer(formalchemy.fields.FieldRenderer):
        def render(self, **kwargs):
            kwargs['value'] = ', '.join(self.value)
            kwargs['size'] = 60
            api_url = config.get('ckan.api_url', '/').rstrip('/')
            tagcomplete_url = api_url+h.url_for(controller='api',
                    action='tag_autocomplete', id=None)
            kwargs['data-tagcomplete-url'] = tagcomplete_url
            kwargs['data-tagcomplete-queryparam'] = 'incomplete'
            kwargs['class'] = 'long tagComplete'
            html = literal(fa_h.text_field(self.name, **kwargs))
            return html

        def _tag_links(self):
            tags = self.value
            tag_links = [h.link_to(tagname, h.url_for(controller='tag', action='read', id=tagname)) for tagname in tags]
            return literal(', '.join(tag_links))

        def render_readonly(self, **kwargs):
            tag_links = self._tag_links()
            return field_readonly_renderer(self.field.key, tag_links)

        def _serialized_value(self):
            # despite being a collection, there is only one field to get
            # the values from
            tags_as_string = self.params.getone(self.name).strip()
            if tags_as_string == "":
                return []
            tags = map(lambda s: s.strip(), tags_as_string.split(','))
            return tags
            
    tagname_match = re.compile('[^"]*$') # already split on commas
    def tag_name_validator(self, val, field):
        for tag in val:
        
            # formalchemy deserializes an empty string into None.
            # This happens if the tagstring gets split on commas, and
            # there's an empty string in the resulting list.
            # e.g. "tag1,,tag2" ; "  ,tag1" and "tag1," will all result
            # in an empty tag name.
            if tag is None:
                tag = u'' # let the minimum length validator take care of it.

            min_length = 2
            if len(tag) < min_length:
                raise formalchemy.ValidationError(_('Tag "%s" length is less than minimum %s') % (tag, min_length))
            if not self.tagname_match.match(tag):
                raise formalchemy.ValidationError(_('Tag "%s" must not contain any quotation marks: "') % (tag))

class ExtrasField(ConfiguredField):
    '''A form field for arbitrary "extras" dataset data.'''
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
        @property
        def raw_value(self):
            return self.model.extras.items() or []
            
        @property
        def is_collection(self):
            # Become a collection to allow multiple values to be passed around.
            return True

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
        @property
        def value(self):
            '''
            Override 'value' method to avoid stringifying each
            extra key-value pair.
            '''
            if not self.field.is_readonly() and self.params is not None:
                v = self.deserialize()
            else:
                v = None
            return v or self.field.model_value

        def render(self, **kwargs):
            extras = self.value
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
            html = render('package/form_extra_fields.html')
            return h.literal(html)

        def render_readonly(self, **kwargs):
            html_items = []
            for key, value in self.value:
                html_items.append(field_readonly_renderer(key, value))
            return html_items

        def deserialize(self):
            # Example params:
            # ('Dataset-1-extras', {...}) (via REST i/f)
            # ('Dataset-1-extras-genre', u'romantic novel'),
            # ('Dataset-1-extras-genre-checkbox', 'on')
            # ('Dataset-1-extras-newfield0-key', u'aaa'),
            # ('Dataset-1-extras-newfield0-value', u'bbb'),
            # TODO: This method is run multiple times per edit - cache results?
            if not hasattr(self, 'extras_re'):
                self.extras_re = re.compile('([a-zA-Z0-9-]*)-([a-f0-9-]*)-extras(?:-(.+))?$')
                self.newfield_re = re.compile('newfield(\d+)-(.*)')
            extra_fields = []
            for key, value in self.params.items():
                extras_match = self.extras_re.match(key)
                if not extras_match:
                    continue
                key_parts = extras_match.groups()
                entity_name = key_parts[0]
                entity_id = key_parts[1]
                if key_parts[2] is None:
                    if isinstance(value, dict):
                        # simple dict passed into 'Dataset-1-extras' e.g. via REST i/f
                        extra_fields.extend(value.items())
                elif key_parts[2].startswith('newfield'):
                    newfield_match = self.newfield_re.match(key_parts[2])
                    if not newfield_match:
                        log.warn('Did not parse newfield correctly: %r', key_parts)
                        continue
                    new_field_index, key_or_value = newfield_match.groups()
                    if key_or_value == 'key':
                        new_key = value
                        value_key = '%s-%s-extras-newfield%s-value' % (entity_name, entity_id, new_field_index)
                        new_value = self.params.get(value_key, '')
                        if new_key or new_value:
                            extra_fields.append((new_key, new_value))
                    elif key_or_value == 'value':
                        # if it doesn't have a matching key, add it to extra_fields anyway for
                        # validation to fail
                        key_key = '%s-%s-extras-newfield%s-key' % (entity_name, entity_id, new_field_index)
                        if not self.params.has_key(key_key):
                            extra_fields.append(('', value))
                    else:
                        log.warn('Expected key or value for newfield: %r' % key)
                elif key_parts[2].endswith('-checkbox'):
                    continue
                else:
                    # existing field
                    key = key_parts[2].decode('utf8')
                    checkbox_key = '%s-%s-extras-%s-checkbox' % (entity_name, entity_id, key)
                    delete = self.params.get(checkbox_key, '') == 'on'
                    if not delete:
                        extra_fields.append((key, value))
            return extra_fields


class GroupSelectField(ConfiguredField):
    '''A form field for selecting groups'''
    
    def __init__(self, name, allow_empty=True, multiple=True, user_editable_groups=None):
        super(GroupSelectField, self).__init__(name)
        self.allow_empty = allow_empty
        self.multiple = multiple
        assert user_editable_groups is not None
        self.user_editable_groups = user_editable_groups
    
    def get_configured(self):
        field = self.GroupSelectionField(self.name, self.allow_empty).with_renderer(self.GroupSelectEditRenderer)
        field.set(multiple=self.multiple)
        field.user_editable_groups = self.user_editable_groups
        return field

    class GroupSelectionField(formalchemy.Field):
        def __init__(self, name, allow_empty):
            formalchemy.Field.__init__(self, name)
            self.allow_empty = allow_empty

        def sync(self):
            if not self.is_readonly():
                self._update_groups()

        def _update_groups(self):
            new_group_ids = self._deserialize() or []

            group_dicts = [dict(id = group_id) for 
                           group_id in new_group_ids]

            context = {'model': model, 'session': model.Session}
            model_save.package_membership_list_save(
                group_dicts, self.parent.model, context)
            
        def requires_label(self):
            return False
        requires_label = property(requires_label)

    class GroupSelectEditRenderer(formalchemy.fields.FieldRenderer):
        def _get_value(self, **kwargs):
            return self.field.parent.model.get_groups()

        def _get_user_editable_groups(self):
            return self.field.user_editable_groups
       
        def render(self, **kwargs):
            # Get groups which are editable by the user.
            editable_groups = self._get_user_editable_groups()

            # Get groups which are already selected.
            selected_groups = self._get_value()

            # Make checkboxes HTML from selected groups.
            checkboxes_html = ''
            checkbox_action = '<input type="checkbox" name="%(name)s" checked="checked" value="%(id)s" />'
            checkbox_noaction = '&nbsp;'
            checkbox_template = '''
            <dt>
                %(action)s
            </dt>
            <dd>
                <label for="%(name)s">%(title)s</label><br/>
            </dd>
            '''
            for group in selected_groups:
                checkbox_context = {
                    'id': group.id,
                    'name': self.name + '-' + group.id,
                    'title': group.display_name
                }
                action = checkbox_noaction
                if group in editable_groups:
                    context = {
                        'id': group.id,
                        'name': self.name + '-' + group.id
                    }
                    action = checkbox_action % context
                # Make checkbox HTML from a group.
                checkbox_context = {
                    'action': action,
                    'name': self.name + '-' + group.id,
                    'title': group.display_name
                }
                checkbox_html = checkbox_template % checkbox_context
                checkboxes_html += checkbox_html

            # Infer addable groups, subtract selected from editable groups.
            addable_groups = []
            for group in editable_groups:
                if group not in selected_groups:
                    addable_groups.append(group)

            # Construct addable options from addable groups.
            options = []
            if len(addable_groups):
                if self.field.allow_empty or len(selected_groups):
                    options.append(('', _('(None)')))
            for group in addable_groups:
                options.append((group.id, group.display_name))

            # Make select HTML.
            if len(options):
                new_name = self.name + '-new'
                select_html = h.select(new_name, None, options)
            else:
                # Todo: Translation call.
                select_html = _("Cannot add any groups.")

            # Make the field HTML.
            field_template = '''  
        <dl> %(checkboxes)s      
            <dt>
                %(label)s
            </dt>
            <dd> %(select)s
            </dd>
        </dl>
            '''
            field_context = {
                'checkboxes': checkboxes_html,
                'select': select_html,
                'label': _("Group"),
            } 
            field_html = field_template % field_context

            # Convert to literals.
            return h.literal(field_html)

        def render_readonly(self, **kwargs):
            return field_readonly_renderer(self.field.key, self._get_value())

        def _serialized_value(self):
            name = self.name.encode('utf-8')
            return [v for k, v in self.params.items() if k.startswith(name)]
        
        def deserialize(self):
            # Return groups which have just been selected by the user.
            new_group_ids = self._serialized_value()
            if new_group_ids and isinstance(new_group_ids, list):
                # Either...
                if len(new_group_ids) == 1:
                    # Convert [['id1', 'id2', ...]] into ['id1,' 'id2', ...].
                    nested_value = new_group_ids[0]
                    if isinstance(new_group_ids, list):
                        new_group_ids = nested_value
                # Or...
                else:
                    # Convert [['id1'], ['id2'], ...] into ['id1,' 'id2', ...].
                    for (i, nested_value) in enumerate(new_group_ids):
                        if nested_value and isinstance(nested_value, list):
                            if len(nested_value) > 1:
                                msg = _("Can't derived new group selection from serialized value structured like this: %s") % nested_value
                                raise Exception, msg
                            new_group_ids[i] = nested_value[0]
                # Todo: Decide on the structure of a multiple-group selection.
            
            if new_group_ids and isinstance(new_group_ids, basestring):
                new_group_ids = [new_group_ids]

            return new_group_ids



class SelectExtraField(TextExtraField):
    '''A form field for text suggested from from a list of options, that is
    stored in an "extras" field.'''
    
    def __init__(self, name, options, allow_empty=True):
        self.options = options[:]
        self.is_required = not allow_empty
        # ensure options have key and value, not just a value
        for i, option in enumerate(self.options):
            if not isinstance(option, (tuple, list)):
                self.options[i] = (option, option)
        super(SelectExtraField, self).__init__(name)

    def get_configured(self):
        field = self.TextExtraField(self.name, options=self.options)
        field_configured = field.with_renderer(self.SelectRenderer).validate(self.validate)
        if self.is_required:
            field_configured = field_configured.required()
        return field_configured

    def validate(self, value, field=None):
        if not value:
            # if value is required then this is checked by 'required' validator
            return
        if value not in [id_ for label, id_ in self.options]:
            raise formalchemy.ValidationError('Value %r is not one of the options.' % id_)

    class SelectRenderer(formalchemy.fields.SelectFieldRenderer):
        def _serialized_value(self):
            return self.params.get(self.name, u'')

        def render(self, options, **kwargs):
            # @param options - an iterable of (label, value)
            if not self.field.is_required():
                options = list(options)
                if options and isinstance(options[0], (tuple, list)):
                    null_option = self.field._null_option
                else:
                    null_option = self.field._null_option[1]
                options.insert(0, self.field._null_option)
            return formalchemy.fields.SelectFieldRenderer.render(self, options, **kwargs)

        def render_readonly(self, **kwargs):
            return field_readonly_renderer(self.field.key, self.value)


class SuggestedTextExtraField(TextExtraField):
    '''A form field for text suggested from from a list of options, that is
    stored in an "extras" field.'''
    def __init__(self, name, options, default=None):
        self.options = options[:]
        self.default = default
        # ensure options have key and value, not just a value
        for i, option in enumerate(self.options):
            if not isinstance(option, (tuple, list)):
                self.options[i] = (option, option)
        super(SuggestedTextExtraField, self).__init__(name)

    def get_configured(self):
        field = self.TextExtraField(self.name, options=self.options)
        field.default = self.default
        return field.with_renderer(self.SelectRenderer)

    class SelectRenderer(formalchemy.fields.FieldRenderer):
        def render(self, options, **kwargs):
            selected = self.value 
            if selected is None: 
                selected = self.field.default
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
            html = literal(fa_h.select(self.name, select_field_selected,
                options, class_="short", **kwargs))
                
            other_name = self.name+'-other'
            html += literal('<label class="inline" for="%s">%s: %s</label>') % (other_name, _('Other'), literal(fa_h.text_field(other_name, value=text_field_value, class_="medium-width", **kwargs)))
            return html

        def render_readonly(self, **kwargs):
            return field_readonly_renderer(self.field.key, self.value)

        def _serialized_value(self):
            main_value = self.params.get(self.name, u'')
            other_value = self.params.get(self.name + '-other', u'')
            return other_value if main_value in ('', 'other') else main_value

class CheckboxExtraField(TextExtraField):
    '''A form field for a checkbox value, stored in an "extras" field as
    "yes" or "no".'''
    def get_configured(self):
        return self.CheckboxExtraField(self.name).with_renderer(self.CheckboxExtraRenderer)

    class CheckboxExtraField(formalchemy.fields.Field):
        @property
        def raw_value(self):
            extras = self.model.extras
            return u'yes' if extras.get(self.name) == u'yes' else u'no'

        def sync(self):
            if not self.is_readonly():
                store_value = u'yes' if self._deserialize() else u'no'
                self.model.extras[self.name] = store_value
    
    class CheckboxExtraRenderer(formalchemy.fields.CheckBoxFieldRenderer):
        def render(self, **kwargs):
            kwargs['size'] = '40'
            bool_value = (self.value == u'yes')
            return fa_h.check_box(self.name, u'yes', checked=bool_value, **kwargs)
            return fa_h.text_field(self.name, value=bool_value, maxlength=self.length, **kwargs)

        def render_readonly(self, **kwargs):
            return field_readonly_renderer(self.field.key, self.value)


class PackageNameField(ConfiguredField):
    
    def get_configured(self):
        return self.PackageNameField(self.name).with_renderer(self.PackageNameRenderer)

    class PackageNameField(formalchemy.Field):
        pass
        
    class PackageNameRenderer(formalchemy.fields.FieldRenderer):
        pass


class UserNameField(ConfiguredField):

    def get_configured(self):
        return self.UserNameField(self.name).with_renderer(self.UserNameRenderer)

    class UserNameField(formalchemy.Field):
        pass

    class UserNameRenderer(formalchemy.fields.FieldRenderer):
        pass


def prettify(field_name):
    '''Generates a field label based on the field name.
    Used by the FormBuilder in method set_label_prettifier.
    Also does i18n.'''
    field_name = field_name.capitalize()
    field_name = field_name.replace('_', ' ')
    return _(field_name)
