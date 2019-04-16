# encoding: utf-8

from sqlalchemy import Table, Column, UnicodeText, ForeignKey

from vdm.sqlalchemy.sqla import copy_table


# This function is copied from vdm, but with the addition of the 'frozen' param
def make_revisioned_table(base_table, frozen=False):
    '''Modify base_table and create correponding revision table.

    A 'frozen' revision table is not written to any more - it's just there
    as a record. It doesn't have the continuity foreign key relation.

    @return revision table.
    '''
    base_table.append_column(
        Column(u'revision_id', UnicodeText, ForeignKey(u'revision.id'))
    )
    newtable = Table(base_table.name + u'_revision', base_table.metadata)
    copy_table(base_table, newtable)

    # create foreign key 'continuity' constraint
    # remember base table primary cols have been exactly duplicated onto our
    # table
    pkcols = []
    for col in base_table.c:
        if col.primary_key:
            pkcols.append(col)
    assert len(pkcols) <= 1,\
        u'Do not support versioning objects with multiple primary keys'
    fk_name = base_table.name + u'.' + pkcols[0].name
    newtable.append_column(
        Column(u'continuity_id', pkcols[0].type,
               None if frozen else ForeignKey(fk_name))
    )

    # TODO: why do we iterate all the way through rather than just using dict
    # functionality ...? Surely we always have a revision here ...
    for col in newtable.c:
        if col.name == u'revision_id':
            col.primary_key = True
            newtable.primary_key.columns.add(col)
    return newtable
