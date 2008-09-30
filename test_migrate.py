# must be outside of tests since that sets some stuff up
import os
import pylons

def load_config(filename):
    print 'loading ...'
    from paste.deploy import appconfig
    from ckan.config.environment import load_environment
    conf = appconfig('config:' + filename)
    load_environment(conf.global_conf, conf.local_conf)

load_config(os.path.abspath('test.ini'))
import ckan.model as model
import commands

class TestMigrateTo0Point7(object):

    @classmethod
    def setup_class(self):
        # dburi = pylons.config['sqlobject.dburi']
        dbname = 'ckantest'
        dbpass = 'pass'
        dbuser = 'ckantest'
        dump_path = os.path.abspath('migrate/ckan.sql')
        model.repo.rebuild()
        cmd = 'psql -h localhost --quiet --file %s --user %s --password %s' % (dump_path, dbuser, dbname)
        # os.system(cmd)
        status, output = commands.getstatusoutput(cmd)
        # new_wsgiapp = loadapp('config:test.ini', relative_to=conf_dir)
        # old_wsgiapp = loadapp('config:old.ini', relative_to=conf_dir)
        # self.app = paste.fixture.TestApp(wsgiapp)
        # run migrate ...

    def test_rest_api(self):
        pass

    def test_model_1(self):
        # model.Package.
        out = list(model.Package.select())
        print len(out)
        assert len(out) == 253
        revs = list(model.Revision.select())
        assert len(revs) == 0


