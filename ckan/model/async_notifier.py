from pylons import config
import blinker
from carrot.connection import BrokerConnection
from carrot.messaging import Publisher
from carrot.messaging import Consumer

import notifier
import meta

__all__ = ['EXCHANGE', 'get_carrot_connection',
           'AsyncNotifier', 'AsyncConsumer']

# settings for AMQP
BACKEND = config.get('carrot_messaging_library', 'queue')
EXCHANGE = 'ckan'

# defaults for AMQP
PORT = 5672 
USERID = 'guest'
PASSWORD = 'guest'
HOSTNAME = 'localhost'
VIRTUAL_HOST = '/'

def get_carrot_connection():
    backend_cls = 'carrot.backends.%s.Backend' % BACKEND
    return BrokerConnection(hostname=HOSTNAME, port=PORT,
                            userid=USERID, password=PASSWORD,
                            virtual_host=VIRTUAL_HOST,
                            backend_cls=backend_cls)

class AsyncNotifier(object):
    @classmethod
    def send_asynchronously(cls, sender, **notification_dict):
        publisher = Publisher(connection=get_carrot_connection(),
                              exchange=EXCHANGE,
                              routing_key=notification_dict['routing_key'])
        publisher.send(notification_dict)
        publisher.close()

# Register AsyncNotifier to receive synchronous notifications
signals = []
for routing_key in notifier.ROUTING_KEYS:
    signal = blinker.signal(routing_key)
    signal.connect(AsyncNotifier.send_asynchronously)
    signals.append(signal)

    
class AsyncConsumer(object):
    '''Receive async notifications. (Derive from this class.)
    '''
    def __init__ (self, queue_name, routing_key):
        self.conn = get_carrot_connection()
        self.consumer_options = {
            'queue':queue_name, 'exchange':EXCHANGE,
            'routing_key':routing_key}

    def callback(self, notification):
        raise NotImplementedError

    def run(self):
        self.consumer = Consumer(connection=self.conn, **self.consumer_options)

        def callback(notification_dict, message):
            notification = Notification.recreate_from_dict(notification_dict)
            self.callback(notification)
            message.ack()
           
        self.consumer.register_callback(self.callback)
        # Consumer loop
        while self.consumer.iterconsume():
            pass
        print "Search indexer shutting down"
#        self.consumer.wait() # Go into the consumer loop.

    def session_remove(self):
        meta.Session.remove()
