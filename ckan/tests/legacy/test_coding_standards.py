# encoding: utf-8

'''
The aim of these tests is to check and improve the coding standards in ckan.
Common issues are tested for here and tests fail if they are discovered in
files that are either new or were previously good. Bad files are
blacklisted to prevent them throwing errors in many cases because of the
number of affected files e.g. PEP8.  However if files start to pass a test
will fail and the file should be removed from the blacklist so that it will
then be kept clean in future.

The idea is to slowly improve the code quality in ckan without having files
deteriourating when they do reach the required standard.

Please do not add new files to the list as any new files should meet the
current coding standards.  Please add comments by files that fail if there
are legitimate reasons for the failure.
'''

import cStringIO
import inspect
import itertools
import os
import re
import sys

import pycodestyle

file_path = os.path.dirname(__file__)
base_path = os.path.abspath(os.path.join(file_path, '..', '..', '..'))


def process_directory(directory, ext='.py'):
    base_len = len(base_path) + 1
    for (dirpath, dirnames, filenames) in os.walk(directory):
        # ignore hidden files and dir
        filenames = [f for f in filenames if not f[0] == '.']
        dirnames[:] = [d for d in dirnames if not d[0] == '.']
        for name in filenames:
            if name.endswith(ext):
                path = os.path.join(dirpath, name)
                filename = path[base_len:]
                yield path, filename


def output_errors(filename, errors):
    out = ['']
    out.append('-' * len(filename))
    out.append(filename)
    out.append('-' * len(filename))
    for error in errors:
        out.append(error)
    return '\n'.join(out)


def show_fails(msg, errors):
    if errors:
        msg = ['\n%s' % msg]
        for error in errors:
            msg.append(errors[error])
        msg.append('\n\nFailing Files:\n==============')
        msg += sorted(errors)
        raise Exception('\n'.join(msg))


def show_passing(msg, errors):
    if errors:
        raise Exception('\n%s\n\n' % msg + '\n'.join(sorted(errors)))


def cs_filter(f, filter_, ignore_comment_lines=True):
    ''' filter the file removing comments if requested.
    looks for comments like
    # CS: <filter_> ignore
    # CS: <filter_> ignore x line
    and removes the requested number of lines.  Lines are removed by
    blanking so the line numbers reported will be correct.  This allows us
    to check files that have known violations of the test rules. '''

    # this RegEx is of poor quality but works
    exp = r'^\s*#\s+CS:.*%s.*ignore\D*((\d+)\s+line)*'
    re_ignore = re.compile(exp % filter_)
    ignore = 0
    out = []
    count = 1
    for line in f:
        # ignore the line if we have been told too
        if ignore > 0:
            line = ''
            ignore -= 1
        matches = re_ignore.search(line)
        if matches:
            ignore = int(matches.group(2) or 1)
        # ignore comments out lines
        if ignore_comment_lines and line.lstrip().startswith('#'):
            line = ''
        out.append(line)
        count += 1
    return out


class TestBadSpellings(object):

    BAD_SPELLING_BLACKLIST_FILES = []

    # these are the bad spellings with the correct spelling
    # use LOWER case
    BAD_SPELLINGS = {
        # CS: bad_spelling ignore 2 lines
        'licence': 'license',
        'organisation': 'organization',
    }

    fails = {}
    passes = []
    done = False

    @classmethod
    def setup(cls):
        if not cls.done:
            cls.process()
        cls.done = True

    @classmethod
    def process(cls):
        blacklist = cls.BAD_SPELLING_BLACKLIST_FILES
        re_bad_spelling = re.compile(
            r'(%s)' % '|'.join([x for x in cls.BAD_SPELLINGS]),
            flags=re.IGNORECASE
        )
        files = itertools.chain.from_iterable([
            process_directory(base_path),
            process_directory(base_path, ext='.rst')])
        for path, filename in files:
            f = open(path, 'r')
            count = 1
            errors = []
            for line in cs_filter(f, 'bad_spelling'):
                matches = re_bad_spelling.findall(line)
                if matches:
                    bad_words = []
                    for m in matches:
                        if m not in bad_words:
                            bad_words.append('%s use %s' %
                                             (m, cls.BAD_SPELLINGS[m.lower()]))
                    bad = ', '.join(bad_words)
                    errors.append('ln:%s \t%s\n<%s>' % (count, line[:-1], bad))
                count += 1
            if errors and filename not in blacklist:
                cls.fails[filename] = output_errors(filename, errors)
            elif not errors and filename in blacklist:
                cls.passes.append(filename)

    def test_good(self):
        msg = 'The following files passed bad spellings rules'
        msg += '\nThey need removing from the test blacklist'
        show_passing(msg, self.passes)

    def test_bad(self):
        msg = 'The following files have bad spellings that need fixing'
        show_fails(msg, self.fails)


