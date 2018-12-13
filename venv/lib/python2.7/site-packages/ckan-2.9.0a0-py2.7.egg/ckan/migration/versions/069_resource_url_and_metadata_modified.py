# encoding: utf-8


def upgrade(migrate_engine):

    update_schema = '''
BEGIN;

ALTER TABLE resource
    ADD COLUMN url_type TEXT;

ALTER TABLE resource_revision
    ADD COLUMN url_type TEXT;

ALTER TABLE package
    ADD COLUMN metadata_modified timestamp without time zone,
    ADD COLUMN creator_user_id TEXT;

ALTER TABLE package_revision
    ADD COLUMN metadata_modified timestamp without time zone,
    ADD COLUMN creator_user_id TEXT;


-- package
update package
set metadata_modified = greatest(max_revision, metadata_modified)
from
(
select id package_id, max(revision_timestamp) max_revision
from package_revision group by id
) max_rev
where max_rev.package_id = package.id;

-- package tag
update package
set metadata_modified = greatest(max_revision, metadata_modified)
from (select package_id, max(revision_timestamp) max_revision
from package_tag_revision group by package_id) max_rev
where max_rev.package_id = package.id;

-- package extra
update package
set metadata_modified = greatest(max_revision, metadata_modified)
from (select package_id, max(revision_timestamp) max_revision
from package_extra_revision group by package_id) max_rev
where max_rev.package_id = package.id;

--resource

update package
set metadata_modified = greatest(max_revision, metadata_modified)
from (select package_id, max(revision_timestamp) max_revision
      from resource_revision
      join resource_group
      on resource_revision.resource_group_id = resource_group.id
      group by package_id) max_rev
where max_rev.package_id = package.id
;

-- add as many creators as we can find
update package set creator_user_id = user_id from
(select
    package_revision.id as package_id,
    "user".id as user_id, revision_timestamp,
    row_number() over
    (partition by package_revision.id order by revision_timestamp) num
from package_revision
    join revision on package_revision.revision_id = revision.id join "user"
    on (revision.author = "user".name
        or revision.author = "user".openid)) first_rev
    where package_id = id and num = 1;

COMMIT;

'''
    migrate_engine.execute(update_schema)
