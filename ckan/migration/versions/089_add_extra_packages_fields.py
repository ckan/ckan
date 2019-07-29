# encoding: utf-8


def upgrade(migrate_engine):
    migrate_engine.execute(
        '''
ALTER TABLE package
	ADD COLUMN associated_tasks text,
	ADD COLUMN collection_period text,
	ADD COLUMN geographical_area text,
	ADD COLUMN number_of_instances text,
	ADD COLUMN number_of_missing_values text,
	ADD COLUMN pkg_description text;


ALTER TABLE package_revision
	ADD COLUMN associated_tasks text,
	ADD COLUMN collection_period text,
	ADD COLUMN geographical_area text,
	ADD COLUMN number_of_instances text,
	ADD COLUMN number_of_missing_values text,
	ADD COLUMN pkg_description text;

CREATE TABLE public.access_request (
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