class TestNastyString(object):
    # CS: nasty_string ignore
    ''' Look for a common coding problem in ckan '..%s..' % str(x) '''

    # Nasty str() issues
    #
    # There are places in ckan where code is like `'...%s..' % str(..)`
    # these cause problems when unicode is present but can remain dormant
    # for a long time before the issue is apparent so try to remove these.
    # The value is converted to a string anyway so the str() is unneeded in
    # any place.

    NASTY_STR_BLACKLIST_FILES = []

    fails = {}
    passes = []
    done = False

    @classmethod
    def setup(cls):
        if not cls.done:
            cls.process()
        cls.done = True

    @classmethod
    def process(cls):
        blacklist = cls.NASTY_STR_BLACKLIST_FILES
        re_nasty_str = re.compile(
            r'''("[^"]*\%s[^"]*"|'[^']*\%s[^']*').*%.*str\('''
        )
        for path, filename in process_directory(base_path):
            f = open(path, 'r')
            count = 1
            errors = []
            for line in cs_filter(f, 'nasty_string'):
                if re_nasty_str.search(line):
                    errors.append('ln:%s \t%s' % (count, line[:-1]))
                count += 1
            if errors and filename not in blacklist:
                cls.fails[filename] = output_errors(filename, errors)
            elif not errors and filename in blacklist:
                cls.passes.append(filename)

    def test_good(self):
        msg = 'The following files passed nasty str() rules'
        msg += '\nThey need removing from the test blacklist'
        show_passing(msg, self.passes)

    def test_bad(self):
        # CS: nasty_string ignore next 2 lines
        msg = ('The following files have nasty str() issues that need'
               ' resolving\nCode is like `\'...%s..\' % str(..)`'
               'and should just be `\'...%s..\' % ..`')
        show_fails(msg, self.fails)


