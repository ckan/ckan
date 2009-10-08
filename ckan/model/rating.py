from meta import *
from core import DomainObject, Package
from types import make_uuid
from user import User

__all__ = ['Rating']

rating_table = Table('rating', metadata,
                     Column('id', UnicodeText, primary_key=True, default=make_uuid),
                     Column('user_id', UnicodeText, ForeignKey('user.id')),
                     Column('user_ip_address', UnicodeText), # alternative to user_id if not logged in
                     Column('package_id', Integer, ForeignKey('package.id')),
                     Column('rating', Float)
                     )

class Rating(DomainObject):
    pass

mapper(Rating, rating_table,
       properties={
            'user': orm.relation(User,
                backref=orm.backref('ratings',
                cascade='all, delete, delete-orphan'
                )),
            'package': orm.relation(Package,
                backref=orm.backref('ratings',
                cascade='all, delete, delete-orphan'
                )),
            },
       )
