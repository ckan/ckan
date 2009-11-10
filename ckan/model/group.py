from datetime import datetime
from meta import *
from core import DomainObject, Package
from types import make_uuid

package_group_table = Table('package_group', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('package_id', Integer, ForeignKey('package.id')),
        Column('group_id', UnicodeText, ForeignKey('group.id'), default=make_uuid),
        )

group_table = Table('group', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('name', UnicodeText, unique=True, nullable=False),
        Column('title', UnicodeText),
        Column('description', UnicodeText),
        Column('created', DateTime, default=datetime.now),
)

class PackageGroup(DomainObject):
    pass

class Group(DomainObject):
    def __init__(self, name=u'', title=u'', description=u''):
        self.name = name
        self.title = title
        self.description = description

    # not versioned
    def delete(self):
        self.purge()

    @classmethod
    def search_by_name(self, text_query):
        text_query = text_query.strip().lower()
        return self.query.filter(self.name.contains(text_query))

    def as_dict(self):
        _dict = DomainObject.as_dict(self)
        _dict['packages'] = [package.name for package in self.packages]
        return _dict

    def add_package_by_name(self, package_name):
        if not package_name:
            return
        package = Package.byName(package_name)
        assert package
        if not package in self.packages:
            self.packages.append(package)

    def __repr__(self):
        return '<Group %s>' % self.name

mapper(Group, group_table, properties={
    'packages':relation(Package, secondary=package_group_table, backref='groups')
    })

mapper(PackageGroup, package_group_table)
    
