import os
import sys

from ckan.lib.commands import CkanCommand


class Celery(CkanCommand):
    '''Celery daemon

    Usage:
        celeryd <run>            - run the celery daemon
        celeryd run concurrency  - run the celery daemon with
                                   argument 'concurrency'
        celeryd view             - view all tasks in the queue
        celeryd clean            - delete all tasks in the queue
    '''
    min_args = 0
    max_args = 2
    summary = __doc__.split('\n')[0]
    usage = __doc__

    def command(self):
        if not self.args:
            self.run_()
        else:
            cmd = self.args[0]
            if cmd == 'run':
                self.run_()
            elif cmd == 'view':
                self.view()
            elif cmd == 'clean':
                self.clean()
            else:
                print 'Command %s not recognized' % cmd
                sys.exit(1)

    def run_(self):
        os.environ['CKAN_CONFIG'] = os.path.abspath(self.options.config)
        from ckan.lib.celery_app import celery
        celery_args = []
        if len(self.args) == 2 and self.args[1] == 'concurrency':
            celery_args.append['--concurrency=1']
        celery.worker_main(argv=['celeryd', '--loglevel=INFO'] + celery_args)

    def view(self):
        self._load_config()
        import ckan.model as model
        from kombu.transport.sqlalchemy.models import Message
        q = model.Session.query(Message)
        q_visible = q.filter_by(visible=True)
        print '%i messages (total)' % q.count()
        print '%i visible messages' % q_visible.count()
        for message in q:
            if message.visible:
                print '%i: Visible' % (message.id)
            else:
                print '%i: Invisible Sent:%s' % (message.id, message.sent_at)

    def clean(self):
        self._load_config()
        import ckan.model as model
        query = model.Session.execute("select * from kombu_message")
        tasks_initially = query.rowcount
        if not tasks_initially:
            print 'No tasks to delete'
            sys.exit(0)
        query = model.Session.execute("delete from kombu_message")
        query = model.Session.execute("select * from kombu_message")
        tasks_afterwards = query.rowcount
        print '%i of %i tasks deleted' % (tasks_initially - tasks_afterwards,
                                          tasks_initially)
        if tasks_afterwards:
            print 'ERROR: Failed to delete all tasks'
            sys.exit(1)
        model.repo.commit_and_remove()