class TestImportStar(object):
    ''' Find files using from xxx import * '''

    # Import * file exceptions
    #
    # The following files contain one or more `from ... import *` lines
    # which should not be used in ckan where possible.  If the files get
    # fixed they should be removed from this list.
    #
    # import * is bad for many reasons and should be avoided.

    IMPORT_STAR_BLACKLIST_FILES = [
        'ckan/migration/versions/001_add_existing_tables.py',
        'ckan/migration/versions/002_add_author_and_maintainer.py',
        'ckan/migration/versions/003_add_user_object.py',
        'ckan/migration/versions/004_add_group_object.py',
        'ckan/migration/versions/005_add_authorization_tables.py',
        'ckan/migration/versions/006_add_ratings.py',
        'ckan/migration/versions/007_add_system_roles.py',
        'ckan/migration/versions/008_update_vdm_ids.py',
        'ckan/migration/versions/009_add_creation_timestamps.py',
        'ckan/migration/versions/010_add_user_about.py',
        'ckan/migration/versions/011_add_package_search_vector.py',
        'ckan/migration/versions/012_add_resources.py',
        'ckan/migration/versions/013_add_hash.py',
        'ckan/migration/versions/014_hash_2.py',
        'ckan/migration/versions/015_remove_state_object.py',
        'ckan/migration/versions/016_uuids_everywhere.py',
        'ckan/migration/versions/017_add_pkg_relationships.py',
        'ckan/migration/versions/018_adjust_licenses.py',
        'ckan/migration/versions/019_pkg_relationships_state.py',
        'ckan/migration/versions/020_add_changeset.py',
        'ckan/migration/versions/022_add_group_extras.py',
        'ckan/migration/versions/023_add_harvesting.py',
        'ckan/migration/versions/024_add_harvested_document.py',
        'ckan/migration/versions/025_add_authorization_groups.py',
        'ckan/migration/versions/026_authorization_group_user_pk.py',
        'ckan/migration/versions/027_adjust_harvester.py',
        'ckan/migration/versions/028_drop_harvest_source_status.py',
        'ckan/migration/versions/029_version_groups.py',
        'ckan/migration/versions/030_additional_user_attributes.py',
        'ckan/migration/versions/031_move_openid_to_new_field.py',
        'ckan/migration/versions/032_add_extra_info_field_to_resources.py',
        'ckan/migration/versions/033_auth_group_user_id_add_conditional.py',
        'ckan/migration/versions/034_resource_group_table.py',
        'ckan/migration/versions/035_harvesting_doc_versioning.py',
        'ckan/migration/versions/036_lockdown_roles.py',
        'ckan/migration/versions/037_role_anon_editor.py',
        'ckan/migration/versions/038_delete_migration_tables.py',
        'ckan/migration/versions/039_add_expired_id_and_dates.py',
        'ckan/migration/versions/040_reset_key_on_user.py',
        'ckan/migration/versions/041_resource_new_fields.py',
        'ckan/migration/versions/042_user_revision_indexes.py',
        'ckan/migration/versions/043_drop_postgres_search.py',
        'ckan/migration/versions/044_add_task_status.py',
        'ckan/migration/versions/045_user_name_unique.py',
        'ckan/migration/versions/046_drop_changesets.py',
        'ckan/migration/versions/047_rename_package_group_member.py',
        'ckan/migration/versions/048_add_activity_streams_tables.py',
        'ckan/migration/versions/049_add_group_approval_status.py',
        'ckan/migration/versions/050_term_translation_table.py',
        'ckan/migration/versions/051_add_tag_vocabulary.py',
        'ckan/migration/versions/052_update_member_capacities.py',
        'ckan/migration/versions/053_add_group_logo.py',
        'ckan/migration/versions/056_add_related_table.py',
        'ckan/migration/versions/057_tracking.py',
        'ckan/migration/versions/058_add_follower_tables.py',
        'ckan/migration/versions/059_add_related_count_and_flag.py',
        'ckan/migration/versions/060_add_system_info_table.py',
        'ckan/migration/versions/061_add_follower__group_table.py',
        'ckan/migration/versions/062_add_dashboard_table.py',
        'ckan/migration/versions/063_org_changes.py',
        'ckan/migration/versions/064_add_email_last_sent_column.py',
        'ckan/migration/versions/065_add_email_notifications_preference.py',
        'ckan/plugins/__init__.py',
        'ckan/tests/legacy/functional/api/base.py',
        'ckan/tests/legacy/functional/api/test_api.py',
        'ckan/tests/legacy/functional/api/test_misc.py',
        'ckan/tests/legacy/functional/api/test_package_search.py',
        'ckan/tests/legacy/functional/api/test_resource_search.py',
        'ckan/tests/legacy/functional/api/test_revision_search.py',
        'ckan/tests/legacy/functional/test_group.py',
        'ckan/tests/legacy/functional/test_home.py',
        'ckan/tests/legacy/functional/test_package.py',
        'ckan/tests/legacy/functional/test_package_relationships.py',
        'ckan/tests/legacy/functional/test_tag.py',
        'ckan/tests/legacy/lib/test_helpers.py',
        'ckan/tests/legacy/lib/test_resource_search.py',
        'ckan/tests/legacy/lib/test_tag_search.py',
        'ckan/tests/legacy/misc/test_sync.py',
        'ckan/tests/legacy/models/test_extras.py',
        'ckan/tests/legacy/models/test_misc.py',
        'ckan/tests/legacy/models/test_package.py',
        'ckan/tests/legacy/models/test_package_relationships.py',
        'ckan/tests/legacy/models/test_purge_revision.py',
        'ckan/tests/legacy/models/test_resource.py',
        'ckan/tests/legacy/models/test_revision.py',
        'ckan/tests/legacy/models/test_user.py',
        'ckan/tests/legacy/pylons_controller.py',
        'fabfile.py',
    ]
    fails = {}
    passes = []
    done = False

    @classmethod
    def setup(cls):
        if not cls.done:
            cls.process()
        cls.done = True

    @classmethod
    def process(cls):
        blacklist = cls.IMPORT_STAR_BLACKLIST_FILES
        re_import_star = re.compile(r'^\s*from\s+.*\simport\s+\*')
        for path, filename in process_directory(base_path):
            f = open(path, 'r')
            count = 1
            errors = []
            for line in f:
                if re_import_star.search(line):
                    errors.append('%s ln:%s import *\n\t%s'
                                  % (filename, count, line))
                count += 1
            if errors and filename not in blacklist:
                cls.fails[filename] = output_errors(filename, errors)
            elif not errors and filename in blacklist:
                cls.passes.append(filename)

    def test_import_good(self):
        msg = 'The following files passed import * rules'
        msg += '\nThey need removing from the test blacklist'
        show_passing(msg, self.passes)

    def test_import_bad(self):
        msg = ('The following files have import * issues that need resolving\n'
               '`from ... import *` lines which should not be used in ckan'
               ' where possible.')
        show_fails(msg, self.fails)


