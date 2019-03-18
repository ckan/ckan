# encoding: utf-8

import sys

from ckan.migration.migrate_package_activity import num_unmigrated


def upgrade(migrate_engine):
    num_unmigrated_dataset_activities = num_unmigrated(migrate_engine)
    if num_unmigrated_dataset_activities:
        print('''
    !!! ERROR !!!
    You have {num_unmigrated} unmigrated package activities.

    You cannot do this db upgrade until you completed the package activity
    migration first. Full instructions for this situation are here:

    https://github.com/ckan/ckan/wiki/Migrate-package-activity#if-you-tried-to-upgrade-from-ckan-28-or-earlier-to-ckan-29-and-it-stopped-at-paster-db-upgrade
                '''.format(num_unmigrated=num_unmigrated_dataset_activities))
        sys.exit(1)
