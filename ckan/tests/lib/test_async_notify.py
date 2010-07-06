from threading import Thread
import time

from carrot.messaging import Consumer

from ckan.tests import *
from ckan import model
from ckan.lib import async_notifier
from ckan.lib.helpers import json
from ckan.lib.create_test_data import CreateTestData

class RecordingConsumerManager(Thread):
    '''As a consumer, this thread creates a queue and records what is put
    on it.
    '''
    def __init__ (self):
        Thread.__init__(self)

    def run(self):
        self.consumer = RecordingConsumer()
        self.consumer.run(clear_queue=True)

    @property
    def queued(self):
        return self.consumer.queued

    def stop(self):
        async_notifier.AsyncNotifier.send_asynchronously(None, **model.StopNotification.create())
        model.Session.remove()
        model.Session.close()

    def clear(self):
        self.consumer.clear()

class RecordingConsumer(async_notifier.AsyncConsumer):
    def __init__ (self):
        queue_name = 'recording_consumer'
        routing_key = '*'
        super(RecordingConsumer, self).__init__(queue_name, routing_key)
        self.clear()

    def callback(self, notification):
        self.queued.append(notification)

    def clear(self):
        self.queued = []


class TestNotification(TestController):
    @classmethod
    def setup_class(self):
        # create notification consumer
        self.consumer = RecordingConsumerManager()
        self.consumer.daemon = True # so destroyed automatically
        self.consumer.start()

        self.pkg_dict = {'name':u'test_notification_pkg',
                         'notes':u'This is a test package',
                         'resources':[{u'url':u'url1'}, {u'url':u'url2'}],
                         'extras':{'key1':'value1',
                                   'key2':'value2'},
                         'tags':[u'one', u'two', u'three'],
                         'groups':[u'big', u'clever'],
                         }
        self.group_name = u'wonderful'
        # tests can use this pkg as long as they promise to leave it as
        # it was created.
        CreateTestData.create_arbitrary([self.pkg_dict], extra_group_names=[self.group_name])
        self.consumer.clear()

    @classmethod
    def teardown_class(self):
        self.consumer.stop()
        CreateTestData.delete()

    def tearDown(self):
        self.usher_message_sending()
        self.consumer.clear()

    @property
    def pkg(self):
        return model.Package.by_name(self.pkg_dict['name'])

    def usher_message_sending(self):
        '''This is a simple way to block the current thread briefly to
        allow the consumer thread to process a message. Since
        these tests use Python Queue then the queue thread should pass the
        message immediately. Should this not work or become intermittent
        on some machines then we should rethink this.'''
        time.sleep(0.1)

    def queue_get_one(self):
        assert len(self.consumer.queued) == 1, [notification for notification in self.consumer.queued]
        notification = self.consumer.queued[0]
        assert isinstance(notification, model.PackageNotification), notification
        return notification

    def test_01_new_package(self):
        # manually create package so no auth objects created
        name = u'testpkg'
        rev = model.repo.new_revision() 
        pkg = model.Package(name=name)
        model.Session.add(pkg)
        model.repo.commit_and_remove()
        CreateTestData.flag_for_deletion([name])

        self.usher_message_sending()
                                        
        notification = self.queue_get_one()
        assert notification.package['name'] == name, notification.payload

    def test_02_new_package_and_permissions(self):
        # create package
        name = u'testpkg2'
        # creasts package and default permission objects
        CreateTestData.create_arbitrary([{'name':name}])

        self.usher_message_sending()
                                        
        notification = self.queue_get_one()
        assert notification['operation'] == 'new', notification['operation']
        assert notification.package['name'] == name, notification.payload

    def test_03_edit_package(self):
        # edit package
        changed_notes = u'Now changed.'
        rev = model.repo.new_revision() 
        self.pkg.notes = changed_notes
        model.repo.commit_and_remove()

        try:
            self.usher_message_sending()

            notification = self.queue_get_one()
            assert notification['operation'] == 'changed', notification['operation']
            assert notification.package['notes'] == changed_notes, notification.payload
        finally:
            # revert package change
            rev = model.repo.new_revision() 
            self.pkg.notes = self.pkg_dict['notes']
            model.repo.commit_and_remove()

    def test_04_edit_package_tags(self):
        # edit package
        new_tag = u'new'
        rev = model.repo.new_revision()
        self.pkg.add_tag_by_name(new_tag)
        CreateTestData.flag_for_deletion(tag_names=[new_tag])
        model.repo.commit_and_remove()

        try:
            self.usher_message_sending()

            notification = self.queue_get_one()
            assert notification['operation'] == 'changed', notification['operation']
            assert notification.package['name'] == self.pkg_dict['name'], notification.payload
            tags = set(notification.package['tags'])
            expected_tags = set(self.pkg_dict['tags'] + [new_tag])
            assert tags == expected_tags, '%s != %s' % (tags, expected_tags)
        finally:
            # revert package change
            rev = model.repo.new_revision()
            self.pkg.tags = [model.Tag.by_name(tag_name) \
                             for tag_name in self.pkg_dict['tags']]
            model.repo.commit_and_remove()

    def _test_05_add_package_group(self):
        # edit package
        group = model.Group.by_name(self.group_name)
        rev = model.repo.new_revision()
        group.add_package_by_name(self.pkg_dict['name'])
        model.repo.commit_and_remove()

        try:
            self.usher_message_sending()

            notification = self.queue_get_one()
            assert notification['operation'] == 'changed', notification['operation']
            assert notification.package['name'] == self.pkg_dict['name'], notification.payload
            groups = set(notification.package['groups'])
            expected_groups = set(u'big')
            assert groups == expected_groups, '%s != %s' % (groups, expected_groups)
        finally:
            # revert package change
            rev = model.repo.new_revision()
            self.pkg.groups = [model.Group.by_name(group_name) \
                               for group_name in self.pkg_dict['groups']]
            model.repo.commit_and_remove()

    def _test_06_remove_package_group(self):
        # edit package
        new_tag = u'new'
        rev = model.repo.new_revision()
        self.pkg.groups = [model.Group.by_name(u'big')] # but not clever
        model.repo.commit_and_remove()

        try:
            self.usher_message_sending()

            notification = self.queue_get_one()
            assert notification['operation'] == 'changed', notification['operation']
            assert notification.package['name'] == self.pkg_dict['name'], notification.payload
            groups = set(notification.package['groups'])
            expected_groups = set(u'big')
            assert groups == expected_groups, '%s != %s' % (groups, expected_groups)
        finally:
            # revert package change
            rev = model.repo.new_revision()
            self.pkg.groups = [model.Group.by_name(group_name) \
                               for group_name in self.pkg_dict['groups']]
            model.repo.commit_and_remove()

    def test_07_add_package_extra(self):
        # edit package
        rev = model.repo.new_revision()
        self.pkg.extras[u'key3'] = u'value3'
        model.repo.commit_and_remove()

        try:
            self.usher_message_sending()

            notification = self.queue_get_one()
            assert notification['operation'] == 'changed', notification['operation']
            assert notification.package['name'] == self.pkg_dict['name'], notification.payload
            extra_keys = set(notification.package['extras'].keys())
            expected_keys = set((u'key1', u'key2', u'key3'))
            assert extra_keys == expected_keys, '%s != %s' % (extra_keys, expected_keys)
            assert notification.package['extras']['key3'] == 'value3', notification.package['extras']['key3']
        finally:
            # revert package change
            rev = model.repo.new_revision()
            del self.pkg.extras['key3']
            model.repo.commit_and_remove()

    def _test_08_edit_package_extra(self):
        raise NotImplementedError()

    def _test_09_remove_package_extra(self):
        raise NotImplementedError()
        
    def _test_10_add_package_resource(self):
        raise NotImplementedError()

    def _test_11_edit_package_resource(self):
        raise NotImplementedError()

    def _test_12_remove_package_resource(self):
        raise NotImplementedError()