class TestPep8(object):
    ''' Check that .py files are pep8 compliant '''

    # PEP8 File exceptions
    #
    # The following files have known PEP8 errors.  When the files get to a
    # point of not having any such errors they should be removed from this
    # list to prevent new errors being added to the file.

    PEP8_BLACKLIST_FILES = [
        'bin/running_stats.py',
        'ckan/__init__.py',
        'ckan/ckan_nose_plugin.py',
        'ckan/config/middleware.py',
        'ckan/config/routing.py',
        'ckan/config/sp_config.py',
        'ckan/controllers/admin.py',
        'ckan/controllers/revision.py',
        'ckan/include/rcssmin.py',
        'ckan/include/rjsmin.py',
        'ckan/lib/activity_streams.py',
        'ckan/lib/activity_streams_session_extension.py',
        'ckan/lib/alphabet_paginate.py',
        'ckan/lib/app_globals.py',
        'ckan/lib/captcha.py',
        'ckan/lib/cli.py',
        'ckan/lib/create_test_data.py',
        'ckan/lib/dictization/__init__.py',
        'ckan/lib/dictization/model_dictize.py',
        'ckan/lib/dictization/model_save.py',
        'ckan/lib/email_notifications.py',
        'ckan/lib/extract.py',
        'ckan/lib/fanstatic_extensions.py',
        'ckan/lib/fanstatic_resources.py',
        'ckan/lib/formatters.py',
        'ckan/lib/hash.py',
        'ckan/lib/help/flash_messages.py',
        'ckan/lib/jinja_extensions.py',
        'ckan/lib/jsonp.py',
        'ckan/lib/maintain.py',
        'ckan/lib/navl/validators.py',
        'ckan/lib/package_saver.py',
        'ckan/lib/plugins.py',
        'ckan/lib/render.py',
        'ckan/lib/search/__init__.py',
        'ckan/lib/search/index.py',
        'ckan/lib/search/query.py',
        'ckan/lib/search/sql.py',
        'ckan/logic/action/__init__.py',
        'ckan/logic/action/delete.py',
        'ckan/logic/action/get.py',
        'ckan/logic/action/update.py',
        'ckan/logic/auth/create.py',
        'ckan/logic/auth/delete.py',
        'ckan/logic/auth/get.py',
        'ckan/logic/auth/update.py',
        'ckan/logic/converters.py',
        'ckan/logic/validators.py',
        'ckan/migration/versions/001_add_existing_tables.py',
        'ckan/migration/versions/002_add_author_and_maintainer.py',
        'ckan/migration/versions/003_add_user_object.py',
        'ckan/migration/versions/004_add_group_object.py',
        'ckan/migration/versions/005_add_authorization_tables.py',
        'ckan/migration/versions/006_add_ratings.py',
        'ckan/migration/versions/007_add_system_roles.py',
        'ckan/migration/versions/008_update_vdm_ids.py',
        'ckan/migration/versions/009_add_creation_timestamps.py',
        'ckan/migration/versions/010_add_user_about.py',
        'ckan/migration/versions/011_add_package_search_vector.py',
        'ckan/migration/versions/012_add_resources.py',
        'ckan/migration/versions/013_add_hash.py',
        'ckan/migration/versions/014_hash_2.py',
        'ckan/migration/versions/015_remove_state_object.py',
        'ckan/migration/versions/016_uuids_everywhere.py',
        'ckan/migration/versions/017_add_pkg_relationships.py',
        'ckan/migration/versions/018_adjust_licenses.py',
        'ckan/migration/versions/019_pkg_relationships_state.py',
        'ckan/migration/versions/020_add_changeset.py',
        'ckan/migration/versions/022_add_group_extras.py',
        'ckan/migration/versions/023_add_harvesting.py',
        'ckan/migration/versions/024_add_harvested_document.py',
        'ckan/migration/versions/025_add_authorization_groups.py',
        'ckan/migration/versions/026_authorization_group_user_pk.py',
        'ckan/migration/versions/027_adjust_harvester.py',
        'ckan/migration/versions/028_drop_harvest_source_status.py',
        'ckan/migration/versions/029_version_groups.py',
        'ckan/migration/versions/030_additional_user_attributes.py',
        'ckan/migration/versions/031_move_openid_to_new_field.py',
        'ckan/migration/versions/032_add_extra_info_field_to_resources.py',
        'ckan/migration/versions/033_auth_group_user_id_add_conditional.py',
        'ckan/migration/versions/034_resource_group_table.py',
        'ckan/migration/versions/035_harvesting_doc_versioning.py',
        'ckan/migration/versions/036_lockdown_roles.py',
        'ckan/migration/versions/037_role_anon_editor.py',
        'ckan/migration/versions/038_delete_migration_tables.py',
        'ckan/migration/versions/039_add_expired_id_and_dates.py',
        'ckan/migration/versions/040_reset_key_on_user.py',
        'ckan/migration/versions/041_resource_new_fields.py',
        'ckan/migration/versions/042_user_revision_indexes.py',
        'ckan/migration/versions/043_drop_postgres_search.py',
        'ckan/migration/versions/044_add_task_status.py',
        'ckan/migration/versions/045_user_name_unique.py',
        'ckan/migration/versions/046_drop_changesets.py',
        'ckan/migration/versions/047_rename_package_group_member.py',
        'ckan/migration/versions/048_add_activity_streams_tables.py',
        'ckan/migration/versions/049_add_group_approval_status.py',
        'ckan/migration/versions/050_term_translation_table.py',
        'ckan/migration/versions/051_add_tag_vocabulary.py',
        'ckan/migration/versions/052_update_member_capacities.py',
        'ckan/migration/versions/053_add_group_logo.py',
        'ckan/migration/versions/054_add_resource_created_date.py',
        'ckan/migration/versions/055_update_user_and_activity_detail.py',
        'ckan/migration/versions/056_add_related_table.py',
        'ckan/migration/versions/057_tracking.py',
        'ckan/migration/versions/058_add_follower_tables.py',
        'ckan/migration/versions/059_add_related_count_and_flag.py',
        'ckan/migration/versions/060_add_system_info_table.py',
        'ckan/migration/versions/061_add_follower__group_table.py',
        'ckan/migration/versions/062_add_dashboard_table.py',
        'ckan/migration/versions/063_org_changes.py',
        'ckan/migration/versions/064_add_email_last_sent_column.py',
        'ckan/migration/versions/065_add_email_notifications_preference.py',
        'ckan/migration/versions/067_turn_extras_to_strings.py',
        'ckan/misc.py',
        'ckan/model/__init__.py',
        'ckan/model/activity.py',
        'ckan/model/authz.py',
        'ckan/model/dashboard.py',
        'ckan/model/domain_object.py',
        'ckan/model/follower.py',
        'ckan/model/group.py',
        'ckan/model/group_extra.py',
        'ckan/model/license.py',
        'ckan/model/meta.py',
        'ckan/model/misc.py',
        'ckan/model/modification.py',
        'ckan/model/package.py',
        'ckan/model/package_extra.py',
        'ckan/model/package_relationship.py',
        'ckan/model/rating.py',
        'ckan/model/resource.py',
        'ckan/model/system_info.py',
        'ckan/model/tag.py',
        'ckan/model/task_status.py',
        'ckan/model/term_translation.py',
        'ckan/model/test_user.py',
        'ckan/model/tracking.py',
        'ckan/model/types.py',
        'ckan/model/user.py',
        'ckan/model/vocabulary.py',
        'ckan/authz.py',
        'ckan/pastertemplates/__init__.py',
        'ckan/plugins/interfaces.py',
        'ckan/poo.py',
        'ckan/rating.py',
        'ckan/templates_legacy/home/__init__.py',
        'ckan/tests/legacy/__init__.py',
        'ckan/tests/legacy/ckantestplugin/ckantestplugin/__init__.py',
        'ckan/tests/legacy/ckantestplugin/setup.py',
        'ckan/tests/legacy/ckantestplugins.py',
        'ckan/tests/legacy/functional/api/base.py',
        'ckan/tests/legacy/functional/api/model/test_group.py',
        'ckan/tests/legacy/functional/api/model/test_licenses.py',
        'ckan/tests/legacy/functional/api/model/test_package.py',
        'ckan/tests/legacy/functional/api/model/test_ratings.py',
        'ckan/tests/legacy/functional/api/model/test_relationships.py',
        'ckan/tests/legacy/functional/api/model/test_revisions.py',
        'ckan/tests/legacy/functional/api/model/test_tag.py',
        'ckan/tests/legacy/functional/api/model/test_vocabulary.py',
        'ckan/tests/legacy/functional/api/test_activity.py',
        'ckan/tests/legacy/functional/api/test_api.py',
        'ckan/tests/legacy/functional/api/test_dashboard.py',
        'ckan/tests/legacy/functional/api/test_email_notifications.py',
        'ckan/tests/legacy/functional/api/test_follow.py',
        'ckan/tests/legacy/functional/api/test_misc.py',
        'ckan/tests/legacy/functional/api/test_package_search.py',
        'ckan/tests/legacy/functional/api/test_resource.py',
        'ckan/tests/legacy/functional/api/test_resource_search.py',
        'ckan/tests/legacy/functional/api/test_revision_search.py',
        'ckan/tests/legacy/functional/api/test_user.py',
        'ckan/tests/legacy/functional/api/test_util.py',
        'ckan/tests/legacy/functional/base.py',
        'ckan/tests/legacy/functional/test_activity.py',
        'ckan/tests/legacy/functional/test_admin.py',
        'ckan/tests/legacy/functional/test_cors.py',
        'ckan/tests/legacy/functional/test_error.py',
        'ckan/tests/legacy/functional/test_home.py',
        'ckan/tests/legacy/functional/test_package.py',
        'ckan/tests/legacy/functional/test_package_relationships.py',
        'ckan/tests/legacy/functional/test_pagination.py',
        'ckan/tests/legacy/functional/test_preview_interface.py',
        'ckan/tests/legacy/functional/test_revision.py',
        'ckan/tests/legacy/functional/test_search.py',
        'ckan/tests/legacy/functional/test_tag.py',
        'ckan/tests/legacy/functional/test_tag_vocab.py',
        'ckan/tests/legacy/functional/test_upload.py',
        'ckan/tests/legacy/functional/test_user.py',
        'ckan/tests/legacy/html_check.py',
        'ckan/tests/legacy/lib/__init__.py',
        'ckan/tests/legacy/lib/test_accept.py',
        'ckan/tests/legacy/lib/test_cli.py',
        'ckan/tests/legacy/lib/test_dictization.py',
        'ckan/tests/legacy/lib/test_email_notifications.py',
        'ckan/tests/legacy/lib/test_hash.py',
        'ckan/tests/legacy/lib/test_helpers.py',
        'ckan/tests/legacy/lib/test_mailer.py',
        'ckan/tests/legacy/lib/test_munge.py',
        'ckan/tests/legacy/lib/test_navl.py',
        'ckan/tests/legacy/lib/test_resource_search.py',
        'ckan/tests/legacy/lib/test_simple_search.py',
        'ckan/tests/legacy/lib/test_solr_package_search.py',
        'ckan/tests/legacy/lib/test_solr_package_search_synchronous_update.py',
        'ckan/tests/legacy/lib/test_solr_schema_version.py',
        'ckan/tests/legacy/lib/test_solr_search_index.py',
        'ckan/tests/legacy/lib/test_tag_search.py',
        'ckan/tests/legacy/logic/test_action.py',
        'ckan/tests/legacy/logic/test_auth.py',
        'ckan/tests/legacy/logic/test_tag.py',
        'ckan/tests/legacy/logic/test_validators.py',
        'ckan/tests/legacy/misc/test_format_text.py',
        'ckan/tests/legacy/misc/test_mock_mail_server.py',
        'ckan/tests/legacy/misc/test_sync.py',
        'ckan/tests/legacy/mock_plugin.py',
        'ckan/tests/legacy/models/test_extras.py',
        'ckan/tests/legacy/models/test_group.py',
        'ckan/tests/legacy/models/test_license.py',
        'ckan/tests/legacy/models/test_misc.py',
        'ckan/tests/legacy/models/test_package.py',
        'ckan/tests/legacy/models/test_package_relationships.py',
        'ckan/tests/legacy/models/test_purge_revision.py',
        'ckan/tests/legacy/models/test_resource.py',
        'ckan/tests/legacy/models/test_revision.py',
        'ckan/tests/legacy/models/test_user.py',
        'ckan/tests/legacy/monkey.py',
        'ckan/tests/legacy/pylons_controller.py',
        'ckan/tests/legacy/schema/test_schema.py',
        'ckan/tests/legacy/test_plugins.py',
        'ckan/tests/legacy/test_versions.py',
        'ckan/websetup.py',
        'ckanext/datastore/bin/datastore_setup.py',
        'ckanext/datastore/logic/action.py',
        'ckanext/datastore/tests/test_create.py',
        'ckanext/datastore/tests/test_search.py',
        'ckanext/datastore/tests/test_upsert.py',
        'ckanext/example_idatasetform/plugin.py',
        'ckanext/example_itemplatehelpers/plugin.py',
        'ckanext/multilingual/plugin.py',
        'ckanext/resourceproxy/plugin.py',
        'ckanext/stats/controller.py',
        'ckanext/stats/plugin.py',
        'ckanext/stats/stats.py',
        'ckanext/stats/tests/__init__.py',
        'ckanext/stats/tests/test_stats_lib.py',
        'ckanext/stats/tests/test_stats_plugin.py',
        'ckanext/test_tag_vocab_plugin.py',
        'ckanext/tests/plugin.py',
        'doc/conf.py',
        'fabfile.py',
        'profile_tests.py',
        'setup.py',
    ]
    fails = {}
    passes = []
    done = False

    @classmethod
    def setup(cls):
        if not cls.done:
            cls.process()
        cls.done = True

    @classmethod
    def process(cls):
        blacklist = cls.PEP8_BLACKLIST_FILES
        for path, filename in process_directory(base_path):
            errors = cls.find_pep8_errors(filename=path)
            if errors and filename not in blacklist:
                cls.fails[filename] = output_errors(filename, errors)
            elif not errors and filename in blacklist:
                cls.passes.append(filename)

    def test_pep8_fails(self):
        msg = 'The following files have pep8 issues that need resolving'
        msg += '\nThey need removing from the test blacklist'
        show_fails(msg, self.fails)

    def test_pep8_pass(self):
        msg = 'The following files passed pep8 but are blacklisted'
        show_passing(msg, self.passes)

    @classmethod
    def find_pep8_errors(cls, filename=None, lines=None):
        try:
            sys.stdout = cStringIO.StringIO()
            config = {}

            # Ignore long lines on test files, as the test names can get long
            # when following our test naming standards.
            if cls._is_test(filename):
                config['ignore'] = ['E501']

            checker = pycodestyle.Checker(filename=filename, lines=lines,
                                          **config)
            checker.check_all()
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = sys.__stdout__

        errors = []
        for line in output.split('\n'):
            parts = line.split(' ', 2)
            if len(parts) == 3:
                location, error, desc = parts
                line_no = location.split(':')[1]
                errors.append('%s ln:%s %s' % (error, line_no, desc))
        return errors

    @classmethod
    def _is_test(cls, filename):
        return bool(re.search('(^|\W)test_.*\.py$', filename, re.IGNORECASE))


