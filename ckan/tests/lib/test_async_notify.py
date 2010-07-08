from threading import Thread
import time

from carrot.messaging import Consumer

from ckan.tests import *
from ckan import model
from ckan.lib import async_notifier
from ckan.lib.helpers import json
from ckan.lib.create_test_data import CreateTestData


class TestNotification(TestController):
    @classmethod
    def setup_class(self):
        self.queue_name = 'recording_consumer'
        self.routing_key = '*'
        self.consumer = async_notifier.AsyncConsumer(self.queue_name, self.routing_key)

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

    @classmethod
    def teardown_class(self):
        CreateTestData.delete()

    @property
    def pkg(self):
        return model.Package.by_name(self.pkg_dict['name'])

    def queue_get_one(self):
        message = self.consumer.consumer.fetch()
        if message:
            message.ack()
        self.consumer.consumer.close()
        notification = model.Notification.recreate_from_dict(message.payload)
        assert isinstance(notification, model.PackageNotification), notification
        return notification

    def clear_queue(self):
        self.consumer.consumer.discard_all()
        self.consumer.consumer.close()

    def test_01_new_package(self):
        # manually create package so no auth objects created
        self.clear_queue()
        name = u'testpkg'
        rev = model.repo.new_revision() 
        pkg = model.Package(name=name)
        model.Session.add(pkg)
        model.repo.commit_and_remove()
        CreateTestData.flag_for_deletion([name])

        notification = self.queue_get_one()
        print notification
        assert notification.package['name'] == name, notification

    def test_02_new_package_and_permissions(self):
        # create package
        name = u'testpkg2'
        # creasts package and default permission objects
        CreateTestData.create_arbitrary([{'name':name}])
        notification = self.queue_get_one()
        assert notification['operation'] == 'new', notification['operation']
        assert notification.package['name'] == name, notification

