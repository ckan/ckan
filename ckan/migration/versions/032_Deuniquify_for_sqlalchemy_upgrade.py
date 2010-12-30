from sqlalchemy import *
from migrate import *
from migrate.changeset.constraint import UniqueConstraint

def upgrade():
    # Upgrade operations go here. Don't create your own engine; use the engine
    # named 'migrate_engine' imported from migrate.
    user_sql = 'ALTER TABLE "group" DROP CONSTRAINT group_name_key'
    migrate_engine.execute(user_sql)
    user_sql = 'ALTER TABLE "package" DROP CONSTRAINT package_name_key'
    migrate_engine.execute(user_sql)
    user_sql = 'ALTER TABLE "tag DROP CONSTRAINT tag_name_key'
    migrate_engine.execute(user_sql)

def downgrade():
    # Operations to reverse the above upgrade go here.
    user_sql = 'ALTER TABLE "group" ADD CONSTRAINT group_name_key UNIQUE(name)'
    migrate_engine.execute(user_sql)
    user_sql = 'ALTER TABLE "package" ADD CONSTRAINT package_name_key UNIQUE(name)'
    migrate_engine.execute(user_sql)
    user_sql = 'ALTER TABLE "tag ADD CONSTRAINT tag_name_key UNIQUE(name)'
    migrate_engine.execute(user_sql)
