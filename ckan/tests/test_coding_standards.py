# encoding: utf-8

u"""A module for coding standards tests.

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

if six.PY2:
    HERE = os.path.abspath(os.path.dirname(__file__.decode(FILESYSTEM_ENCODING)))
else:
    HERE = os.path.abspath(os.path.dirname(__file__))

PROJECT_ROOT = os.path.normpath(os.path.join(HERE, u"..", u".."))

# Directories which are ignored when checking Python source code files
IGNORED_DIRS = [u"ckan/include", u"contrib/cookiecutter"]


def walk_python_files():
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
            if not filename.endswith(u".py"):
                continue
            abs_name = os.path.join(abs_root, filename)
            rel_name = os.path.join(rel_root, filename)
            yield abs_name, rel_name


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


def renumerate(it):
    u"""
    Reverse enumerate.

    Yields tuples ``(i, x)`` where ``x`` are the items of ``it`` in
    reverse order and ``i`` is the corresponding (decreasing) index.
    ``it`` must support ``len``.
    """
    return zip(xrange(len(it) - 1, -1, -1), reversed(it))


def find_unprefixed_string_literals(filename):
    u"""
    Find unprefixed string literals in a Python source file.

    Returns a list of ``(line_number, column)`` tuples (both 1-based) of
    positions where string literals without a ``u`` or ``b`` prefix
    start.

    Note: Due to limitations in Python's ``ast`` module this does not
    check the rear parts of auto-concatenated string literals
    (``'foo' 'bar'``).
    """
    with io.open(filename, encoding=u"utf-8") as f:
        lines = f.readlines()
    # In some versions of Python, the ast module cannot deal with
    # encoding declarations (http://bugs.python.org/issue22221). We
    # therefore replace all comment lines at the beginning of the file
    # with empty lines (to keep the line numbers correct).
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith(u"#"):
            lines[i] = u"\n"
        elif line:
            break
    root = ast.parse(u"".join(lines), filename.encode(FILESYSTEM_ENCODING))
    problems = []
    for node in ast.walk(root):
        if isinstance(node, ast.Str):
            lineno = node.lineno - 1
            col_offset = node.col_offset
            if col_offset == -1:
                # `lineno` and `col_offset` are broken for literals that span
                # multiple lines: For these, `lineno` contains the line of the
                # *closing* quotes, and `col_offset` is always -1, see
                # https://bugs.python.org/issue16806.  We therefore have to
                # find the start of the literal manually, which is difficult
                # since '''-literals can contain """ and vice versa. The
                # following code assumes that no ''' or """ literal begins on
                # the same line where a multi-line literal ends.
                last_line = lines[lineno]
                if last_line.rfind(u'"""') > last_line.rfind(u"'''"):
                    quotes = u'"""'
                else:
                    quotes = u"'''"
                for lineno, line in renumerate(lines[:lineno]):
                    try:
                        i = line.rindex(quotes)
                        if (i > 1) and (line[i - 2: i].lower() == u"ur"):
                            col_offset = i - 2
                        elif (i > 0) and (line[i - 1].lower() in u"rbu"):
                            col_offset = i - 1
                        else:
                            col_offset = 0
                        break
                    except ValueError:
                        continue
            leading = lines[lineno][col_offset - 1: col_offset + 1]
            if leading[:-1] == u"[":  # data['id'] is unambiguous, ignore these
                continue
            if leading[-1:] not in u"ub":  # Don't allow capital U and B either
                problems.append((lineno + 1, col_offset + 1))
    return sorted(problems)


