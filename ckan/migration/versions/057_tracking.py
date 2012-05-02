from sqlalchemy import *
from migrate import *

def upgrade(migrate_engine):
    migrate_engine.execute('''
        BEGIN;
        CREATE TABLE tracking_raw (
            user_key character varying(100) NOT NULL,
            url text NOT NULL,
            tracking_type character varying(10) NOT NULL,
            access_timestamp timestamp without time zone DEFAULT current_timestamp
        );
        CREATE INDEX tracking_raw_url ON tracking_raw(url);
        CREATE INDEX tracking_raw_user_key ON tracking_raw(user_key);
        CREATE INDEX tracking_raw_access_timestamp ON tracking_raw(access_timestamp);

        CREATE TABLE tracking_summary(
            url text NOT NULL,
            package_id text,
            tracking_type character varying(10) NOT NULL,
            count int NOT NULL,
            running_total int NOT NULL DEFAULT 0,
            recent_views int NOT NULL DEFAULT 0,
            tracking_date date
        );

        CREATE INDEX tracking_summary_url ON tracking_summary(url);
        CREATE INDEX tracking_summary_package_id ON tracking_summary(package_id);
        CREATE INDEX tracking_summary_date ON tracking_summary(tracking_date);

        COMMIT;
    '''
    )
