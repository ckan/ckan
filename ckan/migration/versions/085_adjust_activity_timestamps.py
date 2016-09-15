# encoding: utf-8

import datetime


def upgrade(migrate_engine):
    u"""
    The script assumes that the current timestamp was
    recorded with the server's current set timezone
    """
    # choose a fixed date (within DST) so migration depends only on
    # server time zone not the current daylight savings state
    magic_timestamp = datetime.datetime(2016, 6, 20).toordinal()

    utc_date = datetime.datetime.utcfromtimestamp(magic_timestamp)
    local_date = datetime.datetime.fromtimestamp(magic_timestamp)

    if utc_date == local_date:
        return

    with migrate_engine.begin() as connection:
        sql = u"update activity set timestamp = timestamp + (%s - %s);"
        connection.execute(sql, utc_date, local_date)
