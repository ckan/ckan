# encoding: utf-8

import ckan.model


def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
        DROP TABLE "role_action";
        DROP TABLE "package_role";
        DROP TABLE "group_role";
        DROP TABLE "system_role";
        DROP TABLE "authorization_group_role";
        DROP TABLE "user_object_role";
        '''
    )
