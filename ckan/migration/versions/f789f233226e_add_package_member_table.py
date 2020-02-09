"""Add package_member_table

Revision ID: f789f233226e
Revises: d4d9be9189fe
Create Date: 2020-02-09 01:15:12.158897

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f789f233226e'
down_revision = u'd4d9be9189fe'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'package_member',
        sa.Column('id', sa.UnicodeText(), nullable=False),
        sa.Column('package_id', sa.UnicodeText(), nullable=True),
        sa.Column('user_id', sa.UnicodeText(), nullable=True),
        sa.Column('capacity', sa.UnicodeText(), nullable=False),
        sa.Column('modified', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['package_id'], ['package.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('package_member')
