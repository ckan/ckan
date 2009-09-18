FIELD_TIP_TEMPLATE = '<p class="desc">%s</p>'
FIELD_TIPS = {
    'name':"<strong>Unique identifier</strong> for package.<br/>2+ chars, lowercase, using only 'a-z0-9' and '-_'",
    'download_url':'Haven\'t already uploaded your package somewhere? We suggest using <a href="http://www.archive.org/create/">archive.org</a>.',
}

class CustomTextFieldRenderer(formalchemy.fields.TextFieldRenderer):
    def render(self, **kwargs):
        kwargs['size'] = '40'
        field_tip = FIELD_TIPS.get(self.field.key)
        if field_tip:
            tip_html = FIELD_TIP_TEMPLATE % field_tip
        else:
            tip_html = ''        
        return h.text_field(self.name, value=self._value, maxlength=self.length, **kwargs) + tip_html
