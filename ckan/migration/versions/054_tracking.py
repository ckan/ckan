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

        CREATE TABLE tracking_summary(
            url text NOT NULL,
            package_id text,
            tracking_type character varying(10) NOT NULL,
            count int NOT NULL,
            running_total int NOT NULL DEFAULT 0,
            date date
        );

        CREATE INDEX tracking_summary_url ON tracking_summary(url);
        CREATE INDEX tracking_summary_package_id ON tracking_summary(package_id);
        CREATE INDEX tracking_summary_date ON tracking_summary(date);

        COMMIT;
    '''
    )
