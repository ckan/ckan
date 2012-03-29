import datetime

from meta import *
from core import *
from package import *
import user
import domain_object
import types as _types

__all__ = ['Rating']

rating_table = Table('rating', metadata,
                     Column('id', UnicodeText, primary_key=True, default=_types.make_uuid),
                     Column('user_id', UnicodeText, ForeignKey('user.id')),
                     Column('user_ip_address', UnicodeText), # alternative to user_id if not logged in
                     Column('package_id', UnicodeText, ForeignKey('package.id')),
                     Column('rating', Float),
                     Column('created', DateTime, default=datetime.datetime.now),
                     )

class Rating(domain_object.DomainObject):
    pass

mapper(Rating, rating_table,
       properties={
            'user': orm.relation(user.User,
                backref=orm.backref('ratings',
                cascade='all, delete, delete-orphan'
                )),
            'package': orm.relation(Package,
                backref=orm.backref('ratings',
                cascade='all, delete, delete-orphan'
                )),
            },
       )
