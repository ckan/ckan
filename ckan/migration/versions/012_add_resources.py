from sqlalchemy import *
from migrate import *
import migrate.changeset
import vdm.sqlalchemy

metadata = MetaData(migrate_engine)

package_table = Table('package', metadata, autoload=True)
package_resource_table = Table(
    'package_resource', metadata,
    Column('id', Integer, primary_key=True),
    Column('package_id', Integer, ForeignKey('package.id')),
    Column('url', UnicodeText, nullable=False),
    Column('format', UnicodeText),
    Column('description', UnicodeText),
    Column('position', Integer),
    )

vdm.sqlalchemy.make_table_stateful(package_resource_table)
resource_revision_table = vdm.sqlalchemy.make_table_revisioned(package_resource_table)

def upgrade():
    package_resource_table.create()
    resource_revision_table.create()
    
    # move download_urls across to resources
    engine = migrate_engine
    select_sql = select([package_table])
    for pkg in engine.execute(select_sql):
        download_url = pkg['download_url']
        if download_url:
            res_values = {'package_id':pkg.id,
                          'url':download_url,
                          'format':'',
                          'description':'',
                          'position':0,
                          'state_id':1,                      
                          }
            insert_sql = package_resource_table.insert(values=res_values)
            engine.execute(insert_sql)

    package_table.c.download_url.drop()

def downgrade():
    raise NotImplementedError()
