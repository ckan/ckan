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
    # removed feature
    op.drop_index('idx_rating_id', table_name='rating')
    op.drop_index('idx_rating_package_id', table_name='rating')
    op.drop_index('idx_rating_user_id', table_name='rating')
    op.drop_table('rating')
    # enforce package/resource relationship
    op.create_foreign_key(None, 'resource', 'package', ['package_id'], ['id'])
    # long-forgotten columns
    op.drop_column('resource', 'webstore_last_updated')
    op.drop_column('resource', 'webstore_url')
    # redundant indexes
    op.drop_index('idx_package_group_group_id', table_name='member')
    op.drop_index('idx_package_group_pkg_id', table_name='member')
    op.drop_index('idx_package_group_pkg_id_group_id', table_name='member')
    op.drop_index('idx_pkg_id', table_name='package')
    op.drop_index('idx_pkg_name', table_name='package')
    op.drop_index('idx_pkg_title', table_name='package')
    op.drop_index('idx_package_tag_tag_id', table_name='package_tag')
    op.drop_index('term', table_name='term_translation')


def downgrade():
    op.create_index('term', 'term_translation', ['term'], unique=False)
    op.create_index('idx_package_tag_tag_id', 'package_tag', ['tag_id'],
                    unique=False)
    op.create_index('idx_pkg_title', 'package', ['title'], unique=False)
    op.create_index('idx_pkg_name', 'package', ['name'], unique=False)
    op.create_index('idx_pkg_id', 'package', ['id'], unique=False)
    op.create_index('idx_package_group_pkg_id_group_id', 'member',
                    ['group_id', 'table_id'], unique=False)
    op.create_index('idx_package_group_pkg_id', 'member', ['table_id'],
                    unique=False)
    op.create_index('idx_package_group_group_id', 'member', ['group_id'],
                    unique=False)
    op.add_column('resource', sa.Column('webstore_url', sa.TEXT(),
                  autoincrement=False, nullable=True))
    op.add_column('resource', sa.Column('webstore_last_updated',
                  postgresql.TIMESTAMP(), autoincrement=False,
                  nullable=True))
    # Drop unnamed resource.package_id->package.id foreignkey constraint
    conn = op.get_bind()
    conn.execute(sa.text(
        '''
        DO $$
        DECLARE fk_name TEXT;
        BEGIN
            SELECT conname INTO fk_name FROM pg_constraint
            WHERE
            conrelid = 'resource'::regclass
            AND confrelid = 'package'::regclass
            AND contype = 'f'
            LIMIT 1;
            EXECUTE format('ALTER TABLE resource DROP CONSTRAINT %I', fk_name);
        END $$;
    '''
    ))
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
