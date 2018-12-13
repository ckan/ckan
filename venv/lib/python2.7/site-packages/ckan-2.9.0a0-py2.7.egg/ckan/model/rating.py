# encoding: utf-8

import datetime

from sqlalchemy import orm, types, Column, Table, ForeignKey

import meta
import package as _package
import user
import domain_object
import types as _types

__all__ = ['Rating', 'MIN_RATING', 'MAX_RATING']

MIN_RATING = 1.0
MAX_RATING = 5.0


rating_table = Table('rating', meta.metadata,
                     Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
                     Column('user_id', types.UnicodeText, ForeignKey('user.id')),
                     Column('user_ip_address', types.UnicodeText), # alternative to user_id if not logged in
                     Column('package_id', types.UnicodeText, ForeignKey('package.id')),
                     Column('rating', types.Float),
                     Column('created', types.DateTime, default=datetime.datetime.now),
                     )

class Rating(domain_object.DomainObject):
    pass

meta.mapper(Rating, rating_table,
       properties={
            'user': orm.relation(user.User,
                backref=orm.backref('ratings',
                cascade='all, delete, delete-orphan'
                )),
            'package': orm.relation(_package.Package,
                backref=orm.backref('ratings',
                cascade='all, delete, delete-orphan'
                )),
            },
       )
