import blinker
import time
import logging

from pylons import config
from carrot.connection import BrokerConnection
from carrot.messaging import Publisher
from carrot.messaging import Consumer

from ckan.model import meta
from ckan.model import notifier

__all__ = ['EXCHANGE', 'EXCHANGE_TYPE', 'get_carrot_connection',
           'AsyncNotifier', 'AsyncConsumer']

logger = logging.getLogger('ckan.async_notifier')

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

    # list of signals That we are subscribed to
    signals = []

    @classmethod 
    def publisher(cls):
        if getattr(cls, '_publisher', None) is None:
            cls._publisher = Publisher(connection=get_carrot_connection(),
                                       exchange=EXCHANGE,
                                       exchange_type=EXCHANGE_TYPE)
        return cls._publisher

    @classmethod
    def send_asynchronously(cls, sender, **notification_dict):
        logger.debug('AsyncNotifier.send_asynchronously: %s %s' % (sender,
            notification_dict))
        cls.publisher().send(notification_dict,
                       routing_key=notification_dict['routing_key'])
        # TODO: sort out whether this is needed
        # cls._publisher.close()

    @classmethod
    def register_signal(cls, signal):
        '''Register AsyncNotifier to receive `blinker` signal (event) (AsyncNotifier will then rebroadcast this using
        asynchronous system).

        :param signal: signal to rebroadcast. Signal *must* have a kwarg
        routing_key used for routing in the AMQP system.
        '''
        if signal not in cls.signals:
            logger.debug('AsyncNotifier.register_signal: %s' % signal)
            signal.connect(cls.send_asynchronously)
            cls.signals.append(signal)


# TODO: move this to model/notifier and use register_signal
# Register AsyncNotifier to receive *synchronous* notifications
for routing_key in notifier.ROUTING_KEYS:
    signal = blinker.signal(routing_key)
    AsyncNotifier.register_signal(signal)

    
class AsyncConsumer(object):
    '''Receive async notifications. (Derive from this class.)
    '''
    def __init__ (self, queue_name, routing_key):
        self.conn = get_carrot_connection()
        self.consumer_options = {
            'exchange':EXCHANGE, 'exchange_type':EXCHANGE_TYPE,
            'queue':queue_name, 'routing_key':routing_key,
            }
        self.consumer = Consumer(connection=self.conn, **self.consumer_options)

    def callback(self, notification):
        raise NotImplementedError

    def run(self, clear_queue=False):
        if clear_queue:
            self.clear_queue()
            
        def callback(notification_dict, message):
            logger.debug('Received message')
            try:
                notification = notifier.Notification.recreate_from_dict(notification_dict)
            except notifier.NotificationError, e:
                logger.error('Notification malformed: %r', e)
            else:
                if isinstance(notification, notifier.StopNotification):
                    raise StopConsuming()
                self.callback(notification)
                message.ack()
           
        self.consumer.register_callback(callback)
        # Consumer loop
        # NB wait() is only for test mode - using iterconsume() instead
        # self.consumer.wait()
        it = self.consumer.iterconsume()
        logger.info('Search indexer: Waiting for messages')
        while True:
            try:
                it.next()
            except StopConsuming:
                break
            # only need to poll once every few seconds?
#            time.sleep(1.0)
        logger.info('Search indexer: Shutting down')

    def stop(self):
        # consumer.cancel doesn't work for Queue implementation, so instead
        # send a Stop Message.
        AsyncNotifier.send_asynchronously(None, **notifier.StopNotification.create())
        meta.Session.remove()
        meta.Session.close()

    def clear_queue(self):
        '''Clears all notifications on the queue for this consumer.'''
        self.consumer.discard_all()
