from meta import *
from core import DomainObject, Package
from types import make_uuid

package_group_table = Table('package_groups', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('package_id', types.Integer, ForeignKey('package.id')),
        Column('group_id', types.UnicodeText, ForeignKey('group.id'), default=make_uuid),
        )

group_table = Table('group', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('name', types.UnicodeText, unique=True, nullable=False),
        Column('title', types.UnicodeText),
        Column('description', types.UnicodeText),
)

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

    def __repr__(self):
        return '<Group %s>' % self.name

mapper(Group, group_table, properties = {
    'packages':relation(Package, secondary=package_group_table, backref='groups')
    })

