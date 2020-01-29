# encoding: utf-8

from ckan.lib import config_tool


def changes_builder(action, key, value, section="app:main", commented=False):
    changes = config_tool.Changes()
    changes.add(action, config_tool.Option(section, key, value, commented))
    return changes


class TestMakeChanges:
    def test_edit(self):
        config_lines = """
[app:main]
ckan.site_title = CKAN
        """.split(
            "\n"
        )

        out = config_tool.make_changes(
            config_lines,
            [],
            changes_builder("edit", "ckan.site_title", "New Title"),
        )

        assert (
            out
            == """
[app:main]
ckan.site_title = New Title
        """.split(
                "\n"
            )
        ), out

    def test_new(self):
        config_lines = """
[app:main]
ckan.site_title = CKAN
        """.split(
            "\n"
        )

        out = config_tool.make_changes(
            config_lines,
            [],
            changes_builder("add", "ckan.option", "New stuff"),
        )

        assert (
            out
            == """
[app:main]
ckan.option = New stuff
ckan.site_title = CKAN
        """.split(
                "\n"
            )
        ), out

    def test_new_section(self):
        config_lines = """
""".split(
            "\n"
        )

        out = config_tool.make_changes(
            config_lines,
            ["logger"],
            changes_builder(
                "add", "keys", "root, ckan, ckanext", section="logger"
            ),
        )

        assert (
            out
            == """

[logger]
keys = root, ckan, ckanext
""".split(
                "\n"
            )
        ), out

    def test_new_section_before_appmain(self):
        config_lines = """
[app:main]
ckan.site_title = CKAN
""".split(
            "\n"
        )

        out = config_tool.make_changes(
            config_lines,
            ["logger"],
            changes_builder(
                "add", "keys", "root, ckan, ckanext", section="logger"
            ),
        )

        assert (
            out
            == """
[logger]
keys = root, ckan, ckanext

[app:main]
ckan.site_title = CKAN
""".split(
                "\n"
            )
        ), out

    def test_edit_commented_line(self):
        config_lines = """
[app:main]
#ckan.site_title = CKAN
        """.split(
            "\n"
        )

        out = config_tool.make_changes(
            config_lines,
            [],
            changes_builder("edit", "ckan.site_title", "New Title"),
        )

        assert (
            out
            == """
[app:main]
ckan.site_title = New Title
        """.split(
                "\n"
            )
        ), out

    def test_comment_out_line(self):
        config_lines = """
[app:main]
ckan.site_title = CKAN
        """.split(
            "\n"
        )

        out = config_tool.make_changes(
            config_lines,
            [],
            changes_builder(
                "edit", "ckan.site_title", "New Title", commented=True
            ),
        )

        assert (
            out
            == """
[app:main]
#ckan.site_title = New Title
        """.split(
                "\n"
            )
        ), out

    def test_edit_repeated_commented_line(self):
        config_lines = """
[app:main]
#ckan.site_title = CKAN1
ckan.site_title = CKAN2
ckan.site_title = CKAN3
#ckan.site_title = CKAN4
        """.split(
            "\n"
        )

        out = config_tool.make_changes(
            config_lines,
            [],
            changes_builder("edit", "ckan.site_title", "New Title"),
        )

        assert (
            out
            == """
[app:main]
ckan.site_title = New Title
#ckan.site_title = CKAN2
#ckan.site_title = CKAN3
#ckan.site_title = CKAN4
        """.split(
                "\n"
            )
        ), out


class TestParseConfig:
    def test_parse_basic(self):
        input_lines = """
[app:main]
ckan.site_title = CKAN
""".split(
            "\n"
        )

        out = config_tool.parse_config(input_lines)

        # do string comparison to avoid needing an __eq__method on Option
        assert (
            str(out) == "{"
            "'app:main-ckan.site_title': <Option [app:main] ckan.site_title = CKAN>"
            "}"
        )

    def test_parse_sections(self):
        input_lines = """
[logger]
keys = root, ckan, ckanext
level = WARNING

[app:main]
ckan.site_title = CKAN
""".split(
            "\n"
        )

        out = sorted(config_tool.parse_config(input_lines).items())

        assert (
            str(out) == "["
            "('app:main-ckan.site_title', <Option [app:main] ckan.site_title = CKAN>), "
            "('logger-keys', <Option [logger] keys = root, ckan, ckanext>), "
            "('logger-level', <Option [logger] level = WARNING>)"
            "]"
        )

    def test_parse_comment(self):
        input_lines = """
[app:main]
#ckan.site_title = CKAN
""".split(
            "\n"
        )

        out = config_tool.parse_config(input_lines)

        assert (
            str(out) == "{"
            "'app:main-ckan.site_title': <Option [app:main] #ckan.site_title = CKAN>"
            "}"
        )


class TestParseOptionString:
    def test_parse_basic(self):
        input_line = "ckan.site_title = CKAN"
        out = config_tool.parse_option_string("app:main", input_line)
        assert repr(out) == "<Option [app:main] ckan.site_title = CKAN>"
        assert str(out) == "ckan.site_title = CKAN"

    def test_parse_extra_spaces(self):
        input_line = "ckan.site_title  =  CKAN "
        out = config_tool.parse_option_string("app:main", input_line)
        assert repr(out) == "<Option [app:main] ckan.site_title  =  CKAN >"
        assert str(out) == "ckan.site_title  =  CKAN "
        assert out.key == "ckan.site_title"
        assert out.value == "CKAN"

    def test_parse_invalid_space(self):
        input_line = " ckan.site_title = CKAN"
        out = config_tool.parse_option_string("app:main", input_line)
        assert out is None
