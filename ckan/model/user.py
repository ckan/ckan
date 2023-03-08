# encoding: utf-8
from __future__ import annotations

from typing import Any, Iterable, Optional, TYPE_CHECKING

import datetime
import re
from hashlib import sha1, md5
import six

import passlib.utils
from passlib.hash import pbkdf2_sha512
from sqlalchemy.sql.expression import or_
from sqlalchemy.orm import synonym
from sqlalchemy import types, Column, Table, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from flask_login import AnonymousUserMixin
from typing_extensions import Self

from ckan.common import config
from ckan.model import meta
from ckan.model import core
from ckan.model import types as _types
from ckan.model import domain_object
from ckan.common import config, session
from ckan.types import Query

if TYPE_CHECKING:
    from ckan.model import Group, ApiToken


def last_active_check():
    last_active = config.get('ckan.user.last_active_interval')
    calc_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=last_active)

    return calc_time


def set_api_key() -> Optional[str]:
    if config.get('ckan.auth.create_default_api_keys'):
        return _types.make_uuid()
    return None


user_table = Table('user', meta.metadata,
        Column('id', types.UnicodeText, primary_key=True,
               default=_types.make_uuid),
        Column('name', types.UnicodeText, nullable=False, unique=True),
        Column('password', types.UnicodeText),
        Column('fullname', types.UnicodeText),
        Column('email', types.UnicodeText),
        Column('apikey', types.UnicodeText, default=set_api_key),
        Column('created', types.DateTime, default=datetime.datetime.now),
        Column('reset_key', types.UnicodeText),
        Column('about', types.UnicodeText),
        Column('last_active', types.TIMESTAMP),
        Column('activity_streams_email_notifications', types.Boolean,
            default=False),
        Column('sysadmin', types.Boolean, default=False),
        Column('state', types.UnicodeText, default=core.State.ACTIVE),
        Column('image_url', types.UnicodeText),
        Column('plugin_extras', MutableDict.as_mutable(JSONB))
        )