class TestActionAuth(object):
    ''' These tests check the logic auth/action functions are compliant. The
    main tests are that each action has a corresponding auth function and
    that each auth function has an action.  We check the function only
    accepts (context, data_dict) as parameters. '''

    ACTION_FN_SIGNATURES_BLACKLIST = [
        'create: activity_create',
    ]

    ACTION_NO_AUTH_BLACKLIST = [
        'create: follow_dataset',
        'create: follow_group',
        'create: follow_user',
        'create: package_relationship_create_rest',
        'delete: package_relationship_delete_rest',
        'delete: unfollow_dataset',
        'delete: unfollow_group',
        'delete: unfollow_user',
        'get: activity_detail_list',
        'get: am_following_dataset',
        'get: am_following_group',
        'get: am_following_user',
        'get: dashboard_activity_list_html',
        'get: dataset_followee_count',
        'get: dataset_follower_count',
        'get: followee_count',
        'get: group_activity_list',
        'get: group_activity_list_html',
        'get: group_followee_count',
        'get: group_follower_count',
        'get: group_package_show',
        'get: member_list',
        'get: organization_activity_list',
        'get: organization_activity_list_html',
        'get: organization_follower_count',
        'get: package_activity_list',
        'get: package_activity_list_html',
        'get: recently_changed_packages_activity_list',
        'get: recently_changed_packages_activity_list_html',
        'get: resource_search',
        'get: roles_show',
        'get: status_show',
        'get: tag_search',
        'get: term_translation_show',
        'get: user_activity_list',
        'get: user_activity_list_html',
        'get: user_followee_count',
        'get: user_follower_count',
        'update: package_relationship_update_rest',
        'update: task_status_update_many',
        'update: term_translation_update_many',
    ]

    AUTH_NO_ACTION_BLACKLIST = [
        'create: file_upload',
        'delete: revision_delete',
        'delete: revision_undelete',
        'get: group_autocomplete',
        'get: group_list_available',
        'get: sysadmin',
        'get: request_reset',
        'get: user_reset',
        'update: group_change_state',
        'update: group_edit_permissions',
        'update: package_change_state',
        'update: revision_change_state',
    ]

    ACTION_NO_DOC_STR_BLACKLIST = [
        'create: group_create_rest',
        'create: package_create_rest',
        'create: package_relationship_create_rest',
        'delete: package_relationship_delete_rest',
        'get: get_site_user',
        'get: group_show_rest',
        'get: package_show_rest',
        'get: tag_show_rest',
        'update: group_update_rest',
        'update: package_relationship_update_rest',
        'update: package_update_rest',
    ]

    done = False

    @classmethod
    def setup(cls):
        if not cls.done:
            cls.process()
        cls.done = True

    @classmethod
    def process(cls):
        def get_functions(module_root):
            fns = {}
            for auth_module_name in ['get', 'create', 'update', 'delete', 'patch']:
                module_path = '%s.%s' % (module_root, auth_module_name,)
                try:
                    module = __import__(module_path)
                except ImportError:
                    print ('No auth module for action "%s"' % auth_module_name)

                for part in module_path.split('.')[1:]:
                    module = getattr(module, part)

                for key, v in module.__dict__.items():
                    if not hasattr(v, '__call__'):
                        continue
                    if v.__module__ != module_path:
                        continue
                    if not key.startswith('_'):
                        name = '%s: %s' % (auth_module_name, key)
                        fns[name] = v
            return fns
        cls.actions = get_functions('logic.action')
        cls.auths = get_functions('logic.auth')

    def test_actions_have_auth_fn(self):
        actions_no_auth = set(self.actions.keys()) - set(self.auths.keys())
        actions_no_auth -= set(self.ACTION_NO_AUTH_BLACKLIST)
        assert not actions_no_auth, 'These actions have no auth function\n%s' \
            % '\n'.join(sorted(list(actions_no_auth)))

    def test_actions_have_auth_fn_blacklist(self):
        actions_no_auth = set(self.actions.keys()) & set(self.auths.keys())
        actions_no_auth &= set(self.ACTION_NO_AUTH_BLACKLIST)
        assert not actions_no_auth, 'These actions blacklisted but ' + \
            'shouldn\'t be \n%s' % '\n'.join(sorted(list(actions_no_auth)))

    def test_auths_have_action_fn(self):
        auths_no_action = set(self.auths.keys()) - set(self.actions.keys())
        auths_no_action -= set(self.AUTH_NO_ACTION_BLACKLIST)
        assert not auths_no_action, 'These auth functions have no action\n%s' \
            % '\n'.join(sorted(list(auths_no_action)))

    def test_auths_have_action_fn_blacklist(self):
        auths_no_action = set(self.auths.keys()) & set(self.actions.keys())
        auths_no_action &= set(self.AUTH_NO_ACTION_BLACKLIST)
        assert not auths_no_action, 'These auths functions blacklisted but' + \
            ' shouldn\'t be \n%s' % '\n'.join(sorted(list(auths_no_action)))

    def test_fn_signatures(self):
        errors = []
        for name, fn in self.actions.iteritems():
            args_info = inspect.getargspec(fn)
            if args_info.args != ['context', 'data_dict'] \
                    or args_info.varargs is not None \
                    or args_info.keywords is not None:
                if name not in self.ACTION_FN_SIGNATURES_BLACKLIST:
                    errors.append(name)
        assert not errors, 'These action functions have the wrong function' + \
            ' signature, should be (context, data_dict)\n%s' \
            % '\n'.join(sorted(errors))

    def test_fn_docstrings(self):
        errors = []
        for name, fn in self.actions.iteritems():
            if not getattr(fn, '__doc__', None):
                if name not in self.ACTION_NO_DOC_STR_BLACKLIST:
                    errors.append(name)
        assert not errors, 'These action functions need docstrings\n%s' \
            % '\n'.join(sorted(errors))


