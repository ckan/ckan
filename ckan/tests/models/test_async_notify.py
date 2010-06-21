from threading import Thread
import time

from carrot.messaging import Consumer

from ckan.tests import *
from ckan import model
from ckan.lib.helpers import json
from ckan.lib.create_test_data import CreateTestData

class RecordingConsumer(Thread):
    '''As a consumer, this thread creates a queue and records what is put
    on it.
    '''
    def __init__ (self, conn, queue='recorder', routing_key='*'):
        Thread.__init__(self)

        self.conn = conn
        self.consumer_options = {
            'queue':queue, 'exchange':model.EXCHANGE, 'routing_key':routing_key}
        self.clear()

    def run(self):
        conn = self.conn
        self.consumer = Consumer(connection=self.conn, **self.consumer_options)

        def callback(notification_dict, message):
            notification = model.Notification.recreate_from_dict(notification_dict)
            self.queued.append(notification)
            message.ack()
           
        self.consumer.register_callback(callback)
        self.consumer.wait() # Go into the consumer loop.

    def clear(self):
        self.queued = []

    def stop(self):
        self.consumer.cancel()
      

class TestNotification(TestController):
    @classmethod
    def setup_class(self):
        # create notification consumer
        self.consumer = RecordingConsumer(model.get_carrot_connection())
        self.consumer.daemon = True # so destroyed automatically
        self.consumer.start()

        self.pkg_names = []

    @classmethod
    def teardown_class(self):
        self.consumer.stop()
        self.purge_packages(self.pkg_names)
        CreateTestData.delete()

    def tearDown(self):
        self.consumer.clear()

    def usher_message_sending(self):
        '''This is a simple way to block the current thread briefly to
        allow the consumer thread to process a message. Since
        these tests use Python Queue then the queue thread should pass the
        message immediately. Should this not work or become intermittent
        on some machines then we should rethink this.'''
        time.sleep(0.1)

    def queue_get_one(self):
        assert len(self.consumer.queued) == 1, self.consumer.queued
        notification = self.consumer.queued[0]
        assert isinstance(notification, model.PackageNotification), notification
        return notification

    def test_new_package(self):
        # create package
        name = u'testpkg'
        CreateTestData.create_arbitrary([{'name':name}])
        self.pkg_names.append(name)

        self.usher_message_sending()
                                        
        notification = self.queue_get_one()
        assert notification.package['name'] == name, notification.payload

    def test_new_package_and_permissions(self):
        # create package
        name = u'testpkg2'
        # creasts package and default permission objects
        CreateTestData.create_arbitrary([{'name':name}])

        self.usher_message_sending()
                                        
        notification = self.queue_get_one()
        assert notification.package['name'] == name, notification.payload

