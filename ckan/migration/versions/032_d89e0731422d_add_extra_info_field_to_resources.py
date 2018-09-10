"""032 Add extra info field_to_resources

Revision ID: d89e0731422d
Revises: 1b05245167d6
Create Date: 2018-09-04 18:49:00.003141

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd89e0731422d'
down_revision = '1b05245167d6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('package_resource', sa.Column('extras', sa.UnicodeText))
    op.add_column(
        'package_resource_revision', sa.Column('extras', sa.UnicodeText)
    )


def downgrade():
    op.drop_column('package_resource', 'extras')
    op.drop_column('package_resource_revision', 'extras')
