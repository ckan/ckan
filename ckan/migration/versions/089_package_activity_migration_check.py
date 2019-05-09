# encoding: utf-8

import sys

from ckan.migration.migrate_package_activity import num_unmigrated


def upgrade(migrate_engine):
    num_unmigrated_dataset_activities = num_unmigrated(migrate_engine)
    if num_unmigrated_dataset_activities:
        print('''
    NOTE:
    You have {num_unmigrated} unmigrated package activities.

    Once your CKAN upgrade is complete and CKAN server is running again, you
    should run the package activity migration, so that the Activity Stream can
    display the detailed history of datasets:

        python migrate_package_activity.py -c /etc/ckan/production.ini

    Once you've done that, the detailed history is visible in Activity Stream
    to *admins only*. However you are encouraged to make it available to the
    public, by setting this in production.ini:

        ckan.auth.public_activity_stream_detail = true

    More information about all of this is here:
    https://github.com/ckan/ckan/wiki/Migrate-package-activity
                '''.format(num_unmigrated=num_unmigrated_dataset_activities))
    else:
        # there are no unmigrated package activities
        are_any_datasets = bool(
            migrate_engine.execute(u'SELECT id FROM PACKAGE LIMIT 1').rowcount)
        # no need to tell the user if there are no datasets - this could just
        # be a fresh CKAN install
        if are_any_datasets:
            print(u'You have no unmigrated package activities - you do not '
                  'need to run migrate_package_activity.py.')
