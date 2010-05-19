import sqlalchemy
from pylons import config

from carrot.connection import BrokerConnection
from carrot.messaging import Publisher

__all__ = ['EXCHANGE', 'get_conn', 'Notifier', 'NotifierTrigger']

BACKEND = config.get('messaging_library', 'queue')
EXCHANGE = 'ckan'

# defaults for AMQP
PORT = 5672 
USERID = 'guest'
PASSWORD = 'guest'
HOSTNAME = 'localhost'
VIRTUAL_HOST = '/'

def get_conn():
    backend_cls = 'carrot.backends.%s.Backend' % BACKEND
    return BrokerConnection(hostname=HOSTNAME, port=PORT,
                            userid=USERID, password=PASSWORD,
                            virtual_host=VIRTUAL_HOST,
                            backend_cls=backend_cls)

class Notifier(object):
    allowed_change_types = {
        'Package':('new', 'changed', 'deleted'),
        'Group':('changed', 'packages', 'deleted'),
        'Tag':('changed'),
        'Rating':('changed'),
        }

    @classmethod
    def send(cls, domain_object, change_type):
        object_type = domain_object.__class__.__name__
        assert cls.allowed_change_types.has_key(object_type), object_type
        assert change_type in cls.allowed_change_types[object_type], \
               '%s:%s' % (domain_object, change_type)

        id = domain_object.id if not object_type == 'Tag' \
             else domain_object.name
        routing_key = '%s.%s.%s' % (object_type, id,
                                    change_type)
        publisher = Publisher(connection=get_conn(),
                              exchange=EXCHANGE,
                              routing_key=routing_key)
        publisher.send(domain_object.as_dict())
        publisher.close()
        

class NotifierTrigger(sqlalchemy.orm.interfaces.MapperExtension,
                      Notifier):
    
    def after_insert(self, mapper, connection, instance):
        if instance.__class__.__name__ == 'Package':
            self.send(instance, 'new')

    def after_update(self, mapper, connection, instance):
        if instance.__class__.__name__ in ('Package', 'Group'):
            if instance.state == State.DELETED:
                if instance.all_revisions[1].state != State.DELETED:
                    # i.e. just deleted
                    self.send(instance, 'deleted')
                # no message sent if changed whilst deleted
            else:
                self.send(instance, 'changed')

    
