# encoding: utf-8

import datetime
import re
import os
from hashlib import sha1, md5

import passlib.utils
from passlib.hash import pbkdf2_sha512
from sqlalchemy.sql.expression import or_
from sqlalchemy.orm import synonym
from sqlalchemy import types, Column, Table, func
import vdm.sqlalchemy

import meta
import core
import types as _types
import domain_object


user_table = Table('user', meta.metadata,
        Column('id', types.UnicodeText, primary_key=True,
               default=_types.make_uuid),
        Column('name', types.UnicodeText, nullable=False, unique=True),
        Column('openid', types.UnicodeText),
        Column('password', types.UnicodeText),
        Column('fullname', types.UnicodeText),
        Column('email', types.UnicodeText),
        Column('apikey', types.UnicodeText, default=_types.make_uuid),
        Column('created', types.DateTime, default=datetime.datetime.now),
        Column('reset_key', types.UnicodeText),
        Column('about', types.UnicodeText),
        Column('activity_streams_email_notifications', types.Boolean,
            default=False),
        Column('sysadmin', types.Boolean, default=False),
        )

vdm.sqlalchemy.make_table_stateful(user_table)


class User(vdm.sqlalchemy.StatefulObjectMixin,
           domain_object.DomainObject):

    VALID_NAME = re.compile(r"^[a-zA-Z0-9_\-]{3,255}$")
    DOUBLE_SLASH = re.compile(':\/([^/])')

    @classmethod
    def by_openid(cls, openid):
        obj = meta.Session.query(cls).autoflush(False)
        return obj.filter_by(openid=openid).first()

    @classmethod
    def by_email(cls, email):
        return meta.Session.query(cls).filter_by(email=email).all()

    @classmethod
    def get(cls, user_reference):
        query = meta.Session.query(cls).autoflush(False)
        query = query.filter(or_(cls.name == user_reference,
                                 cls.id == user_reference))
        return query.first()

    @classmethod
    def all(cls):
        '''Return all users in this CKAN instance.

        :rtype: list of ckan.model.user.User objects

        '''
        q = meta.Session.query(cls)
        return q.all()

    @property
    def display_name(self):
        if self.fullname is not None and len(self.fullname.strip()) > 0:
            return self.fullname
        return self.name

    @property
    def email_hash(self):
        e = ''
        if self.email:
            e = self.email.strip().lower().encode('utf8')
        return md5(e).hexdigest()

    def get_reference_preferred_for_uri(self):
        '''Returns a reference (e.g. name, id, openid) for this user
        suitable for the user\'s URI.
        When there is a choice, the most preferable one will be
        given, based on readability. This is expected when repoze.who can
        give a more friendly name for an openid user.
        The result is not escaped (will get done in url_for/redirect_to).
        '''
        if self.name:
            ref = self.name
        elif self.openid:
            ref = self.openid
        else:
            ref = self.id
        return ref

    def _set_password(self, password):
        '''Hash using pbkdf2

        Use passlib to hash the password using pkbdf2, upgrading
        passlib will also upgrade the number of rounds and salt of the
        hash as the user logs in automatically. Changing hashing
        algorithm will require this code to be changed (perhaps using
        passlib's CryptContext)
        '''
        hashed_password = pbkdf2_sha512.encrypt(password)

        if not isinstance(hashed_password, unicode):
            hashed_password = hashed_password.decode('utf-8')
        self._password = hashed_password

    def _get_password(self):
        return self._password

    def _verify_and_upgrade_from_sha1(self, password):
        if isinstance(password, unicode):
            password_8bit = password.encode('ascii', 'ignore')
        else:
            password_8bit = password

        hashed_pass = sha1(password_8bit + self.password[:40])
        current_hash = passlib.utils.to_native_str(self.password[40:])

        if passlib.utils.consteq(hashed_pass.hexdigest(), current_hash):
            #we've passed the old sha1 check, upgrade our password
            self._set_password(password)
            self.save()
            return True
        else:
            return False

    def _verify_and_upgrade_pbkdf2(self, password):
        if pbkdf2_sha512.verify(password, self.password):
            self._set_password(password)
            self.save()
            return True
        else:
            return False

    def validate_password(self, password):
        '''
        Check the password against existing credentials.

        :param password: the password that was provided by the user to
            try and authenticate. This is the clear text version that we will
            need to match against the hashed one in the database.
        :type password: unicode object.
        :return: Whether the password is valid.
        :rtype: bool
        '''
        if not password or not self.password:
            return False

        if not pbkdf2_sha512.identify(self.password):
            return self._verify_and_upgrade_from_sha1(password)
        else:
            current_hash = pbkdf2_sha512.from_string(self.password)
            if (current_hash.rounds < pbkdf2_sha512.default_rounds or
                len(current_hash.salt) < pbkdf2_sha512.default_salt_size):

                return self._verify_and_upgrade_pbkdf2(password)
            else:
                return pbkdf2_sha512.verify(password, self.password)

    password = property(_get_password, _set_password)

    @classmethod
    def check_name_valid(cls, name):
        if not name \
            or not len(name.strip()) \
            or not cls.VALID_NAME.match(name):
            return False
        return True

    @classmethod
    def check_name_available(cls, name):
        return cls.by_name(name) == None

    def as_dict(self):
        _dict = domain_object.DomainObject.as_dict(self)
        del _dict['password']
        return _dict

    def number_of_edits(self):
        # have to import here to avoid circular imports
        import ckan.model as model

        # Get count efficiently without spawning the SQLAlchemy subquery
        # wrapper. Reset the VDM-forced order_by on timestamp.
        return meta.Session.execute(
            meta.Session.query(
                model.Revision
            ).filter_by(
                author=self.name
            ).statement.with_only_columns(
                [func.count()]
            ).order_by(
                None
            )
        ).scalar()

    def number_created_packages(self, include_private_and_draft=False):
        # have to import here to avoid circular imports
        import ckan.model as model

        # Get count efficiently without spawning the SQLAlchemy subquery
        # wrapper. Reset the VDM-forced order_by on timestamp.
        q = meta.Session.query(
            model.Package
        ).filter_by(
            creator_user_id=self.id
        )

        if include_private_and_draft:
            q = q.filter(model.Package.state != 'deleted')
        else:
            q = q.filter_by(state='active', private=False)

        return meta.Session.execute(
            q.statement.with_only_columns(
                [func.count()]
            ).order_by(
                None
            )
        ).scalar()

    def activate(self):
        ''' Activate the user '''
        self.state = core.State.ACTIVE

    def set_pending(self):
        ''' Set the user as pending '''
        self.state = core.State.PENDING

    def is_deleted(self):
        return self.state == core.State.DELETED

    def is_pending(self):
        return self.state == core.State.PENDING

    def is_in_group(self, group_id):
        return group_id in self.get_group_ids()

    def is_in_groups(self, group_ids):
        ''' Given a list of group ids, returns True if this user is in
        any of those groups '''
        guser = set(self.get_group_ids())
        gids = set(group_ids)

        return len(guser.intersection(gids)) > 0

    def get_group_ids(self, group_type=None, capacity=None):
        ''' Returns a list of group ids that the current user belongs to '''
        return [g.id for g in
                self.get_groups(group_type=group_type, capacity=capacity)]

    def get_groups(self, group_type=None, capacity=None):
        import ckan.model as model

        q = meta.Session.query(model.Group)\
            .join(model.Member, model.Member.group_id == model.Group.id and \
                       model.Member.table_name == 'user').\
               join(model.User, model.User.id == model.Member.table_id).\
               filter(model.Member.state == 'active').\
               filter(model.Member.table_id == self.id)
        if capacity:
            q = q.filter(model.Member.capacity == capacity)
            return q.all()

        if '_groups' not in self.__dict__:
            self._groups = q.all()

        groups = self._groups
        if group_type:
            groups = [g for g in groups if g.type == group_type]
        return groups

    @classmethod
    def search(cls, querystr, sqlalchemy_query=None, user_name=None):
        '''Search name, fullname, email and openid. '''
        if sqlalchemy_query is None:
            query = meta.Session.query(cls)
        else:
            query = sqlalchemy_query
        qstr = '%' + querystr + '%'
        filters = [
            cls.name.ilike(qstr),
            cls.fullname.ilike(qstr),
            cls.openid.ilike(qstr),
        ]
        # sysadmins can search on user emails
        import ckan.authz as authz
        if user_name and authz.is_sysadmin(user_name):
            filters.append(cls.email.ilike(qstr))

        query = query.filter(or_(*filters))
        return query

    @classmethod
    def user_ids_for_name_or_id(self, user_list=[]):
        '''
        This function returns a list of ids from an input that can be a list of
        names or ids
        '''
        query = meta.Session.query(self.id)
        query = query.filter(or_(self.name.in_(user_list),
                                 self.id.in_(user_list)))
        return [user.id for user in query.all()]


meta.mapper(User, user_table,
    properties={'password': synonym('_password', map_column=True)},
    order_by=user_table.c.name)
