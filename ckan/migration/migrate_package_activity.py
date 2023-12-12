# encoding: utf-8

'''
Migrates revisions into the activity stream, to allow you to view old versions
of datasets and changes (diffs) between them.

This should be run once you've upgraded to CKAN 2.9.

This script is not part of the main migrations because it takes a long time to
run, and you don't want it to delay a site going live again after an upgrade.
In the period between upgrading CKAN and this script completes, the Activity
Stream's view of old versions of datasets and diffs between them will be
incomplete - it won't show resources, extras or tags.

This script is idempotent - there is no harm in running this multiple times, or
stopping and restarting it.

We won't delete the revision tables in the database yet, since we haven't
converted the group, package_relationship to activity objects yet.

(In a future version of CKAN we will remove the 'package_revision' table from
the codebase. We'll need a step in the main migration which checks that
migrate_package_activity.py has been done, before it removes the
package_revision table.)
'''

# This code is not part of the main CKAN CLI because it is a one-off migration,
# whereas the main CLI is a list of tools for more frequent use.

from __future__ import print_function
from __future__ import absolute_import
import argparse
from collections import defaultdict
from typing import Any
import sys


# not importing anything from ckan until after the arg parsing, to fail on bad
# args quickly.

_context: Any = None


def get_context():
    from ckan import model
    import ckan.logic as logic
    global _context
    if not _context:
        user = logic.get_action(u'get_site_user')(
            {u'model': model, u'ignore_auth': True}, {})
        _context = {u'model': model, u'session': model.Session,
                    u'user': user[u'name']}
    return _context


def num_unmigrated(engine):
    num_unmigrated = engine.execute('''
        SELECT count(*) FROM activity a JOIN package p ON a.object_id=p.id
        WHERE a.activity_type IN ('new package', 'changed package')
        AND a.data NOT LIKE '%%{"actor"%%'
        AND p.private = false;
    ''').fetchone()[0]
    return num_unmigrated


def num_activities_migratable():
    from ckan import model
    num_activities = model.Session.execute(u'''
    SELECT count(*) FROM activity a JOIN package p ON a.object_id=p.id
    WHERE a.activity_type IN ('new package', 'changed package')
    AND p.private = false;
    ''').fetchall()[0][0]
    return num_activities


def migrate_all_datasets():
    import ckan.logic as logic
    dataset_names = logic.get_action(u'package_list')(get_context(), {})
    num_datasets = len(dataset_names)
    errors = defaultdict(int)
    with PackageDictizeMonkeyPatch():
        for i, dataset_name in enumerate(dataset_names):
            print(u'\n{}/{} dataset: {}'
                  .format(i + 1, num_datasets, dataset_name))
            migrate_dataset(dataset_name, errors)
    print(u'Migrated:')
    print(u'  {} datasets'.format(len(dataset_names)))
    num_activities = num_activities_migratable()
    print(u'  with {} activities'.format(num_activities))
    print_errors(errors)


class PackageDictizeMonkeyPatch(object):
    '''Patches package_dictize to add back in the revision functionality. This
    allows you to specify context['revision_id'] and see the old revisions of
    a package.

    This works as a context object. We could have used mock.patch and saved a
    couple of lines here, but we'd have had to add mock to requirements.txt.
    '''
    def __enter__(self):
        import ckan.lib.dictization.model_dictize as model_dictize
        try:
            import ckan.migration.revision_legacy_code as revision_legacy_code
        except ImportError:
            # convenient to look for it in the current directory if you just
            # download these files because you are upgrading an older ckan
            from . import revision_legacy_code
        self.existing_function = model_dictize.package_dictize
        model_dictize.package_dictize = \
            revision_legacy_code.package_dictize_with_revisions

    def __exit__(self, exc_type, exc_val, exc_tb):
        import ckan.lib.dictization.model_dictize as model_dictize
        model_dictize.package_dictize = self.existing_function


