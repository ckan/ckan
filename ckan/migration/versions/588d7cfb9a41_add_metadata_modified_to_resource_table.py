"""Add metadata_modified filed to Resource

Revision ID: 588d7cfb9a41
Revises: d4d9be9189fe
Create Date: 2020-02-24 09:24:22.405413

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '588d7cfb9a41'
down_revision = 'd4d9be9189fe'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('resource',
        sa.Column('metadata_modified', sa.DateTime(), nullable=True)
        )


def downgrade():
    op.drop_column('resource', 'metadata_modified')
