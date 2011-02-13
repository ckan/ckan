from sqlalchemy import *
from migrate import *
import migrate.changeset
import vdm.sqlalchemy



def upgrade(migrate_engine):
    metadata = MetaData()
    metadata.bind = migrate_engine

    package_table = Table('package', metadata, autoload=True)
    package_revision_table = Table('package_revision', metadata, autoload=True)
    package_resource_table = Table('package_resource', metadata,
        Column('id', Integer, primary_key=True),
        Column('package_id', Integer, ForeignKey('package.id')),
        Column('url', UnicodeText, nullable=False),
        Column('format', UnicodeText),
        Column('description', UnicodeText),
        Column('position', Integer),
        Column('state_id', Integer),
        Column('revision_id', UnicodeText, ForeignKey('revision.id'))
        )

    package_resource_revision_table = Table('package_resource_revision', metadata,
        Column('id', Integer, primary_key=True),
        Column('package_id', Integer, ForeignKey('package.id')),
        Column('url', UnicodeText, nullable=False),
        Column('format', UnicodeText),
        Column('description', UnicodeText),
        Column('position', Integer),
        Column('state_id', Integer),
        Column('revision_id', UnicodeText, ForeignKey('revision.id'), primary_key=True),
        Column('continuity_id', Integer, ForeignKey('package_resource.id'))
        )

    
    package_resource_table.create()
    package_resource_revision_table.create()
    
    # Move download_urls across to resources
    # NB: strictly we should check each package_revision to check whether
    # download_url changed (and if only change) and then create
    # package_resource_revision for each such revision (and delete every
    # package_revision where only change is download_url)
    # However, we adopt a cruder approach in which we just create 
    engine = migrate_engine
    select_sql = select([package_table])
    for pkg in engine.execute(select_sql):
        download_url = pkg['download_url']
        if download_url:
            # what about revision_id?
            res_values = {'package_id':pkg.id,
                          'url':download_url,
                          'format':u'',
                          'description':u'',
                          'position':0,
                          'state_id':1,
                          'revision_id': pkg.revision_id,
                          }
            insert_sql = package_resource_table.insert(values=res_values)
            engine.execute(insert_sql)
            # get id of just inserted resource
            getid_sql = select([package_resource_table]).where(
                    package_resource_table.c.package_id==pkg.id)
            resource_id = getid_sql.execute().fetchone().id
            # now we need to update revision table ...
            res_rev_values = dict(res_values)
            res_rev_values['continuity_id'] = resource_id
            res_rev_values['id'] = resource_id
            insert_sql = package_resource_revision_table.insert(values=res_rev_values)
            engine.execute(insert_sql)

    package_table.c.download_url.drop()
    package_revision_table.c.download_url.drop()

def downgrade(migrate_engine):
    raise NotImplementedError()
