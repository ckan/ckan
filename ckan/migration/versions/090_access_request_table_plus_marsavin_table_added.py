# encoding: utf-8


def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS public.package_marsavin (
    id uuid DEFAULT uuid_generate_v4 (),
    package_id text,
    associated_tasks text,
    collection_period text,
    geographical_area text,
    number_of_instances text,
    number_of_missing_values text,
    pkg_description text
);

ALTER TABLE public.package_marsavin OWNER TO ckan;

CREATE TABLE IF NOT EXISTS public.access_request (
    id text NOT NULL,
    user_ip_address text,
    user_email text,
    maintainer_name text,
    maintainer_email text,
    user_msg text,
    created timestamp without time zone
);


ALTER TABLE public.access_request OWNER TO ckan;
        '''
    )
