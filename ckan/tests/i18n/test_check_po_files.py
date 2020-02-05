# encoding: utf-8

from ckan.cli.translation import (
    check_po_file,
    simple_conv_specs,
    mapping_keys,
    replacement_fields,
)

PO_OK = """
#: ckan/lib/formatters.py:57
msgid "November"
msgstr "Noiembrie"

#: ckan/lib/formatters.py:61
msgid "December"
msgstr "Decembrie"
"""

PO_WRONG = """
#: ckan/templates/snippets/search_result_text.html:15
msgid "{number} dataset found for {query}"
msgstr "צביר נתונים אחד נמצא עבור {query}"
"""

PO_PLURALS_OK = """
#: ckan/lib/formatters.py:114
msgid "{hours} hour ago"
msgid_plural "{hours} hours ago"
msgstr[0] "Fa {hours} hora"
msgstr[1] "Fa {hours} hores"
"""

PO_WRONG_PLURALS = """
#: ckan/lib/formatters.py:114
msgid "{hours} hour ago"
msgid_plural "{hours} hours ago"
msgstr[0] "o oră în urmă"
msgstr[1] "cîteva ore în urmă"
msgstr[2] "{hours} ore în urmă"
"""


def test_basic():
    errors = check_po_file(PO_OK)
    assert errors == []


def test_wrong():
    errors = check_po_file(PO_WRONG)
    assert len(errors) == 1
    assert errors[0][0] == "{number} dataset found for {query}"


def test_plurals_ok():
    errors = check_po_file(PO_PLURALS_OK)
    assert errors == []


def test_wrong_plurals():
    errors = check_po_file(PO_WRONG_PLURALS)
    assert len(errors) == 2

    for error in errors:
        assert error[0] in ("{hours} hour ago", "{hours} hours ago")


def test_simple_conv_specs():
    assert simple_conv_specs("Authorization function not found: %s") == (
        ["%s"]
    )
    assert simple_conv_specs("Problem purging revision %s: %s") == (
        ["%s", "%s"]
    )
    assert simple_conv_specs(
        "Cannot create new entity of this type: %s %s"
    ) == ["%s", "%s"]
    assert simple_conv_specs("Could not read parameters: %r") == ["%r"]
    assert simple_conv_specs("User %r not authorized to edit %r") == (
        ["%r", "%r"]
    )
    assert simple_conv_specs(
        'Please <a href="%s">update your profile</a> and add your email '
        "address and your full name. "
        "%s uses your email address if you need to reset your password."
    ) == (["%s", "%s"])
    assert simple_conv_specs("You can use %sMarkdown formatting%s here.") == [
        "%s",
        "%s",
    ]
    assert simple_conv_specs(
        "Name must be a maximum of %i characters long"
    ) == ["%i"]
    assert simple_conv_specs("Blah blah %s blah %(key)s blah %i") == (
        ["%s", "%i"]
    )


def test_replacement_fields():
    assert replacement_fields(
        "{actor} added the tag {object} to the dataset {target}"
    ) == (["{actor}", "{object}", "{target}"])
    assert replacement_fields("{actor} updated their profile") == ["{actor}"]


def test_mapping_keys():
    assert mapping_keys(
        "You have requested your password on %(site_title)s to be reset.\n"
        "\n"
        "Please click the following link to confirm this request:\n"
        "\n"
        "   %(reset_link)s\n"
    ) == ["%(reset_link)s", "%(site_title)s"]
    assert mapping_keys("The input field %(name)s was not expected.") == [
        "%(name)s"
    ]
    assert mapping_keys(
        '[1:You searched for "%(query)s". ]%(number_of_results)s '
        "datasets found."
    ) == ["%(number_of_results)s", "%(query)s"]
    assert mapping_keys("Blah blah %s blah %(key)s blah %i") == (["%(key)s"])
