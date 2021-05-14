# encoding: utf-8
"""package activity migration check

Revision ID: 23c92480926e
Revises: 3537d5420e0e
Create Date: 2019-05-09 13:39:17.486611

"""
from __future__ import print_function

from alembic import op

from ckan.migration.migrate_package_activity import num_unmigrated

# revision identifiers, used by Alembic.
revision = u'23c92480926e'
down_revision = u'3537d5420e0e'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    num_unmigrated_dataset_activities = num_unmigrated(conn)

    if num_unmigrated_dataset_activities:
        print(
            u'''
NOTE:
You have {num_unmigrated} unmigrated package activities.

Once your CKAN upgrade is complete and CKAN server is running again, you
should run the package activity migration, so that the Activity Stream can
display the detailed history of datasets:

  python ckan/migration/migrate_package_activity.py -c /etc/ckan/production.ini

Once you've done that, the detailed history is visible in Activity Stream
to *admins only*. However you are encouraged to make it available to the
public, by setting this in production.ini:

  ckan.auth.public_activity_stream_detail = true

More information about all of this is here:
https://github.com/ckan/ckan/wiki/Migrate-package-activity
            '''.format(
                num_unmigrated=num_unmigrated_dataset_activities
            )
        )
    else:
        # there are no unmigrated package activities
        are_any_datasets = bool(
            conn.execute(u'SELECT id FROM PACKAGE LIMIT 1').rowcount
        )
        # no need to tell the user if there are no datasets - this could just
        # be a fresh CKAN install
        if are_any_datasets:
            print(
                u'You have no unmigrated package activities - you do not '
                'need to run migrate_package_activity.py.'
            )


def downgrade():
    pass
