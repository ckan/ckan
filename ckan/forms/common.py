import re

from formalchemy import helpers as h
import formalchemy

import ckan.model as model
import ckan.lib.helpers

FIELD_TIP_TEMPLATE = '<p class="desc">%s</p>'
FIELD_TIPS = {
    'name':"<strong>Unique identifier</strong> for package.<br/>2+ chars, lowercase, using only 'a-z0-9' and '-_'",
    'download_url':'Haven\'t already uploaded your package somewhere? We suggest using <a href="http://www.archive.org/create/">archive.org</a>.',
    'notes':'You can use <a href="http://daringfireball.net/projects/markdown/syntax">Markdown formatting</a> here.',
}

name_match = re.compile('[a-z0-9_\-]*$')
def name_validator(val, field=None):
    min_length = 2
    if len(val) < min_length:
        raise formalchemy.ValidationError('Name must be at least %s characters long' % min_length)
    if not name_match.match(val):
        raise formalchemy.ValidationError('Name must be purely lowercase alphanumeric (ascii) characters and these symbols: -_')

def package_names_validator(val, field=None):
    for pkg_name in val:    
        if not model.Package.by_name(pkg_name):
            raise formalchemy.ValidationError('Package name %s does not exist in database' % pkg_name)

class CustomTextFieldRenderer(formalchemy.fields.TextFieldRenderer):
    def render(self, **kwargs):
        kwargs['size'] = '40'
        field_tip = FIELD_TIPS.get(self.field.key)
        if field_tip:
            tip_html = FIELD_TIP_TEMPLATE % field_tip
        else:
            tip_html = ''        
        return h.text_field(self.name, value=self._value, maxlength=self.length, **kwargs) + tip_html

class TextAreaRenderer(formalchemy.fields.TextAreaFieldRenderer):
    def render(self, **kwargs):
        kwargs['size'] = '60x15'
        value = ckan.lib.helpers.escape(self._value)
        field_tip = FIELD_TIPS.get(self.field.key)
        if field_tip:
            tip_html = FIELD_TIP_TEMPLATE % field_tip
        else:
            tip_html = ''        
        return h.text_area(self.name, content=value, **kwargs) + tip_html
