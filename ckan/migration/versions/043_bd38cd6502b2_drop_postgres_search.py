"""043 Drop postgres search

Revision ID: bd38cd6502b2
Revises: da65e2877034
Create Date: 2018-09-04 18:49:03.717678

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'bd38cd6502b2'
down_revision = 'da65e2877034'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('package_search')


def downgrade():
    op.create_table(
        'package_search',
        sa.Column(
            'package_id',
            sa.UnicodeText,
            sa.ForeignKey('package.id'),
            primary_key=True
        ), sa.Column('search_vector', sa.dialects.postgresql.TSVECTOR)
    )
