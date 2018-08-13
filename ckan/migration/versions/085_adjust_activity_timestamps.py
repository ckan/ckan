# encoding: utf-8

import datetime


def upgrade(migrate_engine):
    u"""
    The script assumes that the current timestamp was
    recorded with the server's current set timezone
    """
    utc_now = datetime.datetime.utcnow()
    local_now = datetime.datetime.now()

    with migrate_engine.begin() as connection:
        sql = u"update activity set timestamp = timestamp + (%s - %s);"
        connection.execute(sql, utc_now, local_now)
