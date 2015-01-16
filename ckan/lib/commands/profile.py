import os

from paste.script.util.logging_config import fileConfig

from ckan.lib.commands import CkanCommand


class Profile(CkanCommand):
    '''Code speed profiler
    Provide a ckan url and it will make the request and record
    how long each function call took in a file that can be read
    by runsnakerun.

    Usage:
       profile URL

    e.g. profile /data/search

    The result is saved in profile.data.search
    To view the profile in runsnakerun:
       runsnakerun ckan.data.search.profile

    You may need to install python module: cProfile
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 1

    def _load_config_into_test_app(self):
        from paste.deploy import loadapp
        import paste.fixture
        if not self.options.config:
            msg = 'No config file supplied'
            raise self.BadCommand(msg)
        self.filename = os.path.abspath(self.options.config)
        if not os.path.exists(self.filename):
            raise AssertionError('Config filename %r does not exist.' %
                                 self.filename)
        fileConfig(self.filename)

        wsgiapp = loadapp('config:' + self.filename)
        self.app = paste.fixture.TestApp(wsgiapp)

    def command(self):
        self._load_config_into_test_app()

        import paste.fixture
        import cProfile
        import re

        url = self.args[0]

        def profile_url(url):
            try:
                self.app.get(url, status=[200],
                             extra_environ={'REMOTE_USER': 'visitor'})
            except paste.fixture.AppError:
                print 'App error: ', url.strip()
            except KeyboardInterrupt:
                raise
            except:
                import traceback
                traceback.print_exc()
                print 'Unknown error: ', url.strip()

        output_filename = 'ckan%s.profile' % re.sub('[/?]', '.',
                                                    url.replace('/', '.'))
        profile_command = "profile_url('%s')" % url
        cProfile.runctx(profile_command, globals(), locals(),
                        filename=output_filename)
        print 'Written profile to: %s' % output_filename
