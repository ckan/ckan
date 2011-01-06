import formalchemy
from pylons.templating import render_genshi as render
from pylons import c

import common

class CkanFieldset(formalchemy.FieldSet):
    default_renderers = {
        formalchemy.types.String:common.TextRenderer,
        'textarea':common.TextAreaRenderer,
        'dropdown': common.SelectFieldRenderer,
        'checkbox': common.CheckboxFieldRenderer,
        formalchemy.types.DateTime: common.DateTimeFieldRenderer,
        }
    def render(self, **kwargs):
        '''Override FormAlchemy rendering to use a Ckan template'''
        if hasattr(self, 'form_template') and self.form_template is not None:
            c.fieldset = self
            return render(self.form_template)
        else:
            return formalchemy.FieldSet.render(self, **kwargs)

    def get_field_groups(self):
        '''Used by the template to group fields'''
        groups = []
        for field in self.render_fields.values():
            group = field.metadata.get('field_group', '')
            if group not in groups:
                groups.append(group)
        return groups


class FormBuilder(object):
    '''Factory for form fieldsets'''
    def __init__(self, base_object):
        self.fs = CkanFieldset(base_object)
        self.added_fields = []
        self.options = self.fs._fields # {field_name:fs.field}
        self.includes = None
        self.set_form_template('package/form.html')

    def add_field(self, field):
        if isinstance(field, common.ConfiguredField):
            field = field.get_configured()
        assert isinstance(field, formalchemy.Field), field
        self.fs.append(field)

    def set_field_option(self, field_name, option, *args):
        field = self.options[field_name]
        assert field
        option = getattr(field, option)
        if args and isinstance(args[0], dict):
            self.options[field_name] = option(**args[0])
        else:
            self.options[field_name] = option(*args)

    def set_field_text(self, field_name, label=None, instructions=None, further_instructions=None, hints=None):
        '''
        Go beyond the default field text and customise the form label,
        instructions and/or hints.
        @param label - label on the form
        @param instructions - basic instructions for the field
        @param further_instructions - extra help (may need to be revealed
                                      on the form)
        @param hints - a short string to suggest an example field value
        '''
        if label:
            self.set_field_option(field_name, 'label', label)
        if instructions:
            self.set_field_option(field_name, 'with_metadata', {'basic_instructions':instructions})
        if further_instructions:
            self.set_field_option(field_name, 'with_metadata', {'further_instructions':further_instructions})
        if hints:
            self.set_field_option(field_name, 'with_metadata', {'hints':hints})

    def set_displayed_fields(self, groups_dict, focus_field=None):
        '''Sets fields to be displayed, what groupings they are in and
        what order groups and fields appear in.

        Each 'field group' is displayed in an html <fieldset> but we
        call it a group here so that it is not confused with
        FormAlchemy 'fieldsets'.
        
        @param groups_dict Dictionary of the lists of field names
                           keyed by the group name. e.g.:
          groups_dict = {'Basic information':['name', 'title'],
                         'Resources':['resources']}
          (Or use an sqlalchemy.util.OrderedDict to ensure order of groups)
        @param focus_field Name of field to have initial focus. If None,
           it defaults to the first field. If False, none are set to take
           focus.
        '''
        assert isinstance(groups_dict, dict), dict
        all_field_names = []
        for group_name, field_names in groups_dict.items():
            assert isinstance(group_name, (str, unicode))
            assert isinstance(field_names, (list, tuple))
            for field_name in field_names:
                assert isinstance(field_name, str)
                self.set_field_option(field_name, 'with_metadata', {'field_group':group_name})
            all_field_names += field_names
        self.includes = all_field_names
        self.focus = self.fs._fields[all_field_names[0]] \
                     if focus_field is None else focus_field
            
    def set_label_prettifier(self, prettify):
        '''@prettify function that munges field labels'''
        self.fs.prettify = prettify

    def set_form_template(self, template_path):
        self.fs.form_template = template_path

    def get_fieldset(self):
        self.fs.configure(options=self.options.values(),
                          include=[getattr(self.fs, name) for name in self.includes],
                          focus=self.focus)
        return_fs = self.fs
        self.fs = None # can't run this method again
        return return_fs
