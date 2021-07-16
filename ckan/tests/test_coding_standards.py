# encoding: utf-8

"""A module for coding standards tests.

These are tests that are not functional- or unit-testing any particular piece
of CKAN code, but are checking coding standards. For example: checking that
there are no errors in the Sphinx build, that there are no PEP8 problems,
etc.

"""

import ast
import io
import os
import os.path
import re
import subprocess
import sys
import six
import pytest

from six import text_type
from six.moves import xrange

FILESYSTEM_ENCODING = text_type(
    sys.getfilesystemencoding() or sys.getdefaultencoding()
)

HERE = os.path.abspath(os.path.dirname(__file__))

PROJECT_ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))

# Directories which are ignored when checking Python source code files
IGNORED_DIRS = ["ckan/include", "contrib/cookiecutter"]


def walk_python_files():
    """
    Generator that yields all CKAN Python source files.

    Yields 2-tuples containing the filename in absolute and relative (to
    the project root) form.
    """

    def _is_dir_ignored(root, d):
        if d.startswith("."):
            return True
        return os.path.join(rel_root, d) in IGNORED_DIRS

    for abs_root, dirnames, filenames in os.walk(PROJECT_ROOT):
        rel_root = os.path.relpath(abs_root, PROJECT_ROOT)
        if rel_root == ".":
            rel_root = ""
        dirnames[:] = [d for d in dirnames if not _is_dir_ignored(rel_root, d)]
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            abs_name = os.path.join(abs_root, filename)
            rel_name = os.path.join(rel_root, filename)
            yield abs_name, rel_name


def test_building_the_docs():
    """There should be no warnings or errors when building the Sphinx docs.

    This test will also fail is build_sphinx exits with non-zero status.

    """
    try:
        output = subprocess.check_output(
            [b"python", b"setup.py", b"build_sphinx"], stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as err:
        assert (
            False
        ), "Building the docs failed with return code: {code}".format(
            code=err.returncode
        )
    output_lines = output.split(six.b("\n"))

    errors = [line for line in output_lines if six.b("ERROR") in line]
    if errors:
        assert False, (
            "Don't add any errors to the Sphinx build: "
            "{errors}".format(errors=errors)
        )

    warnings = [line for line in output_lines if six.b("WARNING") in line]

    # Some warnings have been around for a long time and aren't easy to fix.
    # These are allowed, but no more should be added.
    allowed_warnings = [
        "WARNING: duplicate label ckan.auth.create_user_via_web",
        "WARNING: duplicate label ckan.auth.create_unowned_dataset",
        "WARNING: duplicate label ckan.auth.user_create_groups",
        "WARNING: duplicate label ckan.auth.anon_create_dataset",
        "WARNING: duplicate label ckan.auth.user_delete_organizations",
        "WARNING: duplicate label ckan.auth.create_user_via_api",
        "WARNING: duplicate label ckan.auth.create_dataset_if_not_in_organization",
        "WARNING: duplicate label ckan.auth.user_delete_groups",
        "WARNING: duplicate label ckan.auth.user_create_organizations",
        "WARNING: duplicate label ckan.auth.roles_that_cascade_to_sub_groups",
        "WARNING: duplicate label ckan.auth.public_user_details",
        "WARNING: duplicate label ckan.auth.public_activity_stream_detail",
        "WARNING: duplicate label ckan.auth.allow_dataset_collaborators",
        "WARNING: duplicate label ckan.auth.allow_admin_collaborators",
        "WARNING: duplicate label ckan.auth.allow_collaborators_to_change_owner_org",
        "WARNING: duplicate label ckan.auth.create_default_api_keys",
    ]

    # Remove the allowed warnings from the list of collected warnings.
    # Be sure to only remove one warning for each allowed warning.
    warnings_to_remove = []
    for allowed_warning in allowed_warnings:
        for warning in warnings:
            if six.b(allowed_warning) in warning:
                warnings_to_remove.append(warning)
                break
    new_warnings = [
        warning for warning in warnings if warning not in warnings_to_remove
    ]

    if new_warnings:
        assert False, (
            "Don't add any new warnings to the Sphinx build: "
            "{warnings}".format(warnings=new_warnings)
        )


def test_source_files_specify_encoding():
    """
    Test that *.py files have a PEP 263 UTF-8 encoding specification.

    Empty files and files that only contain comments are ignored.
    """
    pattern = re.compile("#.*?coding[:=][ \\t]*utf-?8")
    decode_errors = []
    no_specification = []
    for abs_path, rel_path in walk_python_files():
        try:
            with io.open(abs_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if pattern.match(line):
                        # Pattern found
                        break
                    elif line and not line.startswith("#"):
                        # File contains non-empty non-comment line
                        no_specification.append(rel_path)
                        break
        except UnicodeDecodeError:
            decode_errors.append(rel_path)

    msgs = []
    if no_specification:
        msgs.append(
            "The following files are missing an encoding specification: "
            "{}".format(no_specification)
        )
    if decode_errors:
        msgs.append(
            "The following files are not valid UTF-8: "
            "{}".format(decode_errors)
        )
    if msgs:
        assert False, "\n\n".join(msgs)


def renumerate(it):
    """
    Reverse enumerate.

    Yields tuples ``(i, x)`` where ``x`` are the items of ``it`` in
    reverse order and ``i`` is the corresponding (decreasing) index.
    ``it`` must support ``len``.
    """
    return zip(xrange(len(it) - 1, -1, -1), reversed(it))
