# encoding: utf-8

import os

import hashlib
import pytest
import six

from passlib.hash import pbkdf2_sha512


import ckan.model as model
import ckan.tests.factories as factories


def _set_password(password):
    """Copy of the old password hashing function

    This is needed to create old password hashes in the tests
    """
    # if isinstance(password, str):
    #     password_8bit = password.encode("ascii", "ignore")
    # else:
    #     password_8bit = password

    salt = hashlib.sha1(os.urandom(60))
    hash = hashlib.sha1(six.ensure_binary(password + salt.hexdigest()))
    hashed_password = salt.hexdigest() + hash.hexdigest()

    if not isinstance(hashed_password, str):
        hashed_password = six.ensure_text(hashed_password)
    return hashed_password


@pytest.mark.usefixtures("clean_db")
class TestPasswordUpgrade:
    def test_upgrade_from_sha(self):
        user = factories.User()
        user_obj = model.User.by_name(user["name"])

        # setup our user with an old password hash
        old_hash = _set_password("testpass")
        user_obj._password = old_hash
        user_obj.save()

        user_obj.validate_password("testpass")
        assert old_hash != user_obj.password
        assert pbkdf2_sha512.identify(user_obj.password)
        assert pbkdf2_sha512.verify("testpass", user_obj.password)

    def test_upgrade_from_sha_with_unicode_password(self):
        user = factories.User()
        password = u"testpassword\xc2\xa0"
        user_obj = model.User.by_name(user["name"])

        # setup our user with an old password hash
        old_hash = _set_password(password)
        user_obj._password = old_hash
        user_obj.save()

        assert user_obj.validate_password(password)
        assert old_hash != user_obj.password
        assert pbkdf2_sha512.identify(user_obj.password)
        assert pbkdf2_sha512.verify(password, user_obj.password)

        # check that we now allow unicode characters
        assert not pbkdf2_sha512.verify("testpassword", user_obj.password)

    def test_upgrade_from_sha_with_wrong_password_fails_to_upgrade(self):
        user = factories.User()
        password = u"testpassword"
        user_obj = model.User.by_name(user["name"])

        old_hash = _set_password(password)
        user_obj._password = old_hash
        user_obj.save()

        assert not user_obj.validate_password("wrongpass")
        assert old_hash == user_obj.password
        assert not pbkdf2_sha512.identify(user_obj.password)

    def test_upgrade_from_pbkdf2_with_less_rounds(self):
        """set up a pbkdf key with less than the default rounds

        If the number of default_rounds is increased in a later version of
        passlib, ckan should upgrade the password hashes for people without
        involvement from users"""
        user = factories.User()
        password = u"testpassword"
        user_obj = model.User.by_name(user["name"])

        # setup hash with salt/rounds less than the default
        old_hash = pbkdf2_sha512.encrypt(password, salt_size=2, rounds=10)
        user_obj._password = old_hash
        user_obj.save()

        assert user_obj.validate_password(password.encode("utf-8"))
        # check that the hash has been updated
        assert old_hash != user_obj.password
        new_hash = pbkdf2_sha512.from_string(user_obj.password)

        assert pbkdf2_sha512.default_rounds > 10
        assert pbkdf2_sha512.default_rounds == new_hash.rounds

        assert pbkdf2_sha512.default_salt_size, 2
        assert pbkdf2_sha512.default_salt_size == len(new_hash.salt)
        assert pbkdf2_sha512.verify(password, user_obj.password)

    def test_upgrade_from_pbkdf2_fails_with_wrong_password(self):
        user = factories.User()
        password = u"testpassword"
        user_obj = model.User.by_name(user["name"])

        # setup hash with salt/rounds less than the default

        old_hash = pbkdf2_sha512.encrypt(password, salt_size=2, rounds=10)
        user_obj._password = old_hash
        user_obj.save()

        assert not user_obj.validate_password("wrong_pass")
        # check that the hash has _not_ been updated
        assert old_hash == user_obj.password

    def test_pbkdf2_password_auth(self):
        user = factories.User()
        password = u"testpassword"
        user_obj = model.User.by_name(user["name"])

        user_obj._set_password(password)
        user_obj.save()
        assert user_obj.validate_password(password)

    def test_pbkdf2_password_auth_unicode(self):
        user = factories.User()
        password = u"testpassword\xc2\xa0"
        user_obj = model.User.by_name(user["name"])
        user_obj._set_password(password)
        user_obj.save()
        assert user_obj.validate_password(password)

    def test_api_key_created_by_default(self):
        user = factories.User()

        assert user['apikey']


@pytest.mark.usefixtures("clean_db")
class TestUser:
    @pytest.mark.ckan_config('ckan.auth.create_default_api_keys', True)
    def test_api_key_created_when_config_true(self):
        user = factories.User()
        assert user['apikey']

    @pytest.mark.ckan_config('ckan.auth.create_default_api_keys', False)
    def test_api_key_not_created_when_config_false(self):
        user = factories.User()
        assert user['apikey'] is None

    def test_basic(self):
        data = factories.User()
        user = model.User.get(data["id"])
        assert user.name == data["name"]
        assert len(user.apikey) == 36
        assert user.fullname == data["fullname"]
        assert user.email == data["email"]

    def test_get(self):
        factories.User(fullname="Brian", name="brian")
        factories.User(fullname="Sandra", name="sandra")

        out = model.User.get(u"brian")
        assert out.fullname == u"Brian"

        out = model.User.get(u"sandra")
        assert out.fullname == u"Sandra"

    def test_is_deleted(self):
        data = factories.User()
        user = model.User.get(data["id"])
        assert not user.is_deleted()
        user.delete()
        assert user.is_deleted()

    def test_user_is_active_by_default(self):
        data = factories.User()
        user = model.User.get(data["id"])
        assert user.is_active()

    def test_activate(self):
        data = factories.User()
        user = model.User.get(data["id"])
        user.state = "some-state"
        assert not user.is_active()
        user.activate()
        assert user.is_active()

    def test_is_pending(self):
        data = factories.User()
        user = model.User.get(data["id"])
        user.state = "some-state"
        assert not user.is_pending()
        user.set_pending()
        assert user.is_pending()

    def test_get_groups(self):
        data = factories.User()
        factories.Group(name="grp1", users=[{"name": data["name"], "capacity": "admin"}])
        user = model.User.get(data["id"])
        groups = user.get_groups()

        assert len(groups) == 1
        assert groups[0].name == "grp1"

        # check cache works between sessions
        model.Session.expunge_all()
        # don't refresh user user since this is how c.user works
        # i.e. don't do this: user = model.User.by_name(u'user')
        assert len(groups) == 1
        assert groups[0].name == "grp1"

    def test_number_of_administered_packages(self):
        data = factories.User()
        factories.Dataset(user=data)
        user1 = model.User.get(data["id"])

        data = factories.User()
        user2 = model.User.get(data["id"])

        user1.number_created_packages() == 1
        user2.number_created_packages() == 0
