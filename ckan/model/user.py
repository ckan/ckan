from datetime import datetime
import re
from hashlib import sha1
from sqlalchemy.sql.expression import or_

from meta import *
from core import DomainObject
from types import make_uuid

user_table = Table('user', metadata,
        Column('id', UnicodeText, primary_key=True, default=make_uuid),
        Column('name', UnicodeText),
        Column('openid', UnicodeText),
        Column('password', UnicodeText),
        Column('fullname', UnicodeText),
        Column('apikey', UnicodeText, default=make_uuid),
        Column('created', DateTime, default=datetime.now),
        Column('about', UnicodeText),
        )

class User(DomainObject):
    
    VALID_NAME = re.compile(r"^[a-zA-Z0-9_\-]{3,255}$")

    @classmethod
    def by_openid(cls, openid):
        obj = Session.query(cls).autoflush(False)
        return obj.filter_by(openid=openid).first()
    
    @classmethod
    def get(cls, identifier):
        query = Session.query(cls).autoflush(False)
        query = query.filter(or_(cls.name==identifier,
                                 cls.openid==identifier,
                                 cls.id==identifier))
        return query.first()

    @property
    def display_name(self):
        if self.fullname is not None and len(self.fullname.strip()) > 0:
            return self.fullname
        return self.name
        
    def _set_password(self, password):
        """Hash password on the fly."""
        if isinstance(password, unicode):
            password_8bit = password.encode('ascii', 'ignore')
        else:
            password_8bit = password

        salt = sha1(os.urandom(60))
        hash = sha1(password_8bit + salt.hexdigest())
        hashed_password = salt.hexdigest() + hash.hexdigest()

        if not isinstance(hashed_password, unicode):
            hashed_password = hashed_password.decode('utf-8')
        self._password = hashed_password

    def _get_password(self):
        """Return the password hashed"""
        return self._password

    def validate_password(self, password):
        """
        Check the password against existing credentials.

        :param password: the password that was provided by the user to
            try and authenticate. This is the clear text version that we will
            need to match against the hashed one in the database.
        :type password: unicode object.
        :return: Whether the password is valid.
        :rtype: bool
        """
        if isinstance(password, unicode):
            password_8bit = password.encode('ascii', 'ignore')
        else:
            password_8bit = password
        hashed_pass = sha1(password_8bit + self.password[:40])
        return self.password[40:] == hashed_pass.hexdigest()

    password = property(_get_password, _set_password)
        
    def as_dict(self):
        _dict = DomainObject.as_dict(self)
        del _dict['password']
        return _dict

mapper(User, user_table,
    order_by=user_table.c.name)

