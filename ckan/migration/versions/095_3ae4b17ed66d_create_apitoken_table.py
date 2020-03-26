"""Create ApiToken table

Revision ID: 3ae4b17ed66d
Revises: 588d7cfb9a41
Create Date: 2020-03-26 18:50:47.502458

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "3ae4b17ed66d"
down_revision = "588d7cfb9a41"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        u"api_token",
        sa.Column(u"id", sa.UnicodeText, primary_key=True),
        sa.Column(u"name", sa.UnicodeText),
        sa.Column(u"user_id", sa.UnicodeText, sa.ForeignKey(u"user.id")),
        sa.Column(
            u"created_at", sa.DateTime,
            server_default=sa.func.current_timestamp()
        ),
        sa.Column(u"last_access", sa.DateTime, nullable=True),
    )


def downgrade():
    op.drop_table(u"api_token")
