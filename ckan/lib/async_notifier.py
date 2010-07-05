from pylons import config
import blinker
from carrot.connection import BrokerConnection
from carrot.messaging import Publisher
from carrot.messaging import Consumer

import notifier
import meta

__all__ = ['EXCHANGE', 'EXCHANGE_TYPE', 'get_carrot_connection',
           'AsyncNotifier', 'AsyncConsumer']

# settings for AMQP
EXCHANGE = 'ckan'
EXCHANGE_TYPE = 'topic'

# defaults for AMQP
PORT = 5672 
USERID = 'guest'
PASSWORD = 'guest'
HOSTNAME = 'localhost'
VIRTUAL_HOST = '/'

class StopConsuming(Exception):
    pass

def get_carrot_connection():
    backend = config.get('carrot_messaging_library', 'queue')
    try:
        port = int(config.get('amqp_port', PORT))
    except ValueError:
        port = PORT
    userid = config.get('amqp_user_id', USERID)
    password = config.get('amqp_password', PASSWORD)
    hostname = config.get('amqp_hostname', HOSTNAME)
    virtual_host = config.get('amqp_virtual_host', VIRTUAL_HOST)
    backend_cls = 'carrot.backends.%s.Backend' % backend
    return BrokerConnection(hostname=hostname, port=port,
                            userid=userid, password=password,
                            virtual_host=virtual_host,
                            backend_cls=backend_cls)
    

class AsyncNotifier(object):
    '''Sends out notifications asynchronously via carrot.
    Receives notifications via blinker (synchronously).'''
    _publisher = None

    @classmethod
    def send_asynchronously(cls, sender, **notification_dict):
        if cls._publisher == None:
            cls._publisher = Publisher(connection=get_carrot_connection(),
                                       exchange=EXCHANGE,
                                       exchange_type=EXCHANGE_TYPE)
        print 'SEND', notification_dict['operation'], notification_dict['routing_key']
        cls._publisher.send(notification_dict,
                       routing_key=notification_dict['routing_key'])
#        cls._publisher.close()

# Register AsyncNotifier to receive *synchronous* notifications
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
            'exchange':EXCHANGE, 'exchange_type':EXCHANGE_TYPE,
            'queue':queue_name, 'routing_key':routing_key,
            }

    def callback(self, notification):
        raise NotImplementedError

    def run(self, clear_queue=False):
        self.consumer = Consumer(connection=self.conn, **self.consumer_options)
        if clear_queue:
            self.clear_queue()
            
        def callback(notification_dict, message):
            print "MESSAGE"
            notification = notifier.Notification.recreate_from_dict(notification_dict)
            if isinstance(notification, notifier.StopNotification):
                raise StopConsuming()
            self.callback(notification)
            message.ack()
           
        self.consumer.register_callback(callback)
        # Consumer loop
##        self.consumer.wait()
        it = self.consumer.iterconsume()
        print 'Search indexer: Waiting for messages'
        while True:
            try:
                it.next()
            except StopConsuming:
                break
        print 'Search indexer: Shutting down'

    def stop(self):
        # consumer.cancel doesn't work for Queue implementation, so instead
        # send a Stop Message.
        AsyncNotifier.send_asynchronously(None, **notifier.StopNotification.create())
        meta.Session.remove()
        meta.Session.close()

    def clear_queue(self):
        '''Clears all notifications on the queue for this consumer.'''
        self.consumer.discard_all()
