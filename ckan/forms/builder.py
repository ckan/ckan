import formalchemy

from ckan import model
import common

class FormBuilder(object):
    '''Builds form fieldsets'''
    def __init__(self, base_object):
        self.fs = formalchemy.FieldSet(base_object)
        self.added_fields = []
        self.options = self.fs._fields # {field_name:fs.field}
        self.includes = None

    def add_field(self, field):
        if isinstance(field, common.ConfiguredField):
            field = field.get_configured()
        assert isinstance(field, formalchemy.Field), field
        self.fs.append(field)

    def set_field_option(self, field_name, option, *args):
        field = self.options[field_name]
        assert field
        option = getattr(field, option)
        if isinstance(args[0], dict):
            self.options[field_name] = option(**args[0])
        else:
            self.options[field_name] = option(*args)

    def set_field_text(self, field_name, label_txt, hint_txt=None):
        self.set_field_option(field_name, 'label', label_txt)
        if hint_txt:
            hint_html = '<p class="desc">%s</p>' % hint_txt
            self.set_field_option(field_name, 'with_metadata', {'instructions':hint_html})

        return
        
    def set_displayed_fields(self, field_name_list):
        assert isinstance(field_name_list, (list, tuple))
        self.includes = field_name_list

    def set_label_prettifier(self, prettify):
        '''@prettify function that munges field labels'''
        self.fs.prettify = prettify

    def get_fieldset(self):
        self.fs.configure(options=self.options.values(),
                          include=[getattr(self.fs, name) for name in self.includes])
        return_fs = self.fs
        self.fs = None # can't run this method again
        return return_fs
