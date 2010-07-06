from threading import Thread
import time

from ckan.tests import *
from ckan import model
from ckan.lib import async_notifier

class OurConsumer(Thread):
    
    def __init__ (self, conn):
        Thread.__init__(self)
        self.result = None
        self.conn = conn

    def run(self):
        from carrot.messaging import Consumer
        conn = self.conn
        consumer = Consumer(connection=conn, queue='feed',
                            exchange=async_notifier.EXCHANGE, routing_key='importer')

        def import_feed_callback(message_data, message):
            feed_url = message_data['import_feed']
#            print 'GOT SOMETHING'
            self.result = 'Got feed import message for: %s' % feed_url
            # something importing this feed url
            # import_feed(feed_url)
            message.ack()
           
        consumer.register_callback(import_feed_callback)
        consumer.wait() # Go into the consumer loop.       

      
class TestQueue:
    def test_basic(self):
        # create connection
        consumer = OurConsumer(async_notifier.get_carrot_connection())
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
