import re

from formalchemy import helpers as h
import formalchemy
import genshi

import ckan.model as model
import ckan.lib.helpers
import ckan.misc

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

def field_readonly_renderer(key, value, newline_reqd=True):
    if value is None:
        value = ''
    key = key.capitalize().replace('_', ' ').replace('-', ' ')
    if key in ('Url', 'Download url', 'Taxonomy url'):
        key = key.replace(u'Url', u'URL')
        key = key.replace(u'url', u'URL')
        value = '<a href="%s">%s</a>' % (value, value)        
    html = '<strong>%s:</strong> %s' % (key, value)
    if newline_reqd:
        html += '<br/>'
    return html

class CustomTextFieldRenderer(formalchemy.fields.TextFieldRenderer):
    def render(self, **kwargs):
        kwargs['size'] = '40'
        field_tip = FIELD_TIPS.get(self.field.key)
        if field_tip:
            tip_html = FIELD_TIP_TEMPLATE % field_tip
        else:
            tip_html = ''        
        return h.text_field(self.name, value=self._value, maxlength=self.length, **kwargs) + tip_html

    def render_readonly(self, **kwargs):
        return field_readonly_renderer(self.field.key, self._value)

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

    def render_readonly(self, **kwargs):
        format = ckan.misc.MarkdownFormat()
        notes_formatted = format.to_html(self._value)
        notes_formatted = genshi.HTML(notes_formatted)
        return field_readonly_renderer(self.field.key, notes_formatted)
