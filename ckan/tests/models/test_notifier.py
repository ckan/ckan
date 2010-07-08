import time
import blinker

from carrot.messaging import Consumer

from ckan.tests import *
from ckan import model
from ckan.lib import async_notifier
from ckan.lib.helpers import json
from ckan.lib.create_test_data import CreateTestData


class TestNotification(TestController):
    '''Tests the triggering of the NotifierMapperTrigger(MapperExtension) when
    you change a package etc.'''

    our_queue = []

    @classmethod
    def add_notification_to_our_queue(cls, sender, **notification_dict):
        notification = model.Notification.recreate_from_dict(notification_dict)
        cls.our_queue.append(notification)
    
    @classmethod
    def setup_class(self):
        # divert NotifierMapperTrigger's message sending to us
        for routing_key in model.ROUTING_KEYS:
            signal = blinker.signal(routing_key)
            signal.connect(self.add_notification_to_our_queue)
        
        self.pkg_dict = {'name':u'test_notification_pkg',
                         'notes':u'This is a test package',
                         'resources':[{u'url':u'url1', u'description':u'desc1'},
                                      {u'url':u'url2', u'description':u'desc2'}],
                         'extras':{'key1':'value1',
                                   'key2':'value2'},
                         'tags':[u'one', u'two', u'three'],
                         'groups':[u'big', u'clever'],
                         }
        self.group_name = u'wonderful'
        # tests can use this pkg as long as they promise to leave it as
        # it was created.
        CreateTestData.create_arbitrary([self.pkg_dict], extra_group_names=[self.group_name])
        self.clear()        

    def setUp(self):
        self.clear()

    @classmethod
    def clear(self):
        self.our_queue = []
        
    @classmethod
    def teardown_class(self):
        for routing_key in model.ROUTING_KEYS:
            signal = blinker.signal(routing_key)
            signal.disconnect(self.add_notification_to_our_queue)
        CreateTestData.delete()

    @property
    def pkg(self):
        return model.Package.by_name(self.pkg_dict['name'])

    def queue_get_one(self):
        notifications = TestNotification.our_queue
        assert len(notifications) == 1, [n for n in notifications]
        notification = notifications[0]
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
                                        
        package_notification = self.queue_get_one()
        assert isinstance(package_notification, model.PackageNotification)
        package_notification.package['name'] == name, package_notification.package
        package_notification['operation'] == 'new', package_notification['operation']

    def test_02_new_package_and_permissions(self):
        # create package
        name = u'testpkg2'
        # creasts package and default permission objects
        CreateTestData.create_arbitrary([{'name':name}])

        package_notification = self.queue_get_one()
        assert isinstance(package_notification, model.PackageNotification)
        package_notification.package['name'] == name, package_notification.package

    def test_03_edit_package(self):
        # edit package
        changed_notes = u'Now changed.'
        rev = model.repo.new_revision() 
        self.pkg.notes = changed_notes
        model.repo.commit_and_remove()

        try:
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

##    def _test_05_add_package_group(self):
##        # edit package
##        group = model.Group.by_name(self.group_name)
##        rev = model.repo.new_revision()
##        group.add_package_by_name(self.pkg_dict['name'])
##        model.repo.commit_and_remove()

##        try:
##            self.usher_message_sending()

##            notification = self.queue_get_one()
##            assert notification['operation'] == 'changed', notification['operation']
##            assert notification.package['name'] == self.pkg_dict['name'], notification.payload
##            groups = set(notification.package['groups'])
##            expected_groups = set(u'big')
##            assert groups == expected_groups, '%s != %s' % (groups, expected_groups)
##        finally:
##            # revert package change
##            rev = model.repo.new_revision()
##            self.pkg.groups = [model.Group.by_name(group_name) \
##                               for group_name in self.pkg_dict['groups']]
##            model.repo.commit_and_remove()

##    def _test_06_remove_package_group(self):
##        # edit package
##        new_tag = u'new'
##        rev = model.repo.new_revision()
##        self.pkg.groups = [model.Group.by_name(u'big')] # but not clever
##        model.repo.commit_and_remove()

##        try:
##            self.usher_message_sending()

