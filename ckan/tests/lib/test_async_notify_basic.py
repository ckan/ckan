from threading import Thread
import time

from carrot.messaging import Consumer

from ckan.tests import *
from ckan import model
from ckan.lib import async_notifier

class OurConsumer(Thread):
    
    def __init__ (self, conn, queue):
        Thread.__init__(self)
        self.result = None
        self.conn = conn
        self.queue = queue
        conn = self.conn
        self.consumer = Consumer(connection=conn, queue=self.queue,
                            exchange=async_notifier.EXCHANGE, routing_key='importer')

        def import_feed_callback(message_data, message):
            feed_url = message_data['import_feed']
#            print 'GOT SOMETHING'
            self.result = 'Got feed import message for: %s' % feed_url
            # something importing this feed url
            # import_feed(feed_url)
            message.ack()
        self.consumer.register_callback(import_feed_callback)
           
    def run(self):
        self.consumer.wait() # Go into the consumer loop.       
  
class TestQueue:
    def test_basic(self):
        # create connection
        consumer = OurConsumer(async_notifier.get_carrot_connection(), 'feed')
        consumer.daemon = True # so destroyed automatically
        consumer.start()

        # send message
        from carrot.messaging import Publisher
        publisher = Publisher(connection=async_notifier.get_carrot_connection(),
                              exchange=async_notifier.EXCHANGE, routing_key='importer')
        msg = 'ckan.net'
        publisher.send({'import_feed': msg})
        publisher.close()

        time.sleep(0.1)
        assert msg in consumer.result, consumer.result


import blinker

class TestBlinkerOnly:
    def test_01(self):
        event_name = 'my-event'
        # create signal
        signal = blinker.signal(event_name)
        events = []
        def callback_fn(sender, **kwargs):
            events.append([sender, kwargs])
        signal.connect(callback_fn)
        signal.send('abc', xyz='xyz')
        assert events[0] == ['abc', {'xyz': 'xyz'}], events


class TestBlinkerNotifiesAsync:
    event_name = 'Package'
    signal = blinker.signal(event_name)
    routing_key = 'importer'
    message_data = { 'import_feed': 'blah' }

    @classmethod
    def setup_class(self):
        async_notifier.AsyncNotifier.register_signal(self.signal)
        self.queue_name = self.__name__

    def test_01_ourconsumer(self):
        consumer = OurConsumer(async_notifier.get_carrot_connection(),
                self.queue_name)
        self.signal.send(self.event_name, routing_key=self.routing_key,
                **self.message_data)
        message = consumer.consumer.fetch()
        out_message_data = message.payload
        assert 'import_feed' in out_message_data, out_message_data
        assert out_message_data['import_feed'] == self.message_data['import_feed'], out_message_data


    def test_02_asyncconsumer(self):
        consumer = async_notifier.AsyncConsumer(self.queue_name, self.routing_key)

        self.signal.send(self.event_name, routing_key=self.routing_key,
                **self.message_data)
        message = consumer.consumer.fetch()
        out_message_data = message.payload
        assert 'import_feed' in out_message_data, out_message_data
        assert out_message_data['import_feed'] == self.message_data['import_feed'], out_message_data

