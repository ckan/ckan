'''A module for coding standards tests.

These are tests that are not functional- or unit-testing any particular piece
of CKAN code, but are checking coding standards. For example: checking that
there are no errors in the Sphinx build, that there are no PEP8 problems,
etc.

'''
import subprocess


# We implement our own check_output() function because
# subprocess.check_output() isn't in Python 2.6.
# This code is copy-pasted from Python 2.7:
# http://hg.python.org/cpython/file/d37f963394aa/Lib/subprocess.py#l544
def check_output(*popenargs, **kwargs):
    r"""Run command with arguments and return its output as a byte string.

    If the exit code was non-zero it raises a CalledProcessError.  The
    CalledProcessError object will have the return code in the returncode
    attribute and output in the output attribute.

    The arguments are the same as for the Popen constructor.  Example:

    >>> check_output(["ls", "-l", "/dev/null"])
    'crw-rw-rw- 1 root root 1, 3 Oct 18  2007 /dev/null\n'

    The stdout argument is not allowed as it is used internally.
    To capture standard error in the result, use stderr=STDOUT.

    >>> check_output(["/bin/sh", "-c",
    ...               "ls -l non_existent_file ; exit 0"],
    ...              stderr=STDOUT)
    'ls: non_existent_file: No such file or directory\n'
    """
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise subprocess.CalledProcessError(retcode, cmd, output=output)
    return output


def test_building_the_docs():
    '''There should be no warnings or errors when building the Sphinx docs.

    This test unfortunately does take quite a long time to run - rebuilding the
    docs from scratch just takes a long time.

    This test will also fail is build_sphinx exits with non-zero status
    (because subprocess.check_output() will raise an exception).

    '''
    try:
        output = check_output(
            ['python', 'setup.py', 'build_sphinx', '--all-files', '--fresh-env'],
            stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as err:
        assert False, "Building the docs failed: {err}".format(
            err=err.message + ' ' + err.output)
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
    warnings_to_remove = []
    for allowed_warning in allowed_warnings:
        for warning in warnings:
            if allowed_warning in warning:
                warnings_to_remove.append(warning)
    new_warnings = [warning for warning in warnings
                    if warning not in warnings_to_remove]

    if new_warnings:
        assert False, ("Don't add any new warnings to the Sphinx build: "
                       "{warnings}".format(warnings=new_warnings))
