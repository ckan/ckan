'''Generic sqlalchemy code (not specifically related to vdm).
'''
import sqlalchemy

class SQLAlchemyMixin(object):
    def __init__(self, **kw):
        for k, v in kw.iteritems():
            setattr(self, k, v)

    def __str__(self):
        return self.__unicode__().encode('utf8')

    def __unicode__(self):
        repr = u'<%s' % self.__class__.__name__
        table = sqlalchemy.orm.class_mapper(self.__class__).mapped_table
        for col in table.c:
            repr += u' %s=%s' % (col.name, getattr(self, col.name))
        repr += '>'
        return repr

    def __repr__(self):
        return self.__str__()

## --------------------------------------------------------
## Table Helpers

def copy_column(name, src_table, dest_table):
    '''
    Note you cannot just copy columns standalone e.g.

        col = table.c['xyz']
        col.copy()

    This will only copy basic info while more complex properties (such as fks,
    constraints) to work must be set when the Column has a parent table.

    TODO: stuff other than fks (e.g. constraints such as uniqueness)
    '''
    col = src_table.c[name]
    if col.unique == True:
        # don't copy across unique constraints, as different versions
        # of an object may have identical column values
        col.unique = False
    dest_table.append_column(col.copy())
    # only get it once we have a parent table
    newcol = dest_table.c[name]
    if len(col.foreign_keys) > 0:
        for fk in col.foreign_keys: 
            newcol.append_foreign_key(fk.copy())

def copy_table_columns(table):
    columns = []
    for col in table.c:
        newcol = col.copy() 
        if len(col.foreign_keys) > 0:
            for fk in col.foreign_keys: 
                newcol.foreign_keys.add(fk.copy())
        columns.append(newcol)
    return columns

def copy_table(table, newtable):
    for key in table.c.keys():
        copy_column(key, table, newtable)

