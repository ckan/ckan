# encoding: utf-8

from sqlalchemy import *
from sqlalchemy.sql import select, and_
from migrate import *
import logging

log = logging.getLogger(__name__)

def upgrade(migrate_engine):
    '''#1066 Change Visitor role on System from "reader" to "anon_editor".'''
    metadata = MetaData(migrate_engine)

    # get visitor ID
    user = Table('user', metadata, autoload=True)
    s = select([user.c.id, user.c.name],
               user.c.name == u'visitor')
    results = migrate_engine.execute(s).fetchall()
    if len(results) == 0:
        log.debug('No visitor on the system - obviously init hasn\'t been run yet' \
                  'and that will init visitor to an anon_editor')
        return

    visitor_id, visitor_name = results[0]

    # find visitor role as reader on system
    uor = Table('user_object_role', metadata, autoload=True)
    visitor_system_condition = and_(uor.c.context == u'System',
                                    uor.c.user_id == visitor_id)
    s = select([uor.c.context, uor.c.user_id, uor.c.role],
               visitor_system_condition)
    results = migrate_engine.execute(s).fetchall()
    if len(results) != 1:
        log.warn('Could not find a Right for a Visitor on the System')
        return
    context, user_id, role = results[0]
    if role != 'reader':
        log.info('Visitor right for the System is not "reader", so not upgrading it to anon_editor.')
        return

    # change visitor role to anon_editor
    log.info('Visitor is a "reader" on the System, so upgrading it to "anon_editor".')
    sql = uor.update().where(visitor_system_condition).\
          values(role=u'anon_editor')
    migrate_engine.execute(sql)


def downgrade(migrate_engine):
    raise NotImplementedError()

