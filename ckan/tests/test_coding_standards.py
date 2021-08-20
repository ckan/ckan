# encoding: utf-8

u"""A module for coding standards tests.

These are tests that are not functional- or unit-testing any particular piece
of CKAN code, but are checking coding standards. For example: checking that
there are no errors in the Sphinx build, that there are no PEP8 problems,
etc.

"""

import importlib
import inspect
import io
import itertools
import os
import os.path
import re
import subprocess
import sys
import pytest
import six
import pycodestyle

from six import text_type

FILESYSTEM_ENCODING = text_type(
    sys.getfilesystemencoding() or sys.getdefaultencoding()
)

HERE = os.path.abspath(os.path.dirname(__file__))

PROJECT_ROOT = os.path.normpath(os.path.join(HERE, u"..", u".."))

# Directories which are ignored when checking Python source code files
IGNORED_DIRS = [u"ckan/include", u"contrib/cookiecutter"]


def walk_python_files(ext=".py"):
    u"""
    Generator that yields all CKAN Python source files.

    Yields 2-tuples containing the filename in absolute and relative (to
    the project root) form.
    """

    def _is_dir_ignored(root, d):
        if d.startswith(u"."):
            return True
        return os.path.join(rel_root, d) in IGNORED_DIRS

    for abs_root, dirnames, filenames in os.walk(PROJECT_ROOT):
        rel_root = os.path.relpath(abs_root, PROJECT_ROOT)
        if rel_root == u".":
            rel_root = u""
        dirnames[:] = [d for d in dirnames if not _is_dir_ignored(rel_root, d)]
        for filename in filenames:
            if not filename.endswith(ext):
                continue
            abs_name = os.path.join(abs_root, filename)
            rel_name = os.path.join(rel_root, filename)
            yield abs_name, rel_name


def output_errors(filename, errors):
    out = [""]
    out.append("-" * len(filename))
    out.append(filename)
    out.append("-" * len(filename))
    for error in errors:
        out.append(error)
    return "\n".join(out)


def show_fails(msg, errors):
    if errors:
        msg = ["\n%s" % msg]
        for error in errors:
            msg.append(errors[error])
        msg.append("\n\nFailing Files:\n==============")
        msg += sorted(errors)
        raise Exception("\n".join(msg))


def show_passing(msg, errors):
    if errors:
        raise Exception("\n%s\n\n" % msg + "\n".join(sorted(errors)))


class TestBadSpellings(object):
    BAD_SPELLING_BLACKLIST_FILES = []

    # these are the bad spellings with the correct spelling
    # use LOWER case
    BAD_SPELLINGS = {
        # CS: bad_spelling ignore 2 lines
        "licence": "license",
        "organisation": "organization",
    }

    @pytest.fixture(scope="class")
    def results(self):
        fails = {}
        passes = []
        result = (fails, passes)
        blacklist = self.BAD_SPELLING_BLACKLIST_FILES
        re_bad_spelling = re.compile(
            r"(%s)" % "|".join([x for x in self.BAD_SPELLINGS]),
            flags=re.IGNORECASE,
        )
        files = itertools.chain.from_iterable(
            [
                walk_python_files(),
                walk_python_files(ext=".rst"),
            ]
        )

        for path, filename in files:
            f = open(path, "r")
            count = 1
            errors = []
            for line in cs_filter(f, "bad_spelling"):
                matches = re_bad_spelling.findall(line)
                if matches:
                    bad_words = []
                    for m in matches:
                        if m not in bad_words:
                            bad_words.append(
                                "%s use %s" % (m, self.BAD_SPELLINGS[m.lower()])
                            )
                    bad = ", ".join(bad_words)
                    errors.append("ln:%s \t%s\n<%s>" % (count, line[:-1], bad))
                count += 1
            if errors and filename not in blacklist:
                fails[filename] = output_errors(filename, errors)
            elif not errors and filename in blacklist:
                passes.append(filename)
        return result

    def test_good(self, results):
        msg = "The following files passed bad spellings rules"
        msg += "\nThey need removing from the test blacklist"
        show_passing(msg, results[1])

    def test_bad(self, results):
        msg = "The following files have bad spellings that need fixing"
        show_fails(msg, results[0])


