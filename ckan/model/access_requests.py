# encoding: utf-8

# a.s. May 7, 2019
#

import datetime

from sqlalchemy import orm, types, Column, Table, ForeignKey, text

import meta
import domain_object
import types as _types

__all__ = ['AccessRequests', 'access_request_table']

access_request_table = Table('access_request', meta.metadata,
                             Column('id', types.UnicodeText,
                                    primary_key=True, default=_types.make_uuid),
                             Column('user_ip_address', types.UnicodeText),
                             Column('user_email', types.UnicodeText),
                             Column('maintainer_name', types.UnicodeText),
                             Column('maintainer_email', types.UnicodeText),
                             Column('user_msg', types.UnicodeText),
                             Column('created', types.DateTime,
                                    default=datetime.datetime.now),
                             )


class AccessRequests(domain_object.DomainObject):

    @classmethod
    def get_test(data=None):
        return


meta.mapper(AccessRequests, access_request_table,
            )
