from sqlalchemy.orm import object_session
from sqlalchemy import __version__ as sqav
from demo import *
from base import *

class TestMisc:
    @classmethod
    def teardown_class(self):
        repo.rebuild_db()

    def test_copy_column(self):
        t1 = package_table
        newtable = Table('mytable', metadata)
        copy_column('id', t1, newtable)
        outcol = newtable.c['id']
        assert outcol.name == 'id'
        assert outcol.primary_key == True
        # pick one with a fk
        name = 'license_id'
        copy_column(name, t1, newtable)
        incol = t1.c[name]
        outcol = newtable.c[name]
        assert outcol != incol
        assert outcol.key == incol.key
        assert len(incol.foreign_keys) == 1
        assert len(outcol.foreign_keys) == 1
        infk = list(incol.foreign_keys)[0]
        outfk = list(outcol.foreign_keys)[0]
        assert infk.parent is not None
        assert outfk.parent is not None

    def test_table_copy(self):
        t1 = package_table
        newtable = Table('newtable', metadata)
        copy_table(t1, newtable)
        assert len(newtable.c) == len(t1.c)
        # pick one with a fk
        incol = t1.c['license_id']
        outcol = None
        for col in newtable.c:
            if col.name == 'license_id':
                outcol = col
        assert outcol != incol
        assert outcol.key == incol.key
        assert len(incol.foreign_keys) == 1
        assert len(outcol.foreign_keys) == 1
        infk = list(incol.foreign_keys)[0]
        outfk = list(outcol.foreign_keys)[0]
        assert infk.parent is not None
        assert outfk.parent is not None

    def test_package_tag_table(self):
        col = package_tag_table.c['tag_id']
        assert len(col.foreign_keys) == 1

    def test_make_stateful(self):
        assert 'state' in package_table.c

    def test_make_revision_table(self):
        assert package_revision_table.name == 'package_revision'
        assert 'revision_id' in package_table.c
        assert 'state' in package_revision_table.c
        assert 'revision_id' in package_revision_table.c
        # very crude ...
        assert len(package_revision_table.c) == len(package_table.c) + 1
        # these tests may seem odd but they would incorporated following a bug
        # where this was *not* the case
        base = package_table
        rev = package_revision_table
        # crude (could be more specific about the fk)
        assert len(rev.c['revision_id'].foreign_keys) == 1
        assert rev.c['revision_id'].primary_key
        assert rev.c['id'].primary_key
        print rev.primary_key.columns
        assert len(rev.primary_key.columns) == 2

    def test_accessing_columns_on_object(self):
        table = class_mapper(Package).mapped_table
        print table.c.keys()
        assert len(table.c.keys()) > 0
        assert 'revision_id' in table.c.keys()

