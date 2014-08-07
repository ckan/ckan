'''A module for coding standards tests.

These are tests that are not functional- or unit-testing any particular piece
of CKAN code, but are checking coding standards. For example: checking that
there are no errors in the Sphinx build, that there are no PEP8 problems,
etc.

'''
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