def cs_filter(f, filter_, ignore_comment_lines=True):
    """filter the file removing comments if requested.
    looks for comments like
    # CS: <filter_> ignore
    # CS: <filter_> ignore x line
    and removes the requested number of lines.  Lines are removed by
    blanking so the line numbers reported will be correct.  This allows us
    to check files that have known violations of the test rules."""

    # this RegEx is of poor quality but works
    exp = r"^\s*#\s+CS:.*%s.*ignore\D*((\d+)\s+line)*"
    re_ignore = re.compile(exp % filter_)
    ignore = 0
    out = []
    count = 1
    for line in f:
        # ignore the line if we have been told too
        if ignore > 0:
            line = ""
            ignore -= 1
        matches = re_ignore.search(line)
        if matches:
            ignore = int(matches.group(2) or 1)
        # ignore comments out lines
        if ignore_comment_lines and line.lstrip().startswith("#"):
            line = ""
        out.append(line)
        count += 1
    return out


class TestImportStar(object):
    """Find files using from xxx import *"""

    # Import * file exceptions
    #
    # The following files contain one or more `from ... import *` lines
    # which should not be used in ckan where possible.  If the files get
    # fixed they should be removed from this list.
    #
    # import * is bad for many reasons and should be avoided.

    IMPORT_STAR_BLACKLIST_FILES = [
        "ckan/plugins/__init__.py",
    ]

    @pytest.fixture(scope="class")
    def results(self):
        blacklist = self.IMPORT_STAR_BLACKLIST_FILES
        re_import_star = re.compile(r"^\s*from\s+.*\simport\s+\*")
        fails = {}
        passes = []
        for path, filename in walk_python_files():
            f = open(path, "r")
            count = 1
            errors = []
            for line in f:
                if re_import_star.search(line):
                    errors.append(
                        "%s ln:%s import *\n\t%s" % (filename, count, line)
                    )
                count += 1
            if errors and filename not in blacklist:
                fails[filename] = output_errors(filename, errors)
            elif not errors and filename in blacklist:
                passes.append(filename)
        return fails, passes

    def test_import_good(self, results):
        msg = "The following files passed import * rules"
        msg += "\nThey need removing from the test blacklist"
        show_passing(msg, results[1])

    def test_import_bad(self, results):
        msg = (
            "The following files have import * issues that need resolving\n"
            "`from ... import *` lines which should not be used in ckan"
            " where possible."
        )
        show_fails(msg, results[0])


