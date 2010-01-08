item_template = '<li>%s</li>\n'

def package_render(fs, errors='', warnings=''):
    fields_html = ''
    for key, field in fs.render_fields.items():
        rendering = field.render_readonly()
        # Extra fields render_readonly as a list, so make others a list too.
        if not isinstance(rendering, list):
            rendering = [rendering]
        for rendering_item in rendering:
            fields_html += item_template % rendering_item
    if errors:
        fields_html += item_template % ('Errors: %s' % errors)
    if warnings:
        fields_html += item_template % ('Warnings: %s' % warnings)
    html = '<ul>\n%s\n</ul>\n' % fields_html
    return html
