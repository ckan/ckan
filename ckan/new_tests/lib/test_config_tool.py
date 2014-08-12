from ckan.lib import config_tool


class TestConfigTool:
    def test_edit(self):
        config_lines = '''
[app:main]
ckan.site_title = CKAN
        '''.split('\n')

        out = config_tool.config_edit_core(
            config_lines, 'app:main', 'ckan.site_title', 'New Title', 'edit')

        assert out == '''
[app:main]
ckan.site_title = New Title
        '''.split('\n'), out

    def test_new(self):
        config_lines = '''
[app:main]
ckan.site_title = CKAN
        '''.split('\n')

        out = config_tool.config_edit_core(
            config_lines, 'app:main', 'ckan.option', 'New stuff', 'add')

        assert out == '''
[app:main]
ckan.option = New stuff
ckan.site_title = CKAN
        '''.split('\n'), out

    def test_new_section(self):
        config_lines = '''
[app:main]
ckan.site_title = CKAN'''.split('\n')

        out = config_tool.config_edit_core(
            config_lines,
            'logger', 'keys', 'root, ckan, ckanext', 'add-section')

        assert out == '''
[app:main]
ckan.site_title = CKAN

[logger]
keys = root, ckan, ckanext'''.split('\n'), out
