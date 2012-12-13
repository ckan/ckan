from migrate import *

def upgrade(migrate_engine):

    update_schema = '''
BEGIN;

ALTER TABLE "user"
    ADD COLUMN sysadmin boolean DEFAULT FALSE;

ALTER TABLE package
    ADD COLUMN owner_org TEXT,
    ADD COLUMN private boolean DEFAULT FALSE;

ALTER TABLE package_revision
    ADD COLUMN owner_org TEXT,
    ADD COLUMN private boolean DEFAULT FALSE;


ALTER TABLE "group"
    ADD COLUMN is_organization boolean DEFAULT FALSE;

ALTER TABLE group_revision
    ADD COLUMN is_organization boolean DEFAULT FALSE;

COMMIT;

'''
    migrate_engine.execute(update_schema)


    # transform sysadmins
    import ckan.model as model
    sysadmins = model.Session.query(model.SystemRole).filter_by(role=model.Role.ADMIN)
    for sysadmin in sysadmins:

        user = model.User.get(sysadmin.user.id)
        user.sysadmin = True
        model.Session.commit()
