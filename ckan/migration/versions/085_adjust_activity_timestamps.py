# encoding: utf-8

import pytz
import tzlocal
import logging

log = logging.getLogger(__name__)

def upgrade(migrate_engine):
"""
The script assumes that the current timestamp was recorded with the server's current set timezone
"""
    local_tz = tzlocal.get_localzone()

    with migrate_engine.begin() as connection:
        sql = "select id, timestamp from activity"
        results = connection.execute(sql)

        log.info("Adjusting Activity timestamp, server's localtime zone: {tz}".format(tz=local_tz))

        for row in results:
            id, timestamp = row

            timestamp = timestamp.replace(tzinfo=local_tz)
            to_utc = timestamp.astimezone(pytz.utc)
            to_utc = to_utc.replace(tzinfo=None)

            update_sql = "update activity set timestamp = %s where id = %s"

            connection.execute(update_sql, to_utc, id)

            log.info("""Adjusting Activity timestamp to UTC for {id}: {old_ts} --> {new_ts}
            """.format(id=id, old_ts=timestamp, new_ts=to_utc))