class User(core.StatefulObjectMixin,
           domain_object.DomainObject):
    id: str
    name: str
    # password: str
    fullname: Optional[str]
    email: str
    apikey: Optional[str]
    created: datetime.datetime
    reset_key: str
    about: str
    activity_streams_email_notifications: bool
    sysadmin: bool
    state: str
    image_url: str
    plugin_extras: dict[str, Any]

    api_tokens: list['ApiToken']

    VALID_NAME = re.compile(r"^[a-zA-Z0-9_\-]{3,255}$")
    DOUBLE_SLASH = re.compile(r':\/([^/])')

    @classmethod
    def by_email(cls, email: str) -> Optional[Self]:
        return meta.Session.query(cls).filter_by(email=email).first()

    @classmethod
    def get(cls, user_reference: Optional[str]) -> Optional[Self]:
        query = meta.Session.query(cls).autoflush(False)
        query = query.filter(or_(cls.name == user_reference,
                                 cls.id == user_reference))
        return query.first()

    @classmethod
    def all(cls) -> list[Self]:
        '''Return all users in this CKAN instance.

        :rtype: list of ckan.model.user.User objects

        '''
        q = meta.Session.query(cls)
        return q.all()

    @property
    def display_name(self) -> str:
        if self.fullname is not None and len(self.fullname.strip()) > 0:
            return self.fullname
        return self.name

    @property
    def email_hash(self) -> str:
        e = b''
        if self.email:
            e = self.email.strip().lower().encode('utf8')
        return md5(e).hexdigest()

    def get_reference_preferred_for_uri(self) -> str:
        '''Returns a reference (e.g. name, id) for this user
        suitable for the user\'s URI.
        When there is a choice, the most preferable one will be
        given, based on readability.
        The result is not escaped (will get done in url_for/redirect_to).
        '''
        if self.name:
            ref = self.name
        else:
            ref = self.id
        return ref

    def _set_password(self, password: str):
        '''Hash using pbkdf2

        Use passlib to hash the password using pkbdf2, upgrading
        passlib will also upgrade the number of rounds and salt of the
        hash as the user logs in automatically. Changing hashing
        algorithm will require this code to be changed (perhaps using
        passlib's CryptContext)
        '''
        hashed_password: Any = pbkdf2_sha512.encrypt(password)

        if not isinstance(hashed_password, str):
            hashed_password = six.ensure_text(hashed_password)
        self._password = hashed_password

    def _get_password(self) -> str:
        return self._password

    def _verify_and_upgrade_from_sha1(self, password: str) -> bool:
        # if isinstance(password, str):
        #     password_8bit = password.encode('ascii', 'ignore')
        # else:
        #     password_8bit = password

        hashed_pass = sha1(six.ensure_binary(password + self.password[:40]))
        current_hash = passlib.utils.to_native_str(self.password[40:])

        if passlib.utils.consteq(hashed_pass.hexdigest(), current_hash):
            #we've passed the old sha1 check, upgrade our password
            self._set_password(password)
            self.save()
            return True
        else:
            return False

    def _verify_and_upgrade_pbkdf2(self, password: str) -> bool:
        if pbkdf2_sha512.verify(password, self.password):
            self._set_password(password)
            self.save()
            return True
        else:
            return False

    def validate_password(self, password: str) -> bool:
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
            current_hash: Any = pbkdf2_sha512.from_string(self.password)
            if (current_hash.rounds < pbkdf2_sha512.default_rounds or
                len(current_hash.salt) < pbkdf2_sha512.default_salt_size):

                return self._verify_and_upgrade_pbkdf2(password)
            else:
                return bool(pbkdf2_sha512.verify(password, self.password))

    password = property(_get_password, _set_password)

    @classmethod
    def check_name_valid(cls, name: str) -> bool:
        if not name \
            or not len(name.strip()) \
            or not cls.VALID_NAME.match(name):
            return False
        return True

    @classmethod
    def check_name_available(cls, name: str) -> bool:
        return cls.by_name(name) == None

    def as_dict(self) -> dict[str, Any]:
        _dict = domain_object.DomainObject.as_dict(self)
        del _dict['password']
        return _dict

    def number_created_packages(self, include_private_and_draft: bool=False) -> int:
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

        result: int = meta.Session.execute(
            q.statement.with_only_columns(
                [func.count()]
            ).order_by(
                None
            )
        ).scalar()
        return result

    def activate(self) -> None:
        ''' Activate the user '''
        self.state = core.State.ACTIVE

    def set_pending(self) -> None:
        ''' Set the user as pending '''
        self.state = core.State.PENDING

    def is_deleted(self) -> bool:
        return self.state == core.State.DELETED

    def is_pending(self) -> bool:
        return self.state == core.State.PENDING

    def is_in_group(self, group_id: str) -> bool:
        return group_id in self.get_group_ids()

    def is_in_groups(self, group_ids: Iterable[str]) -> bool:
        ''' Given a list of group ids, returns True if this user is in
        any of those groups '''
        guser = set(self.get_group_ids())
        gids = set(group_ids)

        return len(guser.intersection(gids)) > 0

    def get_group_ids(self, group_type: Optional[str]=None, capacity: Optional[str]=None) -> list[str]:
        ''' Returns a list of group ids that the current user belongs to '''
        return [g.id for g in
                self.get_groups(group_type=group_type, capacity=capacity)]

    def get_groups(self, group_type: Optional[str]=None, capacity: Optional[str]=None) -> list['Group']:
        import ckan.model as model

        q: Query[model.Group] = meta.Session.query(model.Group)\
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
    def search(cls, querystr: str,
               sqlalchemy_query: Optional[Any] = None,
               user_name: Optional[str] = None) -> Query[Self]:
        '''Search name, fullname, email. '''
        if sqlalchemy_query is None:
            query = meta.Session.query(cls)
        else:
            query = sqlalchemy_query
        qstr = '%' + querystr + '%'
        filters: list[Any] = [
            # type_ignore_reason: incomplete SQLAlchemy types
            cls.name.ilike(qstr),  # type: ignore
            cls.fullname.ilike(qstr),  # type: ignore
        ]
        # sysadmins can search on user emails
        import ckan.authz as authz
        if user_name and authz.is_sysadmin(user_name):
            # type_ignore_reason: incomplete SQLAlchemy types
            filters.append(cls.email.ilike(qstr))  # type: ignore

        query = query.filter(or_(*filters))
        return query

    @classmethod
    def user_ids_for_name_or_id(cls, user_list: Iterable[str]=()) -> list[str]:
        '''
        This function returns a list of ids from an input that can be a list of
        names or ids
        '''
        query: Any = meta.Session.query(cls.id)
        # type_ignore_reason: incomplete SQLAlchemy types
        query = query.filter(or_(cls.name.in_(user_list),  # type: ignore
                                 cls.id.in_(user_list)))  # type: ignore
        return [user.id for user in query.all()]

    def get_id(self) -> str:
        '''Needed by flask-login'''
        return self.id

    @property
    def is_authenticated(self) -> bool:
        '''Needed by flask-login'''
        return True

    @property
    def is_anonymous(self):
        '''Needed by flask-login'''
        return False

    @property
    def is_active(self):
        '''Needed by flask-login'''
        return super().is_active()

    def set_user_last_active(self) -> None:
        if self.last_active:
            session["last_active"] = self.last_active

            if session["last_active"] < last_active_check():
                self.last_active = datetime.datetime.utcnow()
                meta.Session.commit()
        else:
            self.last_active = datetime.datetime.utcnow()
            meta.Session.commit()


class AnonymousUser(AnonymousUserMixin):
    '''Extends the default AnonymousUserMixin to have an attribute
    `name`/`email`, so, when retrieving the current_user.name/email on an
    anonymous user, won't break our app with `AttributeError`.
    '''
    name: str = ""
    email: str = ""


meta.mapper(
    User, user_table,
    properties={'password': synonym('_password', map_column=True)}
    )
