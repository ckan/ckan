# encoding: utf-8
"""085 Adjust activity timestamps

Revision ID: f9bf3d5c4b4d
Revises: d85ce5783688
Create Date: 2018-09-04 18:49:18.307804

"""
import datetime
from alembic import op, context
from sqlalchemy import text
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = 'f9bf3d5c4b4d'
down_revision = 'd85ce5783688'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    magic_timestamp = datetime.datetime(2016, 6, 20).toordinal()

    utc_date = datetime.datetime.utcfromtimestamp(magic_timestamp)
    local_date = datetime.datetime.fromtimestamp(magic_timestamp)

    if utc_date == local_date:
        return

    sql = text("update activity set timestamp = timestamp + (:utc - :local);")

    if context.is_offline_mode():
        execute = context.execute
    else:
        connection = op.get_bind()
        execute = connection.execute

    execute(sql, {"utc": utc_date, "local": local_date})


def downgrade():
    magic_timestamp = datetime.datetime(2016, 6, 20).toordinal()

    utc_date = datetime.datetime.utcfromtimestamp(magic_timestamp)
    local_date = datetime.datetime.fromtimestamp(magic_timestamp)

    if utc_date == local_date:
        return

    sql = text("update activity set timestamp = timestamp - (:utc - :local);")

    if context.is_offline_mode():
        execute = context.execute
    else:
        connection = op.get_bind()
        execute = connection.execute

    execute(sql, {"utc": utc_date, "local": local_date})
