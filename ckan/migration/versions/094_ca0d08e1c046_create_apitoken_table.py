"""Create ApiToken table

Revision ID: ca0d08e1c046
Revises: d4d9be9189fe
Create Date: 2020-01-13 10:34:40.606040

"""
from alembic import op
import sqlalchemy as sa
from ckan.model.api_token import _make_token

# revision identifiers, used by Alembic.
revision = 'ca0d08e1c046'
down_revision = u'd4d9be9189fe'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'api_token',
        sa.Column('id', sa.UnicodeText, primary_key=True, default=_make_token),
        sa.Column('user_id', sa.UnicodeText, sa.ForeignKey('user.id')),
        sa.Column('last_access', sa.DateTime, nullable=True),
    )


def downgrade():
    op.drop_table('api_token')
