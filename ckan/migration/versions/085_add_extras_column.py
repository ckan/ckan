def upgrade(migrate_engine):
    migrate_engine.execute(
        'ALTER TABLE "user" ADD extras JSON'
    )
