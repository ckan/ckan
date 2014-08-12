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

    def test_edit_commented_line(self):
        config_lines = '''
[app:main]
#ckan.site_title = CKAN
        '''.split('\n')

        out = config_tool.config_edit_core(
            config_lines, 'app:main', 'ckan.site_title', 'New Title', 'edit')

        assert out == '''
[app:main]
ckan.site_title = New Title
        '''.split('\n'), out

    def test_is_option_there_but_commented(self):
        config_lines = '''
[app:main]
#ckan.site_title = CKAN
        '''.split('\n')

        is_there = config_tool.is_option_there_but_commented(
            config_lines, 'app:main', 'ckan.site_title')

        assert is_there

    def test_is_option_there_but_commented__not(self):
        config_lines = '''
[app:main]
another_option = CKAN
        '''.split('\n')

        is_there = config_tool.is_option_there_but_commented(
            config_lines, 'app:main', 'ckan.site_title')

        assert not is_there
