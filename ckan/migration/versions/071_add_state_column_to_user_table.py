import ckan.model.core


def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
        ALTER TABLE "user" ADD COLUMN "state" text NOT NULL DEFAULT '%s'
        ''' % ckan.model.core.State.ACTIVE
    )
