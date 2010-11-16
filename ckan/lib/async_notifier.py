import blinker
import time
import logging

from pylons import config
from carrot.connection import BrokerConnection
from carrot.messaging import Publisher
from carrot.messaging import Consumer

from ckan.model import meta
from ckan.model import notifier
from ckan.plugins import SingletonPlugin, implements
from ckan.plugins import IDomainObjectNotification

__all__ = ['EXCHANGE_TYPE', 'get_carrot_connection',
           'AsyncNotifier', 'AsyncConsumer']

logger = logging.getLogger('ckan.async_notifier')

# settings for AMQP
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
    backend = config.get('carrot_messaging_library', 'pyamqplib')
    logger.info("AsyncNotifier using %s backend" % backend)
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
    '''
    Send notifications asynchronously via AMQP, using carrot.
    '''

    @classmethod 
    def publisher(cls):
        if getattr(cls, '_publisher', None) is None or cls._publisher is None:
            cls._publisher = Publisher(connection=get_carrot_connection(),
                                       exchange=config.get('ckan.site_id'),
                                       exchange_type=EXCHANGE_TYPE)
        return cls._publisher

    def send_asynchronously(cls, **notification_dict):
        """
        Send a notification to the AMQP queue
        """
        logger.debug('AsyncNotifier.send_asynchronously: %s',
                     notification_dict)
        try:
            cls.publisher().send(notification_dict,
                                 routing_key=notification_dict['routing_key'])
        except Exception, e:
            # try again, in the case of broken pipe, etc
            logger.exception(e)
            try:
                cls._publisher = None
                cls.publisher().send(notification_dict,
                                    routing_key=notification_dict['routing_key'])
            except: pass


class AMQPDomainObjectNotifier(AsyncNotifier, SingletonPlugin):
    """
    Receive to domain object notifications via IDomainObjectNotification and
    relay them to the AMQP queue.
    """
    implements(IDomainObjectNotification)

    def receive_notification(self, notification):
        self.send_asynchronously(**notification)

class AsyncConsumer(object):
    '''Receive async notifications. (Derive from this class.)
    '''
    def __init__ (self, queue_name, routing_key):
        self.conn = get_carrot_connection()
        self.consumer_options = {
            'exchange': config.get('ckan.site_id'), 
            'exchange_type': EXCHANGE_TYPE,
            'queue': queue_name, 
            'routing_key': routing_key,
            }
        self.consumer = Consumer(connection=self.conn, **self.consumer_options)

    def callback(self, notification):
        '''Derived classes are notified in this method when an async
        notification comes in.'''
        raise NotImplementedError

    def async_callback(self, notification_dict, message):
        '''Called by carrot when a message comes in. It converts the message
        payload to an object and calls self.callback(notification).'''
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

    def run(self, clear_queue=False):
        if clear_queue is True:
            self.clear_queue()
           
        self.consumer.register_callback(self.async_callback)
        # Consumer loop
        # NB wait() is only for test mode - using iterconsume() instead
        logger.info('Queue consumer: Waiting for messages')
        #self.consumer.wait()
        
        it = self.consumer.iterconsume()
        while True:
            try:
                it.next()
            except StopConsuming:
                break
        #    # only need to poll once every few seconds - Queue doesn't block
        #    time.sleep(1.0)
        logger.info('Queue consumer: Shutting down')

    def stop(self):
        # consumer.cancel doesn't work for Queue implementation, so instead
        # send a Stop Message.
        self.consumer.cancel()
        AsyncNotifier.send_asynchronously(None, **notifier.StopNotification.create())
        meta.Session.remove()
        meta.Session.close()

    def clear_queue(self):
        '''Clears all notifications on the queue for this consumer.'''
        self.consumer.discard_all()

