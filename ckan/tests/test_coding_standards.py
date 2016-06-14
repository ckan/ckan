# encoding: utf-8

'''A module for coding standards tests.

These are tests that are not functional- or unit-testing any particular piece
of CKAN code, but are checking coding standards. For example: checking that
there are no errors in the Sphinx build, that there are no PEP8 problems,
etc.

'''

import io
import os
import os.path
import re
import subprocess

import ckan.lib.util as util


def test_building_the_docs():
    '''There should be no warnings or errors when building the Sphinx docs.

    This test unfortunately does take quite a long time to run - rebuilding the
    docs from scratch just takes a long time.

    This test will also fail is build_sphinx exits with non-zero status.

    '''
    try:
        output = util.check_output(
            ['python', 'setup.py', 'build_sphinx', '--all-files', '--fresh-env'],
            stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as err:
        assert False, (
            "Building the docs failed with return code: {code}".format(
                code=err.returncode))
    output_lines = output.split('\n')

    errors = [line for line in output_lines if 'ERROR' in line]
    if errors:
        assert False, ("Don't add any errors to the Sphinx build: "
                       "{errors}".format(errors=errors))

    warnings = [line for line in output_lines if 'WARNING' in line]

    # Some warnings have been around for a long time and aren't easy to fix.
    # These are allowed, but no more should be added.
    allowed_warnings = [
        'WARNING: duplicate label ckan.auth.create_user_via_web',
        'WARNING: duplicate label ckan.auth.create_unowned_dataset',
        'WARNING: duplicate label ckan.auth.user_create_groups',
        'WARNING: duplicate label ckan.auth.anon_create_dataset',
        'WARNING: duplicate label ckan.auth.user_delete_organizations',
        'WARNING: duplicate label ckan.auth.create_user_via_api',
        'WARNING: duplicate label ckan.auth.create_dataset_if_not_in_organization',
        'WARNING: duplicate label ckan.auth.user_delete_groups',
        'WARNING: duplicate label ckan.auth.user_create_organizations',
        'WARNING: duplicate label ckan.auth.roles_that_cascade_to_sub_groups'
    ]

    # Remove the allowed warnings from the list of collected warnings.
    # Be sure to only remove one warning for each allowed warning.
    warnings_to_remove = []
    for allowed_warning in allowed_warnings:
        for warning in warnings:
            if allowed_warning in warning:
                warnings_to_remove.append(warning)
                break
    new_warnings = [warning for warning in warnings
                    if warning not in warnings_to_remove]

    if new_warnings:
        assert False, ("Don't add any new warnings to the Sphinx build: "
                       "{warnings}".format(warnings=new_warnings))


def test_source_files_specify_encoding():
    '''
    Test that *.py files have a PEP 263 UTF-8 encoding specification.

    Empty files and files that only contain comments are ignored.
    '''
    root_dir = os.path.join(os.path.dirname(__file__), '..', '..')
    test_dirs = ['ckan', 'ckanext']
    ignored_dirs = ['ckan/include']
    pattern = re.compile(r'#.*?coding[:=][ \t]*utf-?8')
    decode_errors = []
    no_specification = []

    def check_file(filename):
        try:
            with io.open(filename, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if pattern.match(line):
                        # Pattern found
                        return
                    elif line and not line.startswith('#'):
                        # File contains non-empty non-comment line
                        no_specification.append(os.path.relpath(filename,
                                                root_dir))
                        return
        except UnicodeDecodeError:
            decode_errors.append(filename)

    for test_dir in test_dirs:
        base_dir = os.path.join(root_dir, test_dir)
        for root, dirnames, filenames in os.walk(base_dir):
            dirnames[:] = [d for d in dirnames if not
                           os.path.relpath(os.path.join(root, d), root_dir)
                           in ignored_dirs]
            for filename in filenames:
                if not filename.endswith('.py'):
                    continue
                check_file(os.path.join(root, filename))

    msgs = []
    if no_specification:
        msgs.append('The following files are missing an encoding '
                    + 'specification: {}'.format(no_specification))
    if decode_errors:
        msgs.append('The following files are not valid UTF-8: {}'.format(
                    decode_errors))
    if msgs:
        assert False, '\n\n'.join(msgs)
