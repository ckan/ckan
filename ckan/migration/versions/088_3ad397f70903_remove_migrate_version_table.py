# encoding: utf-8
"""Remove migrate version table

Revision ID: 3ad397f70903
Revises: ff1b303cab77
Create Date: 2018-09-18 18:16:50.083513

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '3ad397f70903'
down_revision = 'ff1b303cab77'
branch_labels = None
depends_on = None


def upgrade():
    '''Drop version table, created by sqlalchemy-migrate.

    There is a chance, that we are initializing a new instance and
    there is no `migrate_version` table, so DO NOT remove `IF EXISTS`
    clause.
    '''
    op.execute('DROP TABLE IF EXISTS migrate_version')


def downgrade():
    '''We aren't going to recreate `migrate_version` here.

    There is a chance, that this table even never was created for
    target database. This migration tries to seamlessly upgrade
    existing instance from usage of sqlalchemy-migrate to alembic. And
    we don't want to downgrade to sqlalchemy-migrate back again.
    '''
    pass
