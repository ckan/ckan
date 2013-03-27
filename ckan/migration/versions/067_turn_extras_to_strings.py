import json

def upgrade(migrate_engine):

    with migrate_engine.begin() as connection:
        tables = 'package_extra group_extra'
        revision_tables = 'package_extra_revision group_extra_revision'

        for table in tables.split():
            sql = """select id, value from {table} where substr(value,1,1) = '"' """.format(table=table)
            results = connection.execute(sql)
            for result in results:
                id, value = result
                update_sql = 'update {table} set value = %s where id = %s'
                connection.execute(update_sql.format(table=table),
                                   json.loads(value), id)

        for table in revision_tables.split():
            sql = """select id, revision_id, value from {table} where substr(value,1,1) = '"' """.format(table=table)

            results = connection.execute(sql)
            for result in results:
                id, revision_id, value = result
                update_sql = 'update {table} set value = %s where id = %s and revision_id = %s'
                connection.execute(update_sql.format(table=table),
                                   json.loads(value), id, revision_id)


