"""042 User revision indexes

Revision ID: da65e2877034
Revises: 6817d4e3bdc3
Create Date: 2018-09-04 18:49:03.380103

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'da65e2877034'
down_revision = '6817d4e3bdc3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('idx_revision_author', 'revision', ['author'])
    op.create_index('idx_openid', 'user', ['openid'])
    op.create_index(
        'idx_user_name_index', 'user', [
            sa.text(
                '''(CASE WHEN ("user".fullname IS NULL OR "user".fullname = '') THEN "user".name ELSE "user".fullname END)'''
            )
        ]
    )


def downgrade():
    op.drop_index('idx_user_name_index', 'user')
    op.drop_index('idx_openid', 'user')
    op.drop_index('idx_revision_author', 'revision')
