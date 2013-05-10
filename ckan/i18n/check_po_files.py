#!/usr/bin/env python
'''Script for checking for common translation mistakes in po files, see:

    paster check-po-files --help

for usage.

Requires polib <http://pypi.python.org/pypi/polib>:

    pip install polib

'''
import re
import paste.script.command

def simple_conv_specs(s):
    '''Return the simple Python string conversion specifiers in the string s.

    e.g. ['%s', '%i']

    See http://docs.python.org/library/stdtypes.html#string-formatting

    '''
    simple_conv_specs_re = re.compile('\%\w')
    return simple_conv_specs_re.findall(s)

def test_simple_conv_specs():
    assert simple_conv_specs("Authorization function not found: %s") == (
            ['%s'])
    assert simple_conv_specs("Problem purging revision %s: %s") == (
            ['%s', '%s'])
    assert simple_conv_specs(
            "Cannot create new entity of this type: %s %s") == ['%s', '%s']
    assert simple_conv_specs("Could not read parameters: %r") == ['%r']
    assert simple_conv_specs("User %r not authorized to edit %r") == (
            ['%r', '%r'])
    assert simple_conv_specs(
        "Please <a href=\"%s\">update your profile</a> and add your email "
        "address and your full name. "
        "%s uses your email address if you need to reset your password.") == (
                ['%s', '%s'])
    assert simple_conv_specs(
            "You can use %sMarkdown formatting%s here.") == ['%s', '%s']
    assert simple_conv_specs(
            "Name must be a maximum of %i characters long") == ['%i']
    assert simple_conv_specs("Blah blah %s blah %(key)s blah %i") == (
        ['%s', '%i'])

def mapping_keys(s):
    '''Return a sorted list of the mapping keys in the string s.

    e.g. ['%(name)s', '%(age)i']

    See http://docs.python.org/library/stdtypes.html#string-formatting

    '''
    mapping_keys_re = re.compile('\%\([^\)]*\)\w')
    return sorted(mapping_keys_re.findall(s))

def test_mapping_keys():
    assert mapping_keys(
            "You have requested your password on %(site_title)s to be reset.\n"
            "\n"
            "Please click the following link to confirm this request:\n"
            "\n"
            "   %(reset_link)s\n") == ['%(reset_link)s', '%(site_title)s']
    assert mapping_keys(
            "The input field %(name)s was not expected.") == ['%(name)s']
    assert mapping_keys(
            "[1:You searched for \"%(query)s\". ]%(number_of_results)s "
            "datasets found.") == ['%(number_of_results)s', '%(query)s']
    assert mapping_keys("Blah blah %s blah %(key)s blah %i") == (
        ['%(key)s']), mapping_keys("Blah blah %s blah %(key)s blah %i")

def replacement_fields(s):
    '''Return a sorted list of the Python replacement fields in the string s.

    e.g. ['{}', '{2}', '{object}', '{target}']

    See http://docs.python.org/library/string.html#formatstrings

    '''
    repl_fields_re = re.compile('\{[^\}]*\}')
    return sorted(repl_fields_re.findall(s))

def test_replacement_fields():
    assert replacement_fields(
            "{actor} added the tag {object} to the dataset {target}") == (
                    ['{actor}', '{object}', '{target}'])
    assert replacement_fields("{actor} updated their profile") == ['{actor}']

class CheckPoFiles(paste.script.command.Command):

    usage = "[FILE] ..."
    group_name = 'ckan'
    summary = 'Check po files for common mistakes'
    parser = paste.script.command.Command.standard_parser(verbose=True)

    def command(self):
        import polib

        test_simple_conv_specs()
        test_mapping_keys()
        test_replacement_fields()
        for path in self.args:
            print u'Checking file {}'.format(path)
            po = polib.pofile(path)
            for entry in po.translated_entries():
                if not entry.msgstr:
                    continue
                for function in (simple_conv_specs, mapping_keys,
                        replacement_fields):
                    if not function(entry.msgid) == function(entry.msgstr):
                        print "    Format specifiers don't match:"
                        print u'    {0} -> {1}'.format(entry.msgid, entry.msgstr)
