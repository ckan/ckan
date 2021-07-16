# encoding: utf-8

"""Add package_member_table

Revision ID: f789f233226e
Revises: 19ddad52b500
Create Date: 2020-02-09 01:15:12.158897

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f789f233226e'
down_revision = '19ddad52b500'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'package_member',
        sa.Column('package_id', sa.UnicodeText()),
        sa.Column('user_id', sa.UnicodeText()),
        sa.Column('capacity', sa.UnicodeText(), nullable=False),
        sa.Column('modified', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['package_id'], ['package.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint(
            'package_id', 'user_id', name='package_member_pkey')
    )


def downgrade():
    op.drop_table('package_member')
