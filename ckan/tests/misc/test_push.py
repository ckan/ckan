from threading import Thread
import time

from ckan.tests import *

class OurConsumer(Thread):
    def __init__ (self, conn):
        Thread.__init__(self)
        self.result = None
        self.conn = conn

    def run(self):
        from carrot.messaging import Consumer
        conn = self.conn
        consumer = Consumer(connection=conn, queue="feed",
                            exchange="feed", routing_key="importer")

        def import_feed_callback(message_data, message):
            feed_url = message_data["import_feed"]
            print "GOT SOMETHING"
            self.result = "Got feed import message for: %s" % feed_url
            # something importing this feed url
            # import_feed(feed_url)
            message.ack()
           
        consumer.register_callback(import_feed_callback)
        consumer.wait() # Go into the consumer loop.       
      
class TestQueue(TestController):
    def get_conn(self):
        from carrot.connection import BrokerConnection
        return BrokerConnection(hostname="localhost", port=5672,
                                userid="guest", password="guest",
                                virtual_host="/")

    def test_basic(self):
        # create connection
        consumer = OurConsumer(self.get_conn())
        consumer.daemon = True
        consumer.start()

        time.sleep(1)

        # send message
        conn = self.get_conn()
        from carrot.messaging import Publisher
        publisher = Publisher(connection=conn,
                              exchange="feed", routing_key="importer")
        publisher.send({"import_feed": "http://cnn.com/rss/edition.rss"})
        publisher.close()

        for i in range(10):
            print consumer.result

