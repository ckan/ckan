from pylons import config
from ckan.lib.cli import CkanCommand
from rq import Queue, Connection, Worker
from redis import Redis

from logging import getLogger


class RunTasksCommand(CkanCommand):
    """Run background tasks

    Creates a worker to listen to one or more queues, and then execute
    the jobs that it finds there.

    Usage:
      paster queue               - Listen to high, medium and low queues
      paster queue -n low        - Listen to only low priorty queue
      paster queue -n high,low   - Listen to high and low queues
    """

    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 0

    def __init__(self, name):
        super(RunTasksCommand, self).__init__(name)

        def prep_names(option, opt, value, parser):
            setattr(parser.values, option.dest, value.split(','))

        self.parser.add_option(u'-n', u'--names', type=u'string',
                               action=u'callback',
                               callback=prep_names,
                               default=['low', 'medium', 'high'],
                               help=u'specify queue names to watch',)

    def command(self):
        self._load_config()

        # Can only create a logger *after* loading config.
        self.log = getLogger(__name__)

        connection_url = config.get(u'ckan.queues.url',
                                    u'redis://localhost:6379/0')
        self.log.info(u'Attempting connection to {url}'
            .format(url=connection_url))

        with Connection(Redis.from_url(connection_url)):
            self.log.info(u'Listening to queues => %s', self.options.names)
            qs = [Queue(n) for n in self.options.names]
            w = Worker(qs)
            w.work()
            log.info("Doing work!")
