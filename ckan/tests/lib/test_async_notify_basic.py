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
                            exchange='ckan', routing_key='importer')

        def import_feed_callback(message_data, message):
            if not message_data.has_key('import_feed'):
                print 'Badly formatted message:', message
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
    '''Basic demo of async messaging. This works standalone only. It
    doesn\'t close its thread properly, so if you run it in the sequence
    of all the tests, then subsequent ones with messages don\'t run
    successfully.'''
    def _test_basic(self):
        # create connection
        consumer = OurConsumer(async_notifier.get_carrot_connection(), 'feed')
        consumer.daemon = True # so destroyed automatically
        consumer.start()

        # send message
        from carrot.messaging import Publisher
        publisher = Publisher(connection=async_notifier.get_carrot_connection(),
                              exchange='ckan', routing_key='importer')
        msg = 'ckan.net'
        publisher.send({'import_feed': msg})
        publisher.close()

        time.sleep(0.5)
        assert msg in consumer.result, consumer.result