def migrate_dataset(dataset_name, errors):
    '''
    Migrates a single dataset.

    NB this function should be run in a `with PackageDictizeMonkeyPatch():`
    '''

    import ckan.logic as logic
    from ckan import model
    from ckanext.activity.model import Activity
    # 'hidden' activity is that by site_user, such as harvests, which are
    # not shown in the activity stream because they can be too numerous.
    # However these do have Activity objects, and if a hidden Activity is
    # followed be a non-hidden one and you look at the changes of that
    # non-hidden Activity, then it does a diff with the hidden one (rather than
    # the most recent non-hidden one), so it is important to store the
    # package_dict in hidden Activity objects.
    package_activity_stream = logic.get_action(u'package_activity_list')(
        get_context(), {u'id': dataset_name, u'include_hidden_activity': True})
    num_activities = len(package_activity_stream)
    if not num_activities:
        print(u'  No activities')

    # Iterate over this package's existing activity stream objects
    for i, activity in enumerate(reversed(package_activity_stream)):
        # e.g. activity =
        # {'activity_type': u'changed package',
        #  'id': u'62107f87-7de0-4d17-9c30-90cbffc1b296',
        #  'object_id': u'7c6314f5-c70b-4911-8519-58dc39a8e340',
        #  'revision_id': u'c3e8670a-f661-40f4-9423-b011c6a3a11d',
        #  'timestamp': '2018-04-20T16:11:45.363097',
        #  'user_id': u'724273ac-a5dc-482e-add4-adaf1871f8cb'}
        print(u'  activity {}/{} {}'.format(
              i + 1, num_activities, activity[u'timestamp']))

        # we need activity.data and using the ORM is the fastest
        activity_obj = model.Session.query(Activity).get(activity[u'id'])
        if u'resources' in activity_obj.data.get(u'package', {}):
            print(u'    activity has full dataset already recorded'
                  ' - no action')
            continue

        # get the dataset as it was at this revision:
        # call package_show just as we do in Activity::activity_stream_item(),
        # only with a revision_id (to get it as it was then)
        context = dict(
            get_context(),
            for_view=False,
            revision_id=activity_obj.revision_id,
            use_cache=False,  # avoid the cache (which would give us the
                              # latest revision)
        )
        try:
            assert activity_obj.revision_id, \
                u'Revision missing on the activity'
            dataset = logic.get_action(u'package_show')(
                context,
                {u'id': activity[u'object_id'], u'include_tracking': False})
        except Exception as exc:
            if isinstance(exc, logic.NotFound):
                error_msg = u'Revision missing'
            else:
                error_msg = str(exc)
            print(u'    Error: {}! Skipping this version '
                  '(revision_id={}, timestamp={})'
                  .format(error_msg, activity_obj.revision_id,
                          activity_obj.timestamp))
            errors[error_msg] += 1
            # We shouldn't leave the activity.data['package'] with missing
            # resources, extras & tags, which could cause the package_read
            # template to raise an exception, when user clicks "View this
            # version". Instead we pare it down to use a title, and forgo
            # viewing it.
            try:
                dataset = {u'title': activity_obj.data['package']['title']}
            except KeyError:
                # unlikely the package is not recorded in the activity, but
                # not impossible
                dataset = {u'title': u'unknown'}

        # get rid of revision_timestamp, which wouldn't be there if saved by
        # during Activity::activity_stream_item() - something to do with not
        # specifying revision_id.
        if u'revision_timestamp' in (dataset.get(u'organization') or {}):
            del dataset[u'organization'][u'revision_timestamp']
        for res in dataset.get(u'resources', []):
            if u'revision_timestamp' in res:
                del res[u'revision_timestamp']

        actor = model.Session.query(model.User).get(activity[u'user_id'])
        actor_name = actor.name if actor else activity[u'user_id']

        # add the data to the Activity, just as we do in
        # Activity::activity_stream_item()
        data = {
            u'package': dataset,
            u'actor': actor_name,
        }
        activity_obj.data = data
        # print '    {} dataset {}'.format(actor_name, repr(dataset))
    if model.Session.dirty:
        model.Session.commit()
        print(u'  saved')
    print(u'  This package\'s {} activities are migrated'.format(
        len(package_activity_stream)))


def wipe_activity_detail(delete_activity_detail):
    from ckan import model
    activity_detail_has_rows = \
        bool(model.Session.execute(
            u'SELECT count(*) '
            'FROM (SELECT * FROM "activity_detail" LIMIT 1) as t;')
            .fetchall()[0][0])
    if not activity_detail_has_rows:
        print(u'\nactivity_detail table is aleady emptied')
        return
    print(
        u'\nNow the migration is done, the history of datasets is now stored\n'
        'in the activity table. As a result, the contents of the\n'
        'activity_detail table will no longer be used after CKAN 2.8.x, and\n'
        'you can delete it to save space (this is safely done before or\n'
        'after the CKAN upgrade).'
    )
    if delete_activity_detail is None:
        delete_activity_detail = \
            input(u'Delete activity_detail table content? (y/n):')
    if delete_activity_detail.lower()[:1] != u'y':
        return
    from ckan import model
    model.Session.execute(u'DELETE FROM "activity_detail";')
    model.Session.commit()
    print(u'activity_detail deleted')


def print_errors(errors):
    if errors:
        print(u'Error summary:')
        for error_msg, count in errors.items():
            print(u'  {} {}'.format(count, error_msg))
        print(u'''
These errors are unusual - maybe a dataset was deleted, purged and then
recreated, or the revisions corrupted for some reason. These activity items now
don't have a package_dict recorded against them, which means that when a user
clicks "View this version" or "Changes" in the Activity Stream for it, it will
be missing. Hopefully that\'s acceptable enough to just ignore, because these
errors are really hard to fix.
            ''')


if __name__ == u'__main__':
    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument(u'-c', u'--config', help=u'CKAN config file (.ini)')
    parser.add_argument(u'--delete', choices=[u'yes', u'no'],
                        help=u'Delete activity detail')
    parser.add_argument(u'--dataset', help=u'just migrate this particular '
                        u'dataset - specify its name')
    args = parser.parse_args()
    assert args.config, u'You must supply a --config'
    print(u'Loading config')

    from ckan.plugins import plugin_loaded
    try:
        from ckan.cli import load_config
        from ckan.config.middleware import make_app
        make_app(load_config(args.config))
    except ImportError:
        # for CKAN 2.6 and earlier
        def load_config(config):  # type: ignore
            from ckan.lib.cli import CkanCommand
            cmd = CkanCommand(name=None)

            class Options(object):
                pass
            cmd.options = Options()
            cmd.options.config = config
            cmd._load_config()
            return
        load_config(args.config)

    if not plugin_loaded("activity"):
        print(
            "Please add the `activity` plugin to your `ckan.plugins` setting")
        sys.exit(1)

    if not args.dataset:
        migrate_all_datasets()
        wipe_activity_detail(delete_activity_detail=args.delete)
    else:
        errors: Any = defaultdict(int)
        with PackageDictizeMonkeyPatch():
            migrate_dataset(args.dataset, errors)
        print_errors(errors)