# List of files white-listed for the string literal prefix test. Files on the
# list are expected to be fixed over time and removed from the list. DO NOT ADD
# NEW FILES TO THE LIST.
_STRING_LITERALS_WHITELIST = [
    u"bin/running_stats.py",
    u"ckan/__init__.py",
    u"ckan/authz.py",
    u"ckan/cli/translation.py",
    u"ckan/config/environment.py",
    u"ckan/config/install.py",
    u"ckan/config/middleware/__init__.py",
    u"ckan/config/middleware/common_middleware.py",
    u"ckan/config/middleware/flask_app.py",
    u"ckan/config/middleware/pylons_app.py",
    u"ckan/config/routing.py",
    u"ckan/controllers/admin.py",
    u"ckan/controllers/api.py",
    u"ckan/controllers/error.py",
    u"ckan/controllers/feed.py",
    u"ckan/controllers/group.py",
    u"ckan/controllers/home.py",
    u"ckan/controllers/organization.py",
    u"ckan/controllers/package.py",
    u"ckan/controllers/partyline.py",
    u"ckan/controllers/revision.py",
    u"ckan/controllers/tag.py",
    u"ckan/controllers/user.py",
    u"ckan/controllers/util.py",
    u"ckan/exceptions.py",
    u"ckan/i18n/check_po_files.py",
    u"ckan/lib/activity_streams.py",
    u"ckan/lib/activity_streams_session_extension.py",
    u"ckan/lib/app_globals.py",
    u"ckan/lib/authenticator.py",
    u"ckan/lib/base.py",
    u"ckan/lib/captcha.py",
    u"ckan/lib/cli.py",
    u"ckan/lib/config_tool.py",
    u"ckan/lib/create_test_data.py",
    u"ckan/lib/datapreview.py",
    u"ckan/lib/dictization/__init__.py",
    u"ckan/lib/dictization/model_dictize.py",
    u"ckan/lib/dictization/model_save.py",
    u"ckan/lib/email_notifications.py",
    u"ckan/lib/extract.py",
    u"ckan/lib/fanstatic_extensions.py",
    u"ckan/lib/fanstatic_resources.py",
    u"ckan/lib/formatters.py",
    u"ckan/lib/hash.py",
    u"ckan/lib/helpers.py",
    u"ckan/lib/i18n.py",
    u"ckan/lib/jinja_extensions.py",
    u"ckan/lib/jsonp.py",
    u"ckan/lib/mailer.py",
    u"ckan/lib/maintain.py",
    u"ckan/lib/munge.py",
    u"ckan/lib/navl/__init__.py",
    u"ckan/lib/navl/dictization_functions.py",
    u"ckan/lib/navl/validators.py",
    u"ckan/lib/plugins.py",
    u"ckan/lib/render.py",
    u"ckan/lib/search/__init__.py",
    u"ckan/lib/search/common.py",
    u"ckan/lib/search/index.py",
    u"ckan/lib/search/query.py",
    u"ckan/lib/search/sql.py",
    u"ckan/lib/repoze_plugins/auth_tkt.py",
    u"ckan/lib/uploader.py",
    u"ckan/logic/__init__.py",
    u"ckan/logic/action/__init__.py",
    u"ckan/logic/action/create.py",
    u"ckan/logic/action/delete.py",
    u"ckan/logic/action/get.py",
    u"ckan/logic/action/patch.py",
    u"ckan/logic/action/update.py",
    u"ckan/logic/auth/__init__.py",
    u"ckan/logic/auth/create.py",
    u"ckan/logic/auth/delete.py",
    u"ckan/logic/auth/get.py",
    u"ckan/logic/auth/patch.py",
    u"ckan/logic/auth/update.py",
    u"ckan/logic/converters.py",
    u"ckan/logic/schema.py",
    u"ckan/logic/validators.py",
    u"ckan/migration/manage.py",
    u"ckan/migration/versions/001_103676e0a497_create_existing_tables.py",
    u"ckan/migration/versions/002_86fdd8c54775_add_author_and_maintainer.py",
    u"ckan/migration/versions/003_f22b4f5241a5_add_user_object.py",
    u"ckan/migration/versions/004_f92ee205e46d_add_group_object.py",
    u"ckan/migration/versions/005_12c2232c15f5_add_authorization_tables.py",
    u"ckan/migration/versions/006_c83955e7acb6_add_ratings.py",
    u"ckan/migration/versions/007_1928d4af1cda_add_system_roles.py",
    u"ckan/migration/versions/008_e8283ffb257e_update_vdm_ids.py",
    u"ckan/migration/versions/009_b739a48de5c4_add_creation_timestamps.py",
    u"ckan/migration/versions/010_a6f13bf14d0c_add_user_about.py",
    u"ckan/migration/versions/011_866f6370b4ac_add_package_search_vector.py",
    u"ckan/migration/versions/012_e5ca33a5d445_add_resources.py",
    u"ckan/migration/versions/013_8a3a5af39797_add_hash.py",
    u"ckan/migration/versions/014_93519b684820_hash_2.py",
    u"ckan/migration/versions/015_6d8ffebcaf54_remove_state_object.py",
    u"ckan/migration/versions/016_37ada738328e_uuids_everywhere.py",
    u"ckan/migration/versions/017_1250b2ff3e36_add_pkg_relationships.py",
    u"ckan/migration/versions/018_05a0778051ca_adjust_licenses.py",
    u"ckan/migration/versions/019_b2eb6f34a638_pkg_relationships_state.py",
    u"ckan/migration/versions/020_69a0b0efc609_add_changeset.py",
    u"ckan/migration/versions/021_765143af2ba3_postgresql_upgrade_sql.py",
    u"ckan/migration/versions/022_7b324ca6c0dc_add_group_extras.py",
    u"ckan/migration/versions/023_87fdd05f0744_add_harvesting.py",
    u"ckan/migration/versions/024_12981fe12484_add_harvested_document.py",
    u"ckan/migration/versions/025_b581622ad327_add_authorization_groups.py",
    u"ckan/migration/versions/026_3615b25af443_authorization_group_user_pk.py",
    u"ckan/migration/versions/027_11e5745c6fc9_adjust_harvester.py",
    u"ckan/migration/versions/028_cdd68fe9ba21_drop_harvest_source_status.py",
    u"ckan/migration/versions/029_1bfdf4240915_version_groups.py",
    u"ckan/migration/versions/030_b16cbf164c8a_additional_user_attributes.py",
    u"ckan/migration/versions/031_1b05245167d6_move_openid_to_new_field.py",
    u"ckan/migration/versions/032_d89e0731422d_add_extra_info_field_to_resources.py",
    u"ckan/migration/versions/033_6da92ef2df15_auth_group_user_id_add_conditional.py",
    u"ckan/migration/versions/034_6c600693af5b_resource_group_table.py",
    u"ckan/migration/versions/035_81148ccebd6c_harvesting_doc_versioning.py",
    u"ckan/migration/versions/036_ecaa8b38782f_lockdown_roles.py",
    u"ckan/migration/versions/037_edcf3b8c3c1b_role_anon_editor.py",
    u"ckan/migration/versions/038_fd6622e3d964_delete_migration_tables.py",
    u"ckan/migration/versions/039_cca459c76d45_add_expired_id_and_dates.py",
    u"ckan/migration/versions/040_500a08f4818e_reset_key_on_user.py",
    u"ckan/migration/versions/041_6817d4e3bdc3_resource_new_fields.py",
    u"ckan/migration/versions/042_da65e2877034_user_revision_indexes.py",
    u"ckan/migration/versions/043_bd38cd6502b2_drop_postgres_search.py",
    u"ckan/migration/versions/044_4190eeeb8d73_add_task_status.py",
    u"ckan/migration/versions/045_54e3f155d945_user_name_unique.py",
    u"ckan/migration/versions/046_b69e9b80396f_drop_changesets.py",
    u"ckan/migration/versions/047_883a7c406926_rename_package_group_member.py",
    u"ckan/migration/versions/048_4a7011172b3f_add_activity_streams_tables.py",
    u"ckan/migration/versions/049_e0c06c2177b5_add_group_approval_status.py",
    u"ckan/migration/versions/050_01a6b058cb7f_term_translation_table.py",
    u"ckan/migration/versions/051_a4fb0d85ced6_add_tag_vocabulary.py",
    u"ckan/migration/versions/052_ba693d64c6d7_update_member_capacities.py",
    u"ckan/migration/versions/053_9d051a099097_add_group_logo.py",
    u"ckan/migration/versions/054_da21b38da4db_add_resource_created_date.py",
    u"ckan/migration/versions/055_048f7db947bf_update_user_and_activity_detail.py",
    u"ckan/migration/versions/056_11af3215ae89_add_related_table.py",
    u"ckan/migration/versions/057_660a5aae527e_tracking.py",
    u"ckan/migration/versions/058_bd36d1826a5d_add_follower_tables.py",
    u"ckan/migration/versions/059_9291bb46f352_add_related_count_and_flag.py",
    u"ckan/migration/versions/060_31ad11c518fc_add_system_info_table.py",
    u"ckan/migration/versions/061_338d460bc460_add_follower_group_table.py",
    u"ckan/migration/versions/062_6deb2bbab394_add_dashboard_table.py",
    u"ckan/migration/versions/063_8b633852cb7a_org_changes.py",
    u"ckan/migration/versions/064_4f8becd4919a_add_email_last_sent_column.py",
    u"ckan/migration/versions/065_1fab0bc6439e_add_email_notifications_preference.py",
    u"ckan/migration/versions/066_ad16b3bd8cb6_default_package_type.py",
    u"ckan/migration/versions/067_266c110eafec_turn_extras_to_strings.py",
    u"ckan/migration/versions/068_e33a5f2b2a84_add_package_extras_index.py",
    u"ckan/migration/versions/069_e7524c675cdb_resource_url_and_metadata_modified.py",
    u"ckan/migration/versions/070_cfb544112fa7_add_activity_and_resource_indexes.py",
    u"ckan/migration/versions/071_c16f081ef73a_add_state_column_to_user_table.py",
    u"ckan/migration/versions/072_08dcb9233ad7_add_resource_view.py",
    u"ckan/migration/versions/073_011f51208be3_update_resource_view_resource_id_.py",
    u"ckan/migration/versions/074_a4ca55f0f45e_remove_resource_groups.py",
    u"ckan/migration/versions/075_9cdc88c8896a_rename_view_plugins.py",
    u"ckan/migration/versions/076_59995aa965c0_rename_view_plugins_2.py",
    u"ckan/migration/versions/077_51171a04d86d_add_revisions_to_system_info.py",
    u"ckan/migration/versions/078_ae821876532a_remove_old_authz_model.py",
    u"ckan/migration/versions/079_e0177a15d2c9_resource_revision_index.py",
    u"ckan/migration/versions/080_8224d872c64f_continuity_id_indexes.py",
    u"ckan/migration/versions/081_a64cf4a79182_set_datastore_active.py",
    u"ckan/migration/versions/082_8ea886d0ede4_create_index_creator_user_id.py",
    u"ckan/migration/versions/083_f98d8fa2a7f7_remove_related_items.py",
    u"ckan/migration/versions/084_d85ce5783688_add_metadata_created.py",
    u"ckan/migration/versions/085_f9bf3d5c4b4d_adjust_activity_timestamps.py",
    u"ckan/migration/versions/086_19663581b3bb_drop_openid_column.py",
    u"ckan/migration/versions/087_ff1b303cab77_remove_old_authorization_tables.py",
    u"ckan/migration/versions/088_3ad397f70903_remove_migrate_version_table.py",
    u"ckan/model/__init__.py",
    u"ckan/model/activity.py",
    u"ckan/model/core.py",
    u"ckan/model/dashboard.py",
    u"ckan/model/domain_object.py",
    u"ckan/model/extension.py",
    u"ckan/model/follower.py",
    u"ckan/model/group.py",
    u"ckan/model/group_extra.py",
    u"ckan/model/license.py",
    u"ckan/model/meta.py",
    u"ckan/model/misc.py",
    u"ckan/model/modification.py",
    u"ckan/model/package.py",
    u"ckan/model/package_extra.py",
    u"ckan/model/package_relationship.py",
    u"ckan/model/rating.py",
    u"ckan/model/resource.py",
    u"ckan/model/resource_view.py",
    u"ckan/model/system_info.py",
    u"ckan/model/tag.py",
    u"ckan/model/task_status.py",
    u"ckan/model/term_translation.py",
    u"ckan/model/tracking.py",
    u"ckan/model/types.py",
    u"ckan/model/user.py",
    u"ckan/model/vocabulary.py",
    u"ckan/pastertemplates/__init__.py",
    u"ckan/plugins/core.py",
    u"ckan/plugins/toolkit.py",
    u"ckan/plugins/toolkit_sphinx_extension.py",
    u"ckan/tests/config/test_environment.py",
    u"ckan/tests/controllers/__init__.py",
    u"ckan/tests/controllers/test_admin.py",
    u"ckan/tests/controllers/test_api.py",
    u"ckan/tests/controllers/test_feed.py",
    u"ckan/tests/controllers/test_group.py",
    u"ckan/tests/controllers/test_home.py",
    u"ckan/tests/controllers/test_organization.py",
    u"ckan/tests/controllers/test_package.py",
    u"ckan/tests/controllers/test_user.py",
    u"ckan/tests/controllers/test_util.py",
    u"ckan/tests/factories.py",
    u"ckan/tests/helpers.py",
    u"ckan/tests/i18n/test_check_po_files.py",
    u"ckan/tests/legacy/__init__.py",
    u"ckan/tests/legacy/ckantestplugins.py",
    u"ckan/tests/legacy/functional/api/__init__.py",
    u"ckan/tests/legacy/functional/api/base.py",
    u"ckan/tests/legacy/functional/api/model/test_group.py",
    u"ckan/tests/legacy/functional/api/model/test_licenses.py",
    u"ckan/tests/legacy/functional/api/model/test_package.py",
    u"ckan/tests/legacy/functional/api/model/test_ratings.py",
    u"ckan/tests/legacy/functional/api/model/test_relationships.py",
    u"ckan/tests/legacy/functional/api/model/test_revisions.py",
    u"ckan/tests/legacy/functional/api/model/test_tag.py",
    u"ckan/tests/legacy/functional/api/model/test_vocabulary.py",
    u"ckan/tests/legacy/functional/api/test_activity.py",
    u"ckan/tests/legacy/functional/api/test_api.py",
    u"ckan/tests/legacy/functional/api/test_dashboard.py",
    u"ckan/tests/legacy/functional/api/test_email_notifications.py",
    u"ckan/tests/legacy/functional/api/test_follow.py",
    u"ckan/tests/legacy/functional/api/test_misc.py",
    u"ckan/tests/legacy/functional/api/test_package_search.py",
    u"ckan/tests/legacy/functional/api/test_resource.py",
    u"ckan/tests/legacy/functional/api/test_resource_search.py",
    u"ckan/tests/legacy/functional/api/test_user.py",
    u"ckan/tests/legacy/functional/api/test_util.py",
    u"ckan/tests/legacy/functional/test_activity.py",
    u"ckan/tests/legacy/functional/test_admin.py",
    u"ckan/tests/legacy/functional/test_error.py",
    u"ckan/tests/legacy/functional/test_group.py",
    u"ckan/tests/legacy/functional/test_package.py",
    u"ckan/tests/legacy/functional/test_pagination.py",
    u"ckan/tests/legacy/functional/test_preview_interface.py",
    u"ckan/tests/legacy/functional/test_revision.py",
    u"ckan/tests/legacy/functional/test_tag.py",
    u"ckan/tests/legacy/functional/test_tracking.py",
    u"ckan/tests/legacy/functional/test_user.py",
    u"ckan/tests/legacy/html_check.py",
    u"ckan/tests/legacy/lib/__init__.py",
    u"ckan/tests/legacy/lib/test_authenticator.py",
    u"ckan/tests/legacy/lib/test_cli.py",
    u"ckan/tests/legacy/lib/test_dictization.py",
    u"ckan/tests/legacy/lib/test_dictization_schema.py",
    u"ckan/tests/legacy/lib/test_email_notifications.py",
    u"ckan/tests/legacy/lib/test_hash.py",
    u"ckan/tests/legacy/lib/test_helpers.py",
    u"ckan/tests/legacy/lib/test_i18n.py",
    u"ckan/tests/legacy/lib/test_navl.py",
    u"ckan/tests/legacy/lib/test_resource_search.py",
    u"ckan/tests/legacy/lib/test_simple_search.py",
    u"ckan/tests/legacy/lib/test_solr_package_search.py",
    u"ckan/tests/legacy/lib/test_solr_package_search_synchronous_update.py",
    u"ckan/tests/legacy/lib/test_solr_schema_version.py",
    u"ckan/tests/legacy/lib/test_solr_search_index.py",
    u"ckan/tests/legacy/lib/test_tag_search.py",
    u"ckan/tests/legacy/logic/test_action.py",
    u"ckan/tests/legacy/logic/test_auth.py",
    u"ckan/tests/legacy/logic/test_init.py",
    u"ckan/tests/legacy/logic/test_member.py",
    u"ckan/tests/legacy/logic/test_tag.py",
    u"ckan/tests/legacy/logic/test_tag_vocab.py",
    u"ckan/tests/legacy/logic/test_validators.py",
    u"ckan/tests/legacy/misc/test_format_text.py",
    u"ckan/tests/legacy/misc/test_sync.py",
    u"ckan/tests/legacy/mock_plugin.py",
    u"ckan/tests/legacy/models/test_activity.py",
    u"ckan/tests/legacy/models/test_extras.py",
    u"ckan/tests/legacy/models/test_follower.py",
    u"ckan/tests/legacy/models/test_group.py",
    u"ckan/tests/legacy/models/test_misc.py",
    u"ckan/tests/legacy/models/test_package.py",
    u"ckan/tests/legacy/models/test_package_relationships.py",
    u"ckan/tests/legacy/models/test_purge_revision.py",
    u"ckan/tests/legacy/models/test_resource.py",
    u"ckan/tests/legacy/models/test_revision.py",
    u"ckan/tests/legacy/models/test_user.py",
    u"ckan/tests/legacy/schema/test_schema.py",
    u"ckan/tests/legacy/test_coding_standards.py",
    u"ckan/tests/legacy/test_plugins.py",
    u"ckan/tests/legacy/test_versions.py",
    u"ckan/tests/lib/__init__.py",
    u"ckan/tests/lib/dictization/test_model_dictize.py",
    u"ckan/tests/lib/navl/test_dictization_functions.py",
    u"ckan/tests/lib/navl/test_validators.py",
    u"ckan/tests/lib/search/test_index.py",
    u"ckan/tests/lib/test_app_globals.py",
    u"ckan/tests/lib/test_auth_tkt.py",
    u"ckan/tests/lib/test_base.py",
    u"ckan/tests/lib/test_config_tool.py",
    u"ckan/tests/lib/test_datapreview.py",
    u"ckan/tests/lib/test_helpers.py",
    u"ckan/tests/lib/test_mailer.py",
    u"ckan/tests/lib/test_munge.py",
    u"ckan/tests/lib/test_navl.py",
    u"ckan/tests/logic/action/__init__.py",
    u"ckan/tests/logic/action/test_create.py",
    u"ckan/tests/logic/action/test_delete.py",
    u"ckan/tests/logic/action/test_get.py",
    u"ckan/tests/logic/action/test_patch.py",
    u"ckan/tests/logic/action/test_update.py",
    u"ckan/tests/logic/auth/__init__.py",
    u"ckan/tests/logic/auth/test_create.py",
    u"ckan/tests/logic/auth/test_delete.py",
    u"ckan/tests/logic/auth/test_get.py",
    u"ckan/tests/logic/auth/test_init.py",
    u"ckan/tests/logic/auth/test_update.py",
    u"ckan/tests/logic/test_conversion.py",
    u"ckan/tests/logic/test_converters.py",
    u"ckan/tests/logic/test_schema.py",
    u"ckan/tests/logic/test_validators.py",
    u"ckan/tests/migration/__init__.py",
    u"ckan/tests/model/__init__.py",
    u"ckan/tests/model/test_license.py",
    u"ckan/tests/model/test_resource.py",
    u"ckan/tests/model/test_resource_view.py",
    u"ckan/tests/model/test_system_info.py",
    u"ckan/tests/model/test_user.py",
    u"ckan/tests/plugins/__init__.py",
    u"ckan/tests/plugins/test_toolkit.py",
    u"ckan/tests/test_authz.py",
    u"ckan/tests/test_factories.py",
    u"ckanext/datapusher/cli.py",
    u"ckanext/datapusher/helpers.py",
    u"ckanext/datapusher/interfaces.py",
    u"ckanext/datapusher/logic/action.py",
    u"ckanext/datapusher/logic/schema.py",
    u"ckanext/datapusher/plugin.py",
    u"ckanext/datapusher/tests/test.py",
    u"ckanext/datapusher/tests/test_action.py",
    u"ckanext/datapusher/tests/test_default_views.py",
    u"ckanext/datapusher/tests/test_interfaces.py",
    u"ckanext/datastore/helpers.py",
    u"ckanext/datastore/backend/__init__.py",
    u"ckanext/datastore/backend/postgres.py",
    u"ckanext/datastore/interfaces.py",
    u"ckanext/datastore/logic/action.py",
    u"ckanext/datastore/logic/auth.py",
    u"ckanext/datastore/logic/schema.py",
    u"ckanext/datastore/plugin.py",
    u"ckanext/datastore/tests/helpers.py",
    u"ckanext/datastore/tests/sample_datastore_plugin.py",
    u"ckanext/datastore/tests/test_configure.py",
    u"ckanext/datastore/tests/test_create.py",
    u"ckanext/datastore/tests/test_db.py",
    u"ckanext/datastore/tests/test_delete.py",
    u"ckanext/datastore/tests/test_disable.py",
    u"ckanext/datastore/tests/test_dump.py",
    u"ckanext/datastore/tests/test_helpers.py",
    u"ckanext/datastore/tests/test_info.py",
    u"ckanext/datastore/tests/test_interface.py",
    u"ckanext/datastore/tests/test_plugin.py",
    u"ckanext/datastore/tests/test_search.py",
    u"ckanext/datastore/tests/test_unit.py",
    u"ckanext/datastore/tests/test_upsert.py",
    u"ckanext/example_iauthfunctions/plugin_v2.py",
    u"ckanext/example_iauthfunctions/plugin_v3.py",
    u"ckanext/example_iauthfunctions/plugin_v4.py",
    u"ckanext/example_iauthfunctions/plugin_v5_custom_config_setting.py",
    u"ckanext/example_iauthfunctions/plugin_v6_parent_auth_functions.py",
    u"ckanext/example_iauthfunctions/tests/test_example_iauthfunctions.py",
    u"ckanext/example_iconfigurer/plugin.py",
    u"ckanext/example_iconfigurer/plugin_v1.py",
    u"ckanext/example_iconfigurer/plugin_v2.py",
    u"ckanext/example_iconfigurer/tests/test_example_iconfigurer.py",
    u"ckanext/example_iconfigurer/tests/test_iconfigurer_toolkit.py",
    u"ckanext/example_iconfigurer/tests/test_iconfigurer_update_config.py",
    u"ckanext/example_idatasetform/plugin.py",
    u"ckanext/example_idatasetform/plugin_v1.py",
    u"ckanext/example_idatasetform/plugin_v2.py",
    u"ckanext/example_idatasetform/plugin_v3.py",
    u"ckanext/example_idatasetform/plugin_v4.py",
    u"ckanext/example_idatasetform/tests/test_controllers.py",
    u"ckanext/example_idatasetform/tests/test_example_idatasetform.py",
    u"ckanext/example_igroupform/plugin.py",
    u"ckanext/example_igroupform/tests/test_controllers.py",
    u"ckanext/example_iresourcecontroller/plugin.py",
    u"ckanext/example_iresourcecontroller/tests/test_example_iresourcecontroller.py",
    u"ckanext/example_itemplatehelpers/plugin.py",
    u"ckanext/example_itranslation/plugin.py",
    u"ckanext/example_itranslation/plugin_v1.py",
    u"ckanext/example_itranslation/tests/test_plugin.py",
    u"ckanext/example_iuploader/plugin.py",
    u"ckanext/example_iuploader/test/test_plugin.py",
    u"ckanext/example_ivalidators/plugin.py",
    u"ckanext/example_ivalidators/tests/test_ivalidators.py",
    u"ckanext/example_theme_docs/custom_config_setting/plugin.py",
    u"ckanext/example_theme_docs/custom_emails/plugin.py",
    u"ckanext/example_theme_docs/custom_emails/tests.py",
    u"ckanext/example_theme_docs/v01_empty_extension/plugin.py",
    u"ckanext/example_theme_docs/v02_empty_template/plugin.py",
    u"ckanext/example_theme_docs/v03_jinja/plugin.py",
    u"ckanext/example_theme_docs/v04_ckan_extends/plugin.py",
    u"ckanext/example_theme_docs/v05_block/plugin.py",
    u"ckanext/example_theme_docs/v06_super/plugin.py",
    u"ckanext/example_theme_docs/v07_helper_function/plugin.py",
    u"ckanext/example_theme_docs/v08_custom_helper_function/plugin.py",
    u"ckanext/example_theme_docs/v09_snippet/plugin.py",
    u"ckanext/example_theme_docs/v10_custom_snippet/plugin.py",
    u"ckanext/example_theme_docs/v11_HTML_and_CSS/plugin.py",
    u"ckanext/example_theme_docs/v12_extra_public_dir/plugin.py",
    u"ckanext/example_theme_docs/v13_custom_css/plugin.py",
    u"ckanext/example_theme_docs/v14_more_custom_css/plugin.py",
    u"ckanext/example_theme_docs/v15_fanstatic/plugin.py",
    u"ckanext/example_theme_docs/v16_initialize_a_javascript_module/plugin.py",
    u"ckanext/example_theme_docs/v17_popover/plugin.py",
    u"ckanext/example_theme_docs/v18_snippet_api/plugin.py",
    u"ckanext/example_theme_docs/v19_01_error/plugin.py",
    u"ckanext/example_theme_docs/v19_02_error_handling/plugin.py",
    u"ckanext/example_theme_docs/v20_pubsub/plugin.py",
    u"ckanext/example_theme_docs/v21_custom_jquery_plugin/plugin.py",
    u"ckanext/imageview/plugin.py",
    u"ckanext/imageview/tests/test_view.py",
    u'ckanext/audioview/plugin.py',
    u'ckanext/audioview/tests/test_view.py',
    u'ckanext/videoview/plugin.py',
    u'ckanext/videoview/tests/test_view.py',
    u"ckanext/multilingual/plugin.py",
    u"ckanext/multilingual/tests/test_multilingual_plugin.py",
    u"ckanext/reclineview/plugin.py",
    u"ckanext/reclineview/tests/test_view.py",
    u"ckanext/resourceproxy/controller.py",
    u"ckanext/resourceproxy/plugin.py",
    u"ckanext/resourceproxy/tests/test_proxy.py",
    u"ckanext/stats/__init__.py",
    u"ckanext/stats/controller.py",
    u"ckanext/stats/plugin.py",
    u"ckanext/stats/stats.py",
    u"ckanext/stats/tests/__init__.py",
    u"ckanext/stats/tests/test_stats_lib.py",
    u"ckanext/stats/tests/test_stats_plugin.py",
    u"ckanext/test_tag_vocab_plugin.py",
    u"ckanext/textview/plugin.py",
    u"ckanext/textview/tests/test_view.py",
    u"ckanext/webpageview/plugin.py",
    u"ckanext/webpageview/tests/test_view.py",
    u"doc/conf.py",
    u"setup.py",
]


@pytest.mark.skipif(six.PY3, reason=u"")
def test_string_literals_are_prefixed():
    u"""
    Test that string literals are prefixed by ``u``, ``b`` or ``ur``.

    See http://docs.ckan.org/en/latest/contributing/unicode.html.
    """
    errors = []
    for abs_path, rel_path in walk_python_files():
        if rel_path in _STRING_LITERALS_WHITELIST:
            continue
        problems = find_unprefixed_string_literals(abs_path)
        if problems:
            errors.append((rel_path, problems))
    if errors:
        lines = [u"Unprefixed string literals:"]
        for filename, problems in errors:
            lines.append(u"  " + filename)
            for line_no, col_no in problems:
                lines.append(u"    line {}, column {}".format(line_no, col_no))
        raise AssertionError(u"\n".join(lines))
