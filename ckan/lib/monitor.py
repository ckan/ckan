from ckan.lib.async_notifier import AsyncConsumer

class Monitor(AsyncConsumer):
    '''Monitor for asynchronous notifications. Prints any notifications.
    NB Doesn\'t work when carrot backend configured to use Python Queue - needs rabbitmq
    or similar.
    '''
    def __init__(self):
        queue_name = 'monitor'
        routing_key = '*'
        super(Monitor, self).__init__(queue_name, routing_key)
        print 'Monitoring notifications'
        print 'Options:'
        options = self.consumer_options.items() + {'host':self.conn.host,
                                                   'userid':self.conn.userid,
                                                   'password':self.conn.password}.items()
        for key, value in options:
            print '    %s: %s' % (key, value)
        print '...'
        self.run()

    def callback(self, notification):
        print '%s: %r\n' % (notification.__class__.__name__, notification['payload'])