class TestBadExceptions(object):
    ''' Look for a common coding problem in ckan Exception(_'...') '''

    # Exceptions should not on the whole be translated as they are for
    # programmers to read in trace backs or log files.  However some like
    # Invalid used in validation functions do get passed back up to the user
    # and so should be translated.

    NASTY_EXCEPTION_BLACKLIST_FILES = [
        'ckan/controllers/api.py',
        'ckan/controllers/user.py',
        'ckan/lib/mailer.py',
        'ckan/logic/action/create.py',
        'ckan/logic/action/delete.py',
        'ckan/logic/action/get.py',
        'ckan/logic/action/update.py',
        'ckan/logic/auth/create.py',
        'ckan/logic/auth/delete.py',
        'ckan/logic/auth/get.py',
        'ckan/authz.py',
        'ckanext/datastore/logic/action.py',
    ]
    fails = {}
    passes = []
    done = False

    @classmethod
    def setup(cls):
        if not cls.done:
            cls.process()
        cls.done = True

    @classmethod
    def process(cls):
        blacklist = cls.NASTY_EXCEPTION_BLACKLIST_FILES
        re_nasty_exception = re.compile(
            r'''raise\W+(?![^I]*Invalid\().*_\('''
        )
        for path, filename in process_directory(base_path):
            f = open(path, 'r')
            count = 1
            errors = []
            for line in f:
                if re_nasty_exception.search(line):
                    errors.append('ln:%s \t%s' % (count, line[:-1]))
                count += 1
            if errors and filename not in blacklist:
                cls.fails[filename] = output_errors(filename, errors)
            elif not errors and filename in blacklist:
                cls.passes.append(filename)

    def test_good(self):
        msg = 'The following files passed nasty exceptions rules'
        msg += '\nThey need removing from the test blacklist'
        show_passing(msg, self.passes)

    def test_bad(self):
        msg = ('The following files have nasty exception issues that need'
               ' resolving\nWe should not be translating exceptions in most'
               ' situations.  We need to when the exception message is passed'
               ' to the front end for example validation')
        show_fails(msg, self.fails)
