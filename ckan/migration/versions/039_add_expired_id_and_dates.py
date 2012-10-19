from migrate import *
import uuid
import datetime

def upgrade(migrate_engine):

    id = uuid.uuid4()

    make_missing_revisions = '''

-- make sure all tables have an entry in the revision_table

insert into revision values ('%(id)s' , '%(timestamp)s', 'admin', 'Admin: make sure every object has a row in a revision table', 'active');

insert into package_tag_revision (id,package_id,tag_id,revision_id,state,continuity_id) select id,package_id,tag_id, '%(id)s' ,state, id from package_tag where package_tag.id not in (select id from package_tag_revision);

insert into resource_revision (id,resource_group_id,url,format,description,position,revision_id,hash,state,extras,continuity_id) select id,resource_group_id,url,format,description,position, '%(id)s' ,hash,state,extras, id from resource where resource.id not in (select id from resource_revision);

insert into group_extra_revision (id,group_id,key,value,state,revision_id,continuity_id) select id,group_id,key,value,state, '%(id)s' , id from group_extra where group_extra.id not in (select id from group_extra_revision);

insert into resource_group_revision (id,package_id,label,sort_order,extras,state,revision_id,continuity_id) select id,package_id,label,sort_order,extras,state, '%(id)s', id from resource_group where resource_group.id not in (select id from resource_group_revision);

insert into package_extra_revision (id,package_id,key,value,revision_id,state,continuity_id) select id,package_id,key,value, '%(id)s',state, id from package_extra where package_extra.id not in (select id from package_extra_revision);

insert into package_relationship_revision (id,subject_package_id,object_package_id,type,comment,revision_id,state,continuity_id) select id,subject_package_id,object_package_id,type,comment, '%(id)s',state, id from package_relationship where package_relationship.id not in (select id from package_relationship_revision);
                           
insert into group_revision (id,name,title,description,created,state,revision_id,continuity_id) select id,name,title,description,created,state, '%(id)s', id from "group" where "group".id not in (select id from group_revision);

insert into package_revision (id,name,title,url,notes,license_id,revision_id,version,author,author_email,maintainer,maintainer_email,state,continuity_id) select id,name,title,url,notes,license_id, '%(id)s',version,author,author_email,maintainer,maintainer_email,state, id from package where package.id not in (select id from package_revision);

''' % dict(id=id, timestamp=datetime.datetime.utcnow().isoformat())


    update_schema = '''
ALTER TABLE package_revision
	ADD COLUMN expired_id text,
	ADD COLUMN revision_timestamp timestamp without time zone,
	ADD COLUMN expired_timestamp timestamp without time zone,
	ADD COLUMN current boolean;

ALTER TABLE package_extra_revision
	ADD COLUMN expired_id text,
	ADD COLUMN revision_timestamp timestamp without time zone,
	ADD COLUMN expired_timestamp timestamp without time zone,
	ADD COLUMN current boolean;

ALTER TABLE group_revision
	ADD COLUMN expired_id text,
	ADD COLUMN revision_timestamp timestamp without time zone,
	ADD COLUMN expired_timestamp timestamp without time zone,
	ADD COLUMN current boolean;

ALTER TABLE group_extra_revision
	ADD COLUMN expired_id text,
	ADD COLUMN revision_timestamp timestamp without time zone,
	ADD COLUMN expired_timestamp timestamp without time zone,
	ADD COLUMN current boolean;


ALTER TABLE package_group_revision
	ADD COLUMN expired_id text,
	ADD COLUMN revision_timestamp timestamp without time zone,
	ADD COLUMN expired_timestamp timestamp without time zone,
	ADD COLUMN current boolean;

ALTER TABLE package_tag_revision
	ADD COLUMN expired_id text,
	ADD COLUMN revision_timestamp timestamp without time zone,
	ADD COLUMN expired_timestamp timestamp without time zone,
	ADD COLUMN current boolean;

ALTER TABLE resource_group_revision
	ADD COLUMN expired_id text,
	ADD COLUMN revision_timestamp timestamp without time zone,
	ADD COLUMN expired_timestamp timestamp without time zone,
	ADD COLUMN current boolean;

ALTER TABLE resource_revision
	ADD COLUMN expired_id text,
	ADD COLUMN revision_timestamp timestamp without time zone,
	ADD COLUMN expired_timestamp timestamp without time zone,
	ADD COLUMN current boolean;

ALTER TABLE package_relationship_revision 
	ADD COLUMN expired_id text,
	ADD COLUMN revision_timestamp timestamp without time zone,
	ADD COLUMN expired_timestamp timestamp without time zone,
	ADD COLUMN current boolean;

ALTER TABLE revision
	ADD COLUMN approved_timestamp timestamp without time zone;

create table tmp_expired_id(id text, revision_id text, revision_timestamp timestamp, expired_timestamp timestamp, expired_id text);
create index id_exp on tmp_expired_id(id, revision_id);

--package revision
truncate tmp_expired_id;
insert into tmp_expired_id select pr.id, revision_id, timestamp, lead(timestamp, 1, '9999-12-31') over (partition by pr.id order by timestamp), lead(pr.revision_id) over (partition by pr.id order by timestamp) from package_revision pr join revision r on pr.revision_id = r.id;
update package_revision pr set revision_timestamp = (select revision_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_timestamp = (select expired_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_id = (select expired_id from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id);
update package_revision set current = '1' where expired_timestamp = '9999-12-31';

create index idx_package_period on package_revision(revision_timestamp, expired_timestamp, id);
create index idx_package_current on package_revision(current);

--package extra revision 
truncate tmp_expired_id;
insert into tmp_expired_id select pr.id, revision_id, timestamp, lead(timestamp, 1, '9999-12-31') over (partition by pr.id order by timestamp), lead(pr.revision_id) over (partition by pr.id order by timestamp) from package_extra_revision pr join revision r on pr.revision_id = r.id;
update package_extra_revision pr set revision_timestamp = (select revision_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_timestamp = (select expired_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_id = (select expired_id from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id);
update package_extra_revision set current = '1' where expired_timestamp = '9999-12-31';

create index idx_package_extra_period on package_extra_revision(revision_timestamp, expired_timestamp, id);
create index idx_package_extra_period_package on package_extra_revision(revision_timestamp, expired_timestamp, package_id);
create index idx_package_extra_current on package_extra_revision(current);

--package group revision
truncate tmp_expired_id;
insert into tmp_expired_id select pr.id, revision_id, timestamp, lead(timestamp, 1, '9999-12-31') over (partition by pr.id order by timestamp), lead(pr.revision_id) over (partition by pr.id order by timestamp) from package_group_revision pr join revision r on pr.revision_id = r.id;
update package_group_revision pr set revision_timestamp = (select revision_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_timestamp = (select expired_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_id = (select expired_id from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id);
update package_group_revision set current = '1' where expired_timestamp = '9999-12-31';

create index idx_package_group_period_package_group on package_group_revision(revision_timestamp, expired_timestamp, package_id, group_id);
create index idx_package_group_current on package_group_revision(current);


-- package_tags
truncate tmp_expired_id;
insert into tmp_expired_id select pr.id, revision_id, timestamp, lead(timestamp, 1, '9999-12-31') over (partition by pr.id order by timestamp), lead(pr.revision_id) over (partition by pr.id order by timestamp) from package_tag_revision pr join revision r on pr.revision_id = r.id;
update package_tag_revision pr set revision_timestamp = (select revision_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_timestamp = (select expired_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_id = (select expired_id from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id);
update package_tag_revision set current = '1' where expired_timestamp = '9999-12-31';

create index idx_period_package_tag on package_tag_revision(revision_timestamp, expired_timestamp, package_id, tag_id);
create index idx_package_tag_current on package_tag_revision(current);

-- package relationship
truncate tmp_expired_id;
insert into tmp_expired_id select pr.id, revision_id, timestamp, lead(timestamp, 1, '9999-12-31') over (partition by pr.id order by timestamp), lead(pr.revision_id) over (partition by pr.id order by timestamp) from package_relationship_revision pr join revision r on pr.revision_id = r.id;
update package_relationship_revision pr set revision_timestamp = (select revision_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_timestamp = (select expired_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_id = (select expired_id from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id);
update package_relationship_revision set current = '1' where expired_timestamp = '9999-12-31';

create index idx_period_package_relationship on package_relationship_revision(revision_timestamp, expired_timestamp, object_package_id, subject_package_id);
create index idx_package_relationship_current on package_relationship_revision(current);

-- resource revision
truncate tmp_expired_id;
insert into tmp_expired_id select pr.id, revision_id, timestamp, lead(timestamp, 1, '9999-12-31') over (partition by pr.id order by timestamp), lead(pr.revision_id) over (partition by pr.id order by timestamp) from resource_revision pr join revision r on pr.revision_id = r.id;
update resource_revision pr set revision_timestamp = (select revision_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_timestamp = (select expired_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_id = (select expired_id from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id);
update resource_revision set current = '1' where expired_timestamp = '9999-12-31';

create index idx_resource_period on resource_revision(revision_timestamp, expired_timestamp, id);
create index idx_resource_period_resource_group on resource_revision(revision_timestamp, expired_timestamp, resource_group_id);
create index idx_resource_current on resource_revision(current);

-- resource group revision;
truncate tmp_expired_id;
insert into tmp_expired_id select pr.id, revision_id, timestamp, lead(timestamp, 1, '9999-12-31') over (partition by pr.id order by timestamp), lead(pr.revision_id) over (partition by pr.id order by timestamp) from resource_group_revision pr join revision r on pr.revision_id = r.id;
update resource_group_revision pr set revision_timestamp = (select revision_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_timestamp = (select expired_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_id = (select expired_id from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id);
update resource_group_revision set current = '1' where expired_timestamp = '9999-12-31';

create index idx_resource_group_period on resource_group_revision(revision_timestamp, expired_timestamp, id);
create index idx_resource_group_period_package on resource_group_revision(revision_timestamp, expired_timestamp, package_id);
create index idx_resource_group_current on resource_group_revision(current);

--group revision;
truncate tmp_expired_id;
insert into tmp_expired_id select pr.id, revision_id, timestamp, lead(timestamp, 1, '9999-12-31') over (partition by pr.id order by timestamp), lead(pr.revision_id) over (partition by pr.id order by timestamp) from group_revision pr join revision r on pr.revision_id = r.id;
update group_revision pr set revision_timestamp = (select revision_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_timestamp = (select expired_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_id = (select expired_id from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id);
update group_revision set current = '1' where expired_timestamp = '9999-12-31';

create index idx_group_period on group_revision(revision_timestamp, expired_timestamp, id);
create index idx_group_current on group_revision(current);

--group extra revision 
truncate tmp_expired_id;
insert into tmp_expired_id select pr.id, revision_id, timestamp, lead(timestamp, 1, '9999-12-31') over (partition by pr.id order by timestamp), lead(pr.revision_id) over (partition by pr.id order by timestamp) from group_extra_revision pr join revision r on pr.revision_id = r.id;
update group_extra_revision pr set revision_timestamp = (select revision_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_timestamp = (select expired_timestamp from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id),
                               expired_id = (select expired_id from tmp_expired_id tmp where tmp.revision_id = pr.revision_id and tmp.id = pr.id);
update group_extra_revision set current = '1' where expired_timestamp = '9999-12-31';

create index idx_group_extra_period on group_extra_revision(revision_timestamp, expired_timestamp, id);
create index idx_group_extra_period_group on group_extra_revision(revision_timestamp, expired_timestamp, group_id);
create index idx_group_extra_current on group_extra_revision(current);

drop table tmp_expired_id;

-- change state of revision tables

update revision set approved_timestamp = timestamp;
'''
    
    migrate_engine.execute('begin;  ' + make_missing_revisions + update_schema + ' commit;')
    
    for table in ['package', 'resource', 'resource_group', 'package_extra', 
                  'package_tag', 'package_relationship', 'group', 'group_extra']:
        count = migrate_engine.execute('''select count(*) from "%s"''' % table).first()[0]
        revision_expired_id_count = migrate_engine.execute('''select count(*) from %s_revision where %s_revision.expired_id is null''' % (table, table)).first()[0]
        revision_expired_data_count = migrate_engine.execute('''select count(*) from %s_revision where %s_revision.expired_timestamp = '9999-12-31' ''' % (table, table)).first()[0]
        revision_current = migrate_engine.execute('''select count(*) from %s_revision where %s_revision.current = '1' ''' % (table, table)).first()[0]
        assert count == revision_expired_id_count
        assert count == revision_expired_data_count
        assert count == revision_current

    
