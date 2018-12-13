from sqlalchemy import *
from sqlalchemy.orm import *

from stateful import *

engine = create_engine('sqlite:///:memory:', echo=True)

metadata = MetaData(bind=engine)

license_table = Table('license', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
        )

package_table = Table('package', metadata,
        Column('id', String(100), primary_key=True),
)

package_license_table = Table('package_license', metadata,
        Column('id', Integer, primary_key=True),
        Column('package_id', Integer, ForeignKey('package.id')),
        Column('license_id', Integer, ForeignKey('license.id')),
        Column('state', String, default='active'),
        )

metadata.create_all(engine)


from sqlalchemy.orm import scoped_session, sessionmaker, create_session
from sqlalchemy.orm import relation, backref
SessionObject = scoped_session(create_session)
session = SessionObject()

from sqlalchemy.orm import mapper
#mapper = SessionObject.mapper

from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm.collections import attribute_mapped_collection

from sqlalchemy import __version__ as sqav
if sqav.startswith("0.4"):
    _clear = session.clear
else:
    _clear = session.expunge_all
    
class BaseObject(object):

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.id)

def delete(st):
    st.state = 'deleted'

def undelete(st):
    st.state = 'active'

def is_active(st):
    return st.state == 'active'

def _create_pl_by_license(license):
    return PackageLicense(license=license)

class Package(BaseObject):

    def __init__(self, id):
        self.id = id

#     licenses_active = StatefulListProperty('package_licenses', is_active,
#             delete, undelete)
#     licenses_deleted = StatefulListProperty('package_licenses', lambda x: not is_active(x),
#             undelete, delete)
#     licenses = OurAssociationProxy('licenses_active', 'license',
#         creator=_create_pl_by_license)
    licenses2 = association_proxy('package_licenses', 'license',
            creator=_create_pl_by_license)

class License(BaseObject):
    def __init__(self, name):
        self.name = name

class PackageLicense(object):
    def __init__(self, package=None, license=None, state='active'):
        self.package = package
        self.license = license
        self.state = state
    
    def __repr__(self):
        return '<PackageLicense %s %s %s %s>' % (self.id, self.package,
                self.license, self.state)

    # for testing versioned m2m
    def get_as_of(self):
        return self

add_stateful_m2m(Package, PackageLicense,  'licenses', 'license',
        'package_licenses', is_active=is_active, delete=delete,
        undelete=undelete)
from base import add_stateful_versioned_m2m
add_stateful_versioned_m2m(Package, PackageLicense,  'licenses3', 'license',
        'package_licenses', is_active=is_active, delete=delete,
        undelete=undelete)

mapper(Package, package_table, properties={
    'package_licenses':relation(PackageLicense),
    })
mapper(License, license_table)
mapper(PackageLicense, package_license_table, properties={
        'package':relation(Package),
        'license':relation(License),
        })


class TestStatefulCollections(object):

    @classmethod
    def setup_class(self):
        pkg1 = Package('pkg1')
        session.add(pkg1)
        lic1 = License('a')
        lic2 = License('b')
        lic3 = License('c')
        lic4 = License('d')
        self.license_list = [ lic1, lic2, lic3, lic4 ]
        for li in [lic1, lic2, lic3, lic4]:
            pkg1.licenses_active.append(PackageLicense(pkg1, li))
        del pkg1.licenses_active[3]
        session.flush()
        
        _clear()

    def test_0_package_licenses(self):
        pkg1 = session.query(Package).get('pkg1')
        assert len(pkg1.package_licenses) == 4
        assert pkg1.package_licenses[-1].state == 'deleted'

    def test_1_licenses(self):
        p1 = session.query(Package).get('pkg1')
        assert len(p1.licenses) == 3

    def test_2_active_deleted_and_appending(self):
        p1 = session.query(Package).get('pkg1')
        assert len(p1.licenses_active) == 3
        assert len(p1.licenses_deleted) == 1
        p1.licenses_deleted.append(PackageLicense(license=License('e')))
        assert len(p1.licenses_active) == 3
        assert len(p1.licenses_deleted) == 2
        session.flush()
        _clear()
        pkg1 = session.query(Package).get('pkg1')
        assert len(p1.package_licenses) == 5
        assert len(p1.licenses_active) == 3
        assert len(p1.licenses_deleted) == 2
        _clear()

    def test_3_assign_etc(self):
        p1 = session.query(Package).get('pkg1')
        p1.licenses = []
        assert len(p1.licenses) == 0 
        assert len(p1.licenses_active) == 0
        assert len(p1.licenses_deleted) == 5
        session.flush()
        _clear()

        pkg1 = session.query(Package).get('pkg1')
        assert len(p1.licenses) == 0 
        assert len(p1.package_licenses) == 5
        assert len(p1.licenses_deleted) == 5

# TODO: move this test to base_test (hasslesome because of all the test
# fixtures)
class TestStatefulVersionedCollections(object):

    @classmethod
    def setup_class(self):
        pkg2 = Package('pkg2')
        session.add(pkg2)
        lic1 = License('a')
        lic2 = License('b')
        lic3 = License('c')
        lic4 = License('d')
        self.license_list = [ lic1, lic2, lic3, lic4 ]
        for li in [lic1, lic2, lic3, lic4]:
            pkg2.licenses3_active.append(PackageLicense(pkg2, li))
        del pkg2.licenses3_active[3]
        session.flush()
        _clear()

    def test_0_package_licenses(self):
        pkg2 = session.query(Package).get('pkg2')
        assert len(pkg2.package_licenses) == 4
        assert pkg2.package_licenses[-1].state == 'deleted'

    def test_1_licenses3(self):
        p1 = session.query(Package).get('pkg2')
        assert len(p1.licenses3) == 3

    def test_2_active_deleted_and_appending(self):
        p1 = session.query(Package).get('pkg2')
        assert len(p1.licenses3_active) == 3
        assert len(p1.licenses3_deleted) == 1
        p1.licenses3_deleted.append(PackageLicense(license=License('e')))
        assert len(p1.licenses3_active) == 3
        assert len(p1.licenses3_deleted) == 2
        session.flush()
        _clear()
        p1 = session.query(Package).get('pkg2')
        assert len(p1.package_licenses) == 5
        assert len(p1.licenses3_active) == 3
        assert len(p1.licenses3_deleted) == 2
        _clear()

    def test_3_assign_etc(self):
        p1 = session.query(Package).get('pkg2')
        p1.licenses3 = []
        assert len(p1.licenses3) == 0 
        assert len(p1.licenses3_active) == 0
        assert len(p1.licenses3_deleted) == 5
        session.flush()
        _clear()

        p1 = session.query(Package).get('pkg2')
        assert len(p1.licenses3) == 0 
        assert len(p1.package_licenses) == 5
        assert len(p1.licenses3_deleted) == 5


class TestSimple:
    def test_1(self):
        pkg1 = Package('pkg3')
        session.add(pkg1)
        lic1 = License('a')
        lic2 = License('b')
        lic3 = License('c')
        lic4 = License('d')
        pkg1.licenses2 = [lic1, lic2, lic3]
        assert len(pkg1.package_licenses) == 3
        assert pkg1.licenses2[0].name == 'a'
        pkg1.licenses2.append(lic4)
        pkg1.package_licenses[-1].state = 'deleted'
        session.flush()
        # must clear or other things won't behave
        _clear()

    def test_2(self):
        p1 = session.query(Package).get('pkg3')
        assert p1.package_licenses[0].package == p1

