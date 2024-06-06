"""autogenerate sync models with migrations

Revision ID: 4a5e3465beb6
Revises: 9f33a0280c51
Create Date: 2024-06-06 20:32:06.936114

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4a5e3465beb6'
down_revision = '9f33a0280c51'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index('idx_rating_id', table_name='rating')
    op.drop_index('idx_rating_package_id', table_name='rating')
    op.drop_index('idx_rating_user_id', table_name='rating')
    op.drop_table('rating')
    op.create_foreign_key(None, 'resource', 'package', ['package_id'], ['id'])
    op.drop_column('resource', 'webstore_last_updated')
    op.drop_column('resource', 'webstore_url')


def downgrade():
    op.add_column('resource', sa.Column('webstore_url', sa.TEXT(),
                  autoincrement=False, nullable=True))
    op.add_column('resource', sa.Column('webstore_last_updated',
                  postgresql.TIMESTAMP(), autoincrement=False,
                  nullable=True))
    op.drop_constraint(None, 'resource', type_='foreignkey')
    op.create_table(
        'rating',
        sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('user_ip_address', sa.TEXT(), autoincrement=False,
                  nullable=True),
        sa.Column('rating', postgresql.DOUBLE_PRECISION(precision=53),
                  autoincrement=False, nullable=True),
        sa.Column('created', postgresql.TIMESTAMP(), autoincrement=False,
                  nullable=True),
        sa.Column('package_id', sa.TEXT(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['package_id'], ['package.id'],
                                name='rating_package_id_fkey'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'],
                                name='rating_user_id_fkey'),
        sa.PrimaryKeyConstraint('id', name='rating_pkey')
    )
    op.create_index('idx_rating_user_id', 'rating', ['user_id'], unique=False)
    op.create_index('idx_rating_package_id', 'rating', ['package_id'],
                    unique=False)
    op.create_index('idx_rating_id', 'rating', ['id'], unique=False)