##            notification = self.queue_get_one()
##            assert notification['operation'] == 'changed', notification['operation']
##            assert notification.package['name'] == self.pkg_dict['name'], notification.payload
##            groups = set(notification.package['groups'])
##            expected_groups = set(u'big')
##            assert groups == expected_groups, '%s != %s' % (groups, expected_groups)
##        finally:
##            # revert package change
##            rev = model.repo.new_revision()
##            self.pkg.groups = [model.Group.by_name(group_name) \
##                               for group_name in self.pkg_dict['groups']]
##            model.repo.commit_and_remove()

    def test_07_add_package_extra(self):
        assert set(self.pkg.extras) == set(self.pkg_dict['extras']), self.pkg.extras
        # edit package
        rev = model.repo.new_revision()
        self.pkg.extras[u'key3'] = u'value3'
        model.repo.commit_and_remove()

        try:
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

    def test_08_edit_package_extra(self):
        assert set(self.pkg.extras) == set(self.pkg_dict['extras']), self.pkg.extras
        # edit package
        rev = model.repo.new_revision()
        self.pkg.extras[u'key2'] = u'value2_changed'
        model.repo.commit_and_remove()

        try:
            notification = self.queue_get_one()
            assert notification['operation'] == 'changed', notification['operation']
            assert notification.package['name'] == self.pkg_dict['name'], notification.payload
            extra_keys = set(notification.package['extras'].keys())
            extras = notification.package['extras']
            expected_keys = set((u'key1', u'key2'))
            assert extra_keys == expected_keys, '%s != %s' % (extra_keys, expected_keys)
            assert notification.package['extras']['key2'] == 'value2_changed', notification.package['extras']['key3']
        finally:
            # revert package change
            rev = model.repo.new_revision()
            self.pkg.extras['key2'] = u'value2'
            model.repo.commit_and_remove()


    def test_09_remove_package_extra(self):
        assert set(self.pkg.extras) == set(self.pkg_dict['extras']), self.pkg.extras
        # edit package
        rev = model.repo.new_revision()
        del self.pkg.extras[u'key2']
        model.repo.commit_and_remove()

        try:
            notification = self.queue_get_one()
            assert notification['operation'] == 'changed', notification['operation']
            assert notification.package['name'] == self.pkg_dict['name'], notification.payload
            extra_keys = set(notification.package['extras'].keys())
            expected_keys = set([u'key1'])
            assert extra_keys == expected_keys, '%s != %s' % (extra_keys, expected_keys)
        finally:
            # revert package change
            rev = model.repo.new_revision()
            self.pkg.extras['key2'] = u'value2'
            model.repo.commit_and_remove()
        
    def test_10_add_package_resource(self):
        assert len(self.pkg.as_dict()['resources']) == len(self.pkg_dict['resources']), self.pkg.as_dict()['resources']
        # edit package
        rev = model.repo.new_revision()
        self.pkg.add_resource(u'newurl')
        model.repo.commit_and_remove()

        try:
            notification = self.queue_get_one()
            assert notification['operation'] == 'changed', notification['operation']
            assert notification.package['name'] == self.pkg_dict['name'], notification.payload
            resources = notification.package['resources']
            assert len(resources) == 3
            assert resources[2]['url'] == 'newurl', resources
        finally:
            # revert package change
            rev = model.repo.new_revision()
            del self.pkg.resources[2]
            model.repo.commit_and_remove()

    def test_11_edit_package_resource(self):
        assert len(self.pkg.as_dict()['resources']) == len(self.pkg_dict['resources']), self.pkg.as_dict()['resources']
        # edit package
        rev = model.repo.new_revision()
        self.pkg.resources[0].description = u'edited description'
        model.repo.commit_and_remove()

        try:
            notification = self.queue_get_one()
            assert notification['operation'] == 'changed', notification['operation']
            assert notification.package['name'] == self.pkg_dict['name'], notification.payload
            resources = notification.package['resources']
            assert len(resources) == 2
            assert resources[0]['description'] == u'edited description', resources
        finally:
            # revert package change
            rev = model.repo.new_revision()
            self.pkg.resources[0].description = self.pkg_dict['resources'][0]['description']
            model.repo.commit_and_remove()

    def test_12_remove_package_resource(self):
        assert len(self.pkg.as_dict()['resources']) == len(self.pkg_dict['resources']), self.pkg.as_dict()['resources']
        # edit package
        rev = model.repo.new_revision()
        del self.pkg.resources[0]
        model.repo.commit_and_remove()

        try:
            notification = self.queue_get_one()
            assert notification['operation'] == 'changed', notification['operation']
            assert notification.package['name'] == self.pkg_dict['name'], notification.payload
            resources = notification.package['resources']
            assert len(resources) == 1
        finally:
            # revert package change
            rev = model.repo.new_revision()
            res = self.pkg_dict['resources'][0]
            self.pkg.add_resource(res['url'], description=res['description'])
            model.repo.commit_and_remove()
