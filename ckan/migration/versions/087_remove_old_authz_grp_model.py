# encoding: utf-8

import ckan.model


def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
        DROP TABLE IF EXISTS "authorization_group_user";
	DROP TABLE IF EXISTS "authorization_group";
        '''
    )
