# encoding: utf-8

import ckan.model as model
import ckan.lib.create_test_data as ctd

CreateTestData = ctd.CreateTestData


class FollowerClassesTests(object):
    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()

    def test_get(self):
        following = self.FOLLOWER_CLASS.get(self.follower.id, self.followee.id)
        assert following.follower_id == self.follower.id, following
        assert following.object_id == self.followee.id, following

    def test_get_returns_none_if_couldnt_find_users(self):
        following = self.FOLLOWER_CLASS.get('some-id', 'other-id')
        assert following is None, following

    def test_is_following(self):
        assert self.FOLLOWER_CLASS.is_following(self.follower.id,
                                                self.followee.id)

    def test_is_following_returns_false_if_user_isnt_following(self):
        assert not self.FOLLOWER_CLASS.is_following(self.followee.id,
                                                    self.follower.id)

    def test_followee_count(self):
        count = self.FOLLOWER_CLASS.followee_count(self.follower.id)
        assert count == 1, count

    def test_followee_list(self):
        followees = self.FOLLOWER_CLASS.followee_list(self.follower.id)
        object_ids = [f.object_id for f in followees]
        assert object_ids == [self.followee.id], object_ids

    def test_follower_count(self):
        count = self.FOLLOWER_CLASS.follower_count(self.followee.id)
        assert count == 1, count

    def test_follower_list(self):
        followers = self.FOLLOWER_CLASS.follower_list(self.followee.id)
        follower_ids = [f.follower_id for f in followers]
        assert follower_ids == [self.follower.id], follower_ids


class TestUserFollowingUser(FollowerClassesTests):
    FOLLOWER_CLASS = model.UserFollowingUser

    @classmethod
    def setup_class(cls):
        model.repo.rebuild_db()
        cls.follower = CreateTestData.create_user('follower')
        cls.followee = CreateTestData.create_user('followee')
        cls.FOLLOWER_CLASS(cls.follower.id, cls.followee.id).save()
        cls._create_deleted_models()

    @classmethod
    def _create_deleted_models(cls):
        deleted_user = CreateTestData.create_user('deleted_user')
        cls.FOLLOWER_CLASS(deleted_user.id, cls.followee.id).save()
        cls.FOLLOWER_CLASS(cls.follower.id, deleted_user.id).save()
        deleted_user.delete()
        deleted_user.save()


class TestUserFollowingDataset(FollowerClassesTests):
    FOLLOWER_CLASS = model.UserFollowingDataset

    @classmethod
    def setup_class(cls):
        model.repo.rebuild_db()
        cls.follower = CreateTestData.create_user('follower')
        cls.followee = cls._create_dataset('followee')
        cls.FOLLOWER_CLASS(cls.follower.id, cls.followee.id).save()
        cls._create_deleted_models()

    @classmethod
    def _create_deleted_models(cls):
        deleted_user = CreateTestData.create_user('deleted_user')
        cls.FOLLOWER_CLASS(deleted_user.id, cls.followee.id).save()
        deleted_user.delete()
        deleted_user.save()
        deleted_dataset = cls._create_dataset('deleted_dataset')
        cls.FOLLOWER_CLASS(cls.follower.id, deleted_dataset.id).save()
        deleted_dataset.delete()
        deleted_dataset.save()

    @classmethod
    def _create_dataset(self, name):
        CreateTestData.create_arbitrary({'name': name})
        return model.Package.get(name)


class TestUserFollowingGroup(FollowerClassesTests):
    FOLLOWER_CLASS = model.UserFollowingGroup

    @classmethod
    def setup_class(cls):
        model.repo.rebuild_db()
        model.repo.new_revision()
        cls.follower = CreateTestData.create_user('follower')
        cls.followee = cls._create_group('followee')
        cls.FOLLOWER_CLASS(cls.follower.id, cls.followee.id).save()
        cls._create_deleted_models()
        model.repo.commit_and_remove()

    @classmethod
    def _create_deleted_models(cls):
        deleted_user = CreateTestData.create_user('deleted_user')
        cls.FOLLOWER_CLASS(deleted_user.id, cls.followee.id).save()
        deleted_user.delete()
        deleted_user.save()
        deleted_group = cls._create_group('deleted_group')
        cls.FOLLOWER_CLASS(cls.follower.id, deleted_group.id).save()
        deleted_group.delete()
        deleted_group.save()

    @classmethod
    def _create_group(self, name):
        group = model.Group(name)
        group.save()
        return group
