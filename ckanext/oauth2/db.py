# -*- coding: utf-8 -*-

# Copyright (c) 2014 CoNWeT Lab., Universidad Politécnica de Madrid

# This file is part of OAuth2 CKAN Extension.

# OAuth2 CKAN Extension is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# OAuth2 CKAN Extension is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with OAuth2 CKAN Extension.  If not, see <http://www.gnu.org/licenses/>.

import sqlalchemy as sa

UserToken = None


def init_db(model):

    global UserToken
    if UserToken is None:

        class _UserToken(model.DomainObject):

            @classmethod
            def by_user_name(cls, user_name):
                return model.Session.query(cls).filter_by(user_name=user_name).first()

        UserToken = _UserToken

        user_token_table = sa.Table('user_token', model.meta.metadata,
            sa.Column('user_name', sa.types.UnicodeText, primary_key=True),
            sa.Column('access_token', sa.types.UnicodeText),
            sa.Column('token_type', sa.types.UnicodeText),
            sa.Column('refresh_token', sa.types.UnicodeText),
            sa.Column('expires_in', sa.types.UnicodeText)
        )

        # Create the table only if it does not exist
        user_token_table.create(checkfirst=True)

        model.meta.mapper(UserToken, user_token_table)
