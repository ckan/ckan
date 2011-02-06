from nose.plugins import Plugin
from inspect import isclass
import os


class CkanNose(Plugin):

    def startContext(self, ctx):

        #import needs to be here or setup happens too early
        import ckan.model as model
        #this is run at the start of every class
        if isclass(ctx):
            model.repo.init_db()

    def options(self, parser, env):
        parser.add_option(
                        "--ckan_ini", action="store", dest="ckan_ini",
                        default = None,
                        help="specify the ckan ini file you want to use")

    def configure(self, options, config):
        self.options = options
        # try and make sure plugin only runs for ckan tests 
        if options.ckan_ini or 'ckan' in os.getcwd().split("/"):
            self.enabled = True

    def begin(self):
        from ckan.tests import setup_tests
        setup_tests(self.options.ckan_ini)

