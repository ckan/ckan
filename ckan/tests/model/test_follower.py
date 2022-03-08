# encoding: utf-8

import pytest
import ckan.model as model
import ckan.tests.factories as factories


class FollowerClassesTests(object):
    def test_get(self):
        self._before()
        following = self.FOLLOWER_CLASS.get(
            self.follower["id"], self.followee["id"]
        )
        assert following.follower_id == self.follower["id"], following
        assert following.object_id == self.followee["id"], following

    def test_get_returns_none_if_couldnt_find_users(self):
        self._before()
        following = self.FOLLOWER_CLASS.get("some-id", "other-id")
        assert following is None, following

    def test_is_following(self):
        self._before()
        assert self.FOLLOWER_CLASS.is_following(
            self.follower["id"], self.followee["id"]
        )

    def test_is_following_returns_false_if_user_isnt_following(self):
        self._before()
        assert not self.FOLLOWER_CLASS.is_following(
            self.followee["id"], self.follower["id"]
        )

    def test_followee_count(self):
        self._before()
        count = self.FOLLOWER_CLASS.followee_count(self.follower["id"])
        assert count == 1, count

    def test_followee_list(self):
        self._before()
        followees = self.FOLLOWER_CLASS.followee_list(self.follower["id"])
        object_ids = [f.object_id for f in followees]
        assert object_ids == [self.followee["id"]], object_ids

    def test_follower_count(self):
        self._before()
        count = self.FOLLOWER_CLASS.follower_count(self.followee["id"])
        assert count == 1, count

    def test_follower_list(self):
        self._before()
        followers = self.FOLLOWER_CLASS.follower_list(self.followee["id"])
        follower_ids = [f.follower_id for f in followers]
        assert follower_ids == [self.follower["id"]], follower_ids


@pytest.mark.usefixtures("non_clean_db")
class TestUserFollowingUser(FollowerClassesTests):
    FOLLOWER_CLASS = model.UserFollowingUser

    def _before(self):
        self.follower = factories.User()
        self.followee = factories.User()
        self.FOLLOWER_CLASS(self.follower["id"], self.followee["id"]).save()
        self._create_deleted_models()

    def _create_deleted_models(self):
        deleted_user = factories.User()
        self.FOLLOWER_CLASS(deleted_user["id"], self.followee["id"]).save()
        self.FOLLOWER_CLASS(self.follower["id"], deleted_user["id"]).save()
        user = model.User.get(deleted_user["id"])
        user.delete()
        user.save()


@pytest.mark.usefixtures("non_clean_db")
class TestUserFollowingDataset(FollowerClassesTests):
    FOLLOWER_CLASS = model.UserFollowingDataset

    def _before(self):
        self.follower = factories.User()
        self.followee = self._create_dataset()
        self.FOLLOWER_CLASS(self.follower["id"], self.followee["id"]).save()
        self._create_deleted_models()

    def _create_deleted_models(self):
        deleted_user = factories.User()
        self.FOLLOWER_CLASS(deleted_user["id"], self.followee["id"]).save()
        user = model.User.get(deleted_user["id"])
        user.delete()
        user.save()
        deleted_dataset = self._create_dataset()
        self.FOLLOWER_CLASS(self.follower["id"], deleted_dataset["id"]).save()
        dataset = model.Package.get(deleted_dataset["id"])
        dataset.delete()
        dataset.save()

    def _create_dataset(self):
        return factories.Dataset()


@pytest.mark.usefixtures("non_clean_db")
class TestUserFollowingGroup(FollowerClassesTests):
    FOLLOWER_CLASS = model.UserFollowingGroup

    def _before(self):
        self.follower = factories.User()
        self.followee = self._create_group()
        self.FOLLOWER_CLASS(self.follower["id"], self.followee["id"]).save()
        self._create_deleted_models()
        model.repo.commit_and_remove()

    def _create_deleted_models(self):
        deleted_user = factories.User()
        self.FOLLOWER_CLASS(deleted_user["id"], self.followee["id"]).save()
        user = model.User.get(deleted_user["id"])
        user.delete()
        user.save()

        deleted_group = self._create_group()
        self.FOLLOWER_CLASS(self.follower["id"], deleted_group["id"]).save()
        group = model.Group.get(deleted_group["id"])
        group.delete()
        group.save()

    def _create_group(self):
        return factories.Group()
