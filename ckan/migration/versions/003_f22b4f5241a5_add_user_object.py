"""Add user object

Revision ID: f22b4f5241a5
Revises: 86fdd8c54775
Create Date: 2018-09-04 17:19:32.836747

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f22b4f5241a5'
down_revision = '86fdd8c54775'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user', sa.Column('id', sa.UnicodeText, primary_key=True),
        sa.Column('name', sa.UnicodeText), sa.Column('apikey', sa.UnicodeText)
    )

    op.drop_table('apikey')


def downgrade():
    op.create_table(
        'apikey',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('name', sa.UnicodeText()),
        sa.Column('key', sa.UnicodeText()),
    )
    op.drop_table('user')
