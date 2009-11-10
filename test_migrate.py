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
        # os.system(cmd)
        # status, output = commands.getstatusoutput(cmd)
        # new_wsgiapp = loadapp('config:test.ini', relative_to=conf_dir)
        # old_wsgiapp = loadapp('config:old.ini', relative_to=conf_dir)
        # self.app = paste.fixture.TestApp(wsgiapp)
        # run migrate ...

    def test_packages(self):
        out = model.Package.query.all()
        print len(out)
        assert len(out) == 254

    def test_revisions(self):
        revs = model.Revision.query.all()
        assert len(revs) == 1586, len(revs)
        revs = model.repo.history()
        assert len(revs) == 693, len(revs)

    def test_tags(self):
        tags = model.Tag.query.all()
        assert len(tags) == 560, len(tags)

    def test_package_continuity(self):
        name = u'geonames'
        pkg = model.Package.by_name(name)
        assert pkg.name == name
        assert pkg.url == u'http://www.geonames.org/export/', pkg
        assert pkg.download_url == u'http://download.geonames.org/export/dump/allCountries.zip'
        assert len(pkg.tags) == 7, pkg.tags

    def test_package_revisions(self):
        name = u'geonames'
        pkg = model.Package.by_name(name)
        pkgrevs = pkg.all_revisions
        assert len(pkgrevs) == 4, len(pkgrevs)
        assert pkgrevs[0].revision.timestamp.year == 2007
        assert pkgrevs[-1].revision.timestamp.year == 2008
        assert pkgrevs[0].name == name, pkgrevs[0]
        assert pkgrevs[-1].name == name
        assert pkgrevs[0].download_url == None

    def test_api_key(self):
        keys = model.ApiKey.query.all()
        assert len(keys) == 3, len(keys)
        assert 'johnbywater' in keys[0].name

    def test_license(self):
        lics = model.License.query.all()
        assert len(lics) == 63, len(lics)


class TestMigrate08(object):
    @classmethod
    def setup_class(self):
        from ckan.lib.cli import CreateTestData
        import migrate.versioning.api as mig

        model.repo.rebuild_db()
        CreateTestData.create()

        vtable = model.version_table
        update = vtable.update(values={'version': 7})
        model.metadata.bind.execute(update)
        dbversion = mig.db_version(model.metadata.bind.url,
                model.repo.migrate_repository)
        assert dbversion == 7, dbversion

        model.repo.upgrade_db()
        dbversion = mig.db_version(model.metadata.bind.url,
                model.repo.migrate_repository)
        assert dbversion == 8, dbversion
        model.Session.remove()

    @classmethod
    def teardown_class(self):
        pass

    def test_1(self):
        revs = model.Revision.query.all()
        assert len(revs) == 2
        rev = revs[-1]
        assert len(rev.id) == 36, rev

        pkgs = model.Package.query.all()
        for pkg in pkgs:
            assert pkg.revision_id == rev.id
            assert pkg.revision == rev

