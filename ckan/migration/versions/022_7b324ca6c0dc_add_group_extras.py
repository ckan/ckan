# encoding: utf-8
"""022 Add group_extras

Revision ID: 7b324ca6c0dc
Revises: c7743043ed99
Create Date: 2018-09-04 18:48:56.635671

"""
from alembic import op
import sqlalchemy as sa
from ckan.migration import skip_based_on_legacy_engine_version
# revision identifiers, used by Alembic.
revision = '7b324ca6c0dc'
down_revision = '765143af2ba3'
branch_labels = None
depends_on = None


def upgrade():
    if skip_based_on_legacy_engine_version(op, __name__):
        return
    op.create_table(
        'group_extra',
        sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('group_id', sa.UnicodeText, sa.ForeignKey('group.id')),
        sa.Column('key', sa.UnicodeText),
        sa.Column('value', sa.UnicodeText),
    )


def downgrade():
    op.drop_table('group_extra')
