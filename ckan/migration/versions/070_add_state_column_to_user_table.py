import vdm.sqlalchemy


def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
        ALTER TABLE "user" ADD COLUMN "state" text NOT NULL DEFAULT '%s'
        ''' % vdm.sqlalchemy.State.ACTIVE
    )


def downgrade(migrate_engine):
    migrate_engine.exeecute(
        '''
        ALTER TABLE "user" DROP COLUMN "state"
        '''
    )