def test_building_the_docs():
    u"""There should be no warnings or errors when building the Sphinx docs.

    This test will also fail is build_sphinx exits with non-zero status.

    """
    try:
        output = subprocess.check_output(
            [b"python", b"setup.py", b"build_sphinx"], stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as err:
        assert (
            False
        ), u"Building the docs failed with return code: {code}".format(
            code=err.returncode
        )
    output_lines = output.split(six.b(u"\n"))

    errors = [line for line in output_lines if six.b(u"ERROR") in line]
    if errors:
        assert False, (
            u"Don't add any errors to the Sphinx build: "
            u"{errors}".format(errors=errors)
        )

    warnings = [line for line in output_lines if six.b(u"WARNING") in line]

    # Some warnings have been around for a long time and aren't easy to fix.
    # These are allowed, but no more should be added.
    allowed_warnings = [
        u"WARNING: duplicate label ckan.auth.create_user_via_web",
        u"WARNING: duplicate label ckan.auth.create_unowned_dataset",
        u"WARNING: duplicate label ckan.auth.user_create_groups",
        u"WARNING: duplicate label ckan.auth.anon_create_dataset",
        u"WARNING: duplicate label ckan.auth.user_delete_organizations",
        u"WARNING: duplicate label ckan.auth.create_user_via_api",
        u"WARNING: duplicate label ckan.auth.create_dataset_if_not_in_organization",
        u"WARNING: duplicate label ckan.auth.user_delete_groups",
        u"WARNING: duplicate label ckan.auth.user_create_organizations",
        u"WARNING: duplicate label ckan.auth.roles_that_cascade_to_sub_groups",
        u"WARNING: duplicate label ckan.auth.public_user_details",
        u"WARNING: duplicate label ckan.auth.public_activity_stream_detail",
        u"WARNING: duplicate label ckan.auth.allow_dataset_collaborators",
        u"WARNING: duplicate label ckan.auth.allow_admin_collaborators",
        u"WARNING: duplicate label ckan.auth.allow_collaborators_to_change_owner_org",
        u"WARNING: duplicate label ckan.auth.create_default_api_keys",
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
            u"Don't add any new warnings to the Sphinx build: "
            u"{warnings}".format(warnings=new_warnings)
        )


def test_source_files_specify_encoding():
    u"""
    Test that *.py files have a PEP 263 UTF-8 encoding specification.

    Empty files and files that only contain comments are ignored.
    """
    pattern = re.compile(u"#.*?coding[:=][ \\t]*utf-?8")
    decode_errors = []
    no_specification = []
    for abs_path, rel_path in walk_python_files():
        try:
            with io.open(abs_path, encoding=u"utf-8") as f:
                for line in f:
                    line = line.strip()
                    if pattern.match(line):
                        # Pattern found
                        break
                    elif line and not line.startswith(u"#"):
                        # File contains non-empty non-comment line
                        no_specification.append(rel_path)
                        break
        except UnicodeDecodeError:
            decode_errors.append(rel_path)

    msgs = []
    if no_specification:
        msgs.append(
            u"The following files are missing an encoding specification: "
            u"{}".format(no_specification)
        )
    if decode_errors:
        msgs.append(
            u"The following files are not valid UTF-8: "
            u"{}".format(decode_errors)
        )
    if msgs:
        assert False, u"\n\n".join(msgs)


class TestPep8(object):
    """Check that .py files are pep8 compliant"""

    # PEP8 File exceptions
    #
    # The following files have known PEP8 errors.  When the files get to a
    # point of not having any such errors they should be removed from this
    # list to prevent new errors being added to the file.

    PEP8_BLACKLIST_FILES = [
        "bin/running_stats.py",
        "ckan/__init__.py",
        "ckan/config/middleware.py",
        "ckan/lib/app_globals.py",
        "ckan/lib/cli.py",
        "ckan/lib/create_test_data.py",
        "ckan/lib/dictization/__init__.py",
        "ckan/lib/dictization/model_dictize.py",
        "ckan/lib/dictization/model_save.py",
        "ckan/lib/email_notifications.py",
        "ckan/lib/hash.py",
        "ckan/lib/jinja_extensions.py",
        "ckan/lib/jsonp.py",
        "ckan/lib/maintain.py",
        "ckan/lib/navl/validators.py",
        "ckan/lib/package_saver.py",
        "ckan/lib/plugins.py",
        "ckan/lib/render.py",
        "ckan/lib/search/__init__.py",
        "ckan/lib/search/index.py",
        "ckan/lib/search/query.py",
        "ckan/lib/search/sql.py",
        "ckan/logic/action/__init__.py",
        "ckan/logic/action/delete.py",
        "ckan/logic/action/get.py",
        "ckan/logic/action/update.py",
        "ckan/logic/auth/create.py",
        "ckan/logic/auth/delete.py",
        "ckan/logic/auth/get.py",
        "ckan/logic/auth/update.py",
        "ckan/logic/converters.py",
        "ckan/logic/validators.py",
        "ckan/misc.py",
        "ckan/model/__init__.py",
        "ckan/model/activity.py",
        "ckan/model/dashboard.py",
        "ckan/model/domain_object.py",
        "ckan/model/follower.py",
        "ckan/model/group.py",
        "ckan/model/group_extra.py",
        "ckan/model/license.py",
        "ckan/model/meta.py",
        "ckan/model/misc.py",
        "ckan/model/modification.py",
        "ckan/model/package.py",
        "ckan/model/package_extra.py",
        "ckan/model/package_relationship.py",
        "ckan/model/rating.py",
        "ckan/model/resource.py",
        "ckan/model/system_info.py",
        "ckan/model/tag.py",
        "ckan/model/task_status.py",
        "ckan/model/term_translation.py",
        "ckan/model/tracking.py",
        "ckan/model/user.py",
        "ckan/model/vocabulary.py",
        "ckan/authz.py",
        "ckanext/datastore/logic/action.py",
        "ckanext/datastore/tests/test_create.py",
        "ckanext/example_idatasetform/plugin.py",
        "ckanext/example_itemplatehelpers/plugin.py",
        "ckanext/multilingual/plugin.py",
        "ckanext/stats/stats.py",
        "ckanext/test_tag_vocab_plugin.py",
        "ckanext/tests/plugin.py",
        "doc/conf.py",
        "setup.py",
        "contrib/cookiecutter/ckan_extension/"
        "{{cookiecutter.project}}/setup.py",
        "contrib/cookiecutter/ckan_extension/hooks/post_gen_project.py",
        "contrib/cookiecutter/ckan_extension/"
        "{{cookiecutter.project}}/ckanext/{{cookiecutter.project_shortname}}"
        "/tests/test_plugin.py",
        "contrib/cookiecutter/ckan_extension/{{cookiecutter.project}}"
        "/ckanext/{{cookiecutter.project_shortname}}/plugin.py",
    ]

    @pytest.fixture(scope="class")
    def results(self):
        blacklist = self.PEP8_BLACKLIST_FILES
        fails = {}
        passes = []
        for path, filename in walk_python_files():
            errors = self.find_pep8_errors(filename=path)
            if errors and filename not in blacklist:
                fails[filename] = output_errors(filename, errors)
            elif not errors and filename in blacklist:
                passes.append(filename)
        return fails, passes

    def test_pep8_fails(self, results):
        msg = "The following files have pep8 issues that need resolving"
        msg += "\nThey need removing from the test blacklist"
        show_fails(msg, results[0])

    def test_pep8_pass(self, results):
        msg = "The following files passed pep8 but are blacklisted"
        show_passing(msg, results[1])

    def find_pep8_errors(self, filename=None, lines=None):
        try:
            sys.stdout = io.StringIO()
            config = {
                "ignore": [
                    # W503/W504 - breaking before/after binary operators is agreed
                    # to not be a concern and was changed to be ignored by default.
                    # However we overwrite the ignore list here, so add it back in.
                    # See: https://github.com/PyCQA/pycodestyle/issues/498
                    "W503",
                    "W504",
                ]
            }

            # Ignore long lines on test files, as the test names can get long
            # when following our test naming standards.
            if self._is_test(filename):
                config["ignore"].append("E501")

            checker = pycodestyle.Checker(
                filename=filename, lines=lines, **config
            )
            checker.check_all()
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = sys.__stdout__

        errors = []
        for line in output.split("\n"):
            parts = line.split(" ", 2)
            if len(parts) == 3:
                location, error, desc = parts
                line_no = location.split(":")[1]
                errors.append("%s ln:%s %s" % (error, line_no, desc))
        return errors

    def _is_test(self, filename):
        return bool(re.search(r"(^|\W)test_.*\.py$", filename, re.IGNORECASE))


class TestActionAuth(object):
    """These tests check the logic auth/action functions are compliant. The
    main tests are that each action has a corresponding auth function and
    that each auth function has an action.  We check the function only
    accepts (context, data_dict) as parameters."""

    ACTION_FN_SIGNATURES_BLACKLIST = ["create: activity_create"]

    ACTION_NO_AUTH_BLACKLIST = [
        "create: follow_dataset",
        "create: follow_group",
        "create: follow_user",
        "delete: unfollow_dataset",
        "delete: unfollow_group",
        "delete: unfollow_user",
        "get: am_following_dataset",
        "get: am_following_group",
        "get: am_following_user",
        "get: dataset_followee_count",
        "get: dataset_follower_count",
        "get: followee_count",
        "get: group_followee_count",
        "get: group_follower_count",
        "get: group_package_show",
        "get: member_list",
        "get: organization_follower_count",
        "get: recently_changed_packages_activity_list",
        "get: resource_search",
        "get: roles_show",
        "get: status_show",
        "get: tag_search",
        "get: term_translation_show",
        "get: user_followee_count",
        "get: user_follower_count",
        "update: task_status_update_many",
        "update: term_translation_update_many",
    ]

    AUTH_NO_ACTION_BLACKLIST = [
        "create: file_upload",
        "delete: revision_delete",
        "delete: revision_undelete",
        "get: activity_list",
        "get: group_list_available",
        "get: sysadmin",
        "get: request_reset",
        "get: user_reset",
        "update: group_change_state",
        "update: group_edit_permissions",
        "update: package_change_state",
        "update: revision_change_state",
    ]

    ACTION_NO_DOC_STR_BLACKLIST = ["get: get_site_user"]

    @pytest.fixture(scope="class")
    def results(self):
        def get_functions(module_root):
            import ckan.authz as authz

            fns = {}
            for auth_module_name in [
                "get",
                "create",
                "update",
                "delete",
                "patch",
            ]:
                module_path = "%s.%s" % (module_root, auth_module_name)
                module = importlib.import_module(module_path)
                members = authz.get_local_functions(module)
                for key, v in members:
                    name = "%s: %s" % (auth_module_name, key)
                    fns[name] = v
            return fns

        actions = get_functions("logic.action")
        auths = get_functions("logic.auth")
        return actions, auths

    def test_actions_have_auth_fn(self, results):
        actions_no_auth = set(results[0].keys()) - set(results[1].keys())
        actions_no_auth -= set(self.ACTION_NO_AUTH_BLACKLIST)
        assert (
            not actions_no_auth
        ), "These actions have no auth function\n%s" % "\n".join(
            sorted(list(actions_no_auth))
        )

    def test_actions_have_auth_fn_blacklist(self, results):
        actions_no_auth = set(results[0].keys()) & set(results[1].keys())
        actions_no_auth &= set(self.ACTION_NO_AUTH_BLACKLIST)
        assert (
            not actions_no_auth
        ), "These actions blacklisted but " + "shouldn't be \n%s" % "\n".join(
            sorted(list(actions_no_auth))
        )

    def test_auths_have_action_fn(self, results):
        auths_no_action = set(results[1].keys()) - set(results[0].keys())
        auths_no_action -= set(self.AUTH_NO_ACTION_BLACKLIST)
        assert (
            not auths_no_action
        ), "These auth functions have no action\n%s" % "\n".join(
            sorted(list(auths_no_action))
        )

    def test_auths_have_action_fn_blacklist(self, results):
        auths_no_action = set(results[1].keys()) & set(results[0].keys())
        auths_no_action &= set(self.AUTH_NO_ACTION_BLACKLIST)
        assert not auths_no_action, (
            "These auths functions blacklisted but"
            + " shouldn't be \n%s" % "\n".join(sorted(list(auths_no_action)))
        )

    def test_fn_signatures(self, results):
        errors = []
        for name, fn in six.iteritems(results[0]):
            args_info = inspect.getargspec(fn)
            if (
                args_info.args != ["context", "data_dict"]
                or args_info.varargs is not None
                or args_info.keywords is not None
            ):
                if name not in self.ACTION_FN_SIGNATURES_BLACKLIST:
                    errors.append(name)
        assert not errors, (
            "These action functions have the wrong function"
            + " signature, should be (context, data_dict)\n%s"
            % "\n".join(sorted(errors))
        )

    def test_fn_docstrings(self, results):
        errors = []
        for name, fn in six.iteritems(results[0]):
            if not getattr(fn, "__doc__", None):
                if name not in self.ACTION_NO_DOC_STR_BLACKLIST:
                    errors.append(name)
        assert (
            not errors
        ), "These action functions need docstrings\n%s" % "\n".join(
            sorted(errors)
        )


class TestBadExceptions(object):
    """Look for a common coding problem in ckan Exception(_'...')"""

    # Exceptions should not on the whole be translated as they are for
    # programmers to read in trace backs or log files.  However some like
    # Invalid used in validation functions do get passed back up to the user
    # and so should be translated.

    NASTY_EXCEPTION_BLACKLIST_FILES = [
        "ckan/lib/mailer.py",
        "ckan/logic/action/create.py",
        "ckan/logic/action/delete.py",
        "ckan/logic/action/get.py",
        "ckan/logic/action/update.py",
        "ckan/logic/auth/create.py",
        "ckan/logic/auth/delete.py",
        "ckan/logic/auth/get.py",
        "ckan/authz.py",
        "ckanext/datastore/logic/action.py",
    ]

    @pytest.fixture(scope="class")
    def results(self):
        blacklist = self.NASTY_EXCEPTION_BLACKLIST_FILES
        re_nasty_exception = re.compile(r"""raise\W+(?![^I]*Invalid\().*_\(""")
        fails = {}
        passes = []
        for path, filename in walk_python_files():
            f = open(path, "r")
            count = 1
            errors = []
            for line in f:
                if re_nasty_exception.search(line):
                    errors.append("ln:%s \t%s" % (count, line[:-1]))
                count += 1
            if errors and filename not in blacklist:
                fails[filename] = output_errors(filename, errors)
            elif not errors and filename in blacklist:
                passes.append(filename)
        return fails, passes

    def test_good(self, results):
        msg = "The following files passed nasty exceptions rules"
        msg += "\nThey need removing from the test blacklist"
        show_passing(msg, results[1])

    def test_bad(self, results):
        msg = (
            "The following files have nasty exception issues that need"
            " resolving\nWe should not be translating exceptions in most"
            " situations.  We need to when the exception message is passed"
            " to the front end for example validation"
        )
        show_fails(msg, results[0])
