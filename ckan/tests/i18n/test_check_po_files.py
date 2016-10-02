# encoding: utf-8

import nose

from ckan.i18n.check_po_files import (check_po_file,
                                      simple_conv_specs,
                                      mapping_keys,
                                      replacement_fields)

eq_ = nose.tools.eq_


PO_OK = '''
#: ckan/lib/formatters.py:57
msgid "November"
msgstr "Noiembrie"

#: ckan/lib/formatters.py:61
msgid "December"
msgstr "Decembrie"
'''

PO_WRONG = '''
#: ckan/templates/snippets/search_result_text.html:15
msgid "{number} dataset found for {query}"
msgstr "צביר נתונים אחד נמצא עבור {query}"
'''

PO_PLURALS_OK = '''
#: ckan/lib/formatters.py:114
msgid "{hours} hour ago"
msgid_plural "{hours} hours ago"
msgstr[0] "Fa {hours} hora"
msgstr[1] "Fa {hours} hores"
'''

PO_WRONG_PLURALS = '''
#: ckan/lib/formatters.py:114
msgid "{hours} hour ago"
msgid_plural "{hours} hours ago"
msgstr[0] "o oră în urmă"
msgstr[1] "cîteva ore în urmă"
msgstr[2] "{hours} ore în urmă"
'''


class TestCheckPoFiles(object):

    def test_basic(self):

        errors = check_po_file(PO_OK)

        eq_(errors, [])

    def test_wrong(self):

        errors = check_po_file(PO_WRONG)

        eq_(len(errors), 1)

        eq_(errors[0][0], '{number} dataset found for {query}')

    def test_plurals_ok(self):

        errors = check_po_file(PO_PLURALS_OK)

        eq_(errors, [])

    def test_wrong_plurals(self):

        errors = check_po_file(PO_WRONG_PLURALS)

        eq_(len(errors), 2)

        for error in errors:
            assert error[0] in ('{hours} hour ago', '{hours} hours ago')


class TestValidators(object):

    def test_simple_conv_specs(self):
        eq_(simple_conv_specs("Authorization function not found: %s"),
            (['%s']))
        eq_(simple_conv_specs("Problem purging revision %s: %s"),
            (['%s', '%s']))
        eq_(simple_conv_specs("Cannot create new entity of this type: %s %s"),
            ['%s', '%s'])
        eq_(simple_conv_specs("Could not read parameters: %r"), ['%r'])
        eq_(simple_conv_specs("User %r not authorized to edit %r"),
            (['%r', '%r']))
        eq_(simple_conv_specs(
            "Please <a href=\"%s\">update your profile</a> and add your email "
            "address and your full name. "
            "%s uses your email address if you need to reset your password."),
            (['%s', '%s']))
        eq_(simple_conv_specs("You can use %sMarkdown formatting%s here."),
            ['%s', '%s'])
        eq_(simple_conv_specs("Name must be a maximum of %i characters long"),
            ['%i'])
        eq_(simple_conv_specs("Blah blah %s blah %(key)s blah %i"),
            (['%s', '%i']))

    def test_replacement_fields(self):
        eq_(replacement_fields(
            "{actor} added the tag {object} to the dataset {target}"),
            (['{actor}', '{object}', '{target}']))
        eq_(replacement_fields("{actor} updated their profile"), ['{actor}'])

    def test_mapping_keys(self):
        eq_(mapping_keys(
            "You have requested your password on %(site_title)s to be reset.\n"
            "\n"
            "Please click the following link to confirm this request:\n"
            "\n"
            "   %(reset_link)s\n"),
            ['%(reset_link)s', '%(site_title)s'])
        eq_(mapping_keys(
            "The input field %(name)s was not expected."),
            ['%(name)s'])
        eq_(mapping_keys(
            "[1:You searched for \"%(query)s\". ]%(number_of_results)s "
            "datasets found."),
            ['%(number_of_results)s', '%(query)s'])
        eq_(mapping_keys("Blah blah %s blah %(key)s blah %i"),
            (['%(key)s']), mapping_keys("Blah blah %s blah %(key)s blah %i"))
