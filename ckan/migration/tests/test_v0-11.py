# must be outside of tests since that sets some stuff up
import os
import pylons

from sqlalchemy import *

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
        out = model.Session.query(model.Package).all()
        print len(out)
        assert len(out) == 254

    def test_revisions(self):
        revs = model.Session.query(model.Revision).all()
        assert len(revs) == 1586, len(revs)
        revs = model.repo.history()
        assert len(revs) == 693, len(revs)

    def test_tags(self):
        tags = model.Session.query(model.Tag).all()
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
        keys = model.Session.query(model.ApiKey).all()
        assert len(keys) == 3, len(keys)
        assert 'johnbywater' in keys[0].name

    def test_license(self):
        lics = model.Session.query(model.License).all()
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

        model.repo.upgrade_db(8)
        dbversion = mig.db_version(model.metadata.bind.url,
                model.repo.migrate_repository)
        assert dbversion == 8, dbversion
        model.Session.remove()

    @classmethod
    def teardown_class(self):
        pass

    def test_1(self):
        revs = model.Session.query(model.Revision).all()
        assert len(revs) == 2
        rev = revs[-1]
        assert len(rev.id) == 36, rev

        pkgs = model.Session.query(model.Package).all()
        for pkg in pkgs:
            assert pkg.revision_id == revs[1].id or pkg.revision_id == revs[0].id, '%s!=%s' % (pkg.revision_id, revs[0].id)
            assert pkg.revision == revs[0] or pkg.revision == revs[1]

def set_version(version):
    vtable = model.version_table
    update = vtable.update(values={'version': version})
    model.metadata.bind.execute(update)
    check_version(version)

def check_version(version):
    import migrate.versioning.api as migrate
    dbversion = migrate.db_version(model.metadata.bind.url,
            model.repo.migrate_repository)
    assert dbversion == version, dbversion

class TestMigrate09(object):
    # NB Run this with model code still at v8
    @classmethod
    def setup_class(self):
        from ckan.lib.cli import CreateTestData

        model.repo.rebuild_db()
        CreateTestData.create() # assumes model code at v8
        set_version(8)
        
        model.repo.upgrade_db(9)
        check_version(9)

    def test_1(self):
        # Now run this with model code at v9
        users = model.Session.query(model.User).all()
        assert users
        for user in users:
            assert user.created

        model.Session.remove()
    
class TestMigrate10(object):
    # NB Run this with model code still at v9
    @classmethod
    def setup_class(self):
        from ckan.lib.cli import CreateTestData

        model.repo.rebuild_db()
        CreateTestData.create() # assumes model code at v9
        set_version(9)
        
        model.repo.upgrade_db(10)
        check_version(10)

##    def test_1(self):
##        user = Table('user', metadata, autoload=True)
##        rows = migrate_engine.execute(user.select())
##        for row in rows:
##            assert 'about' in row.keys(), row


"""Here's how to run TestMigrate11 tests:
cd ckan/model
hg up dbd159e52a7b
cd ../..
paster db clean && paster db init
nosetests test_migrate.py:TestMigrate11A
cd ckan/model
hg up
cd ../..
nosetests test_migrate.py:TestMigrate11B
"""
class TestMigrate11A(object):
    # NB Run this part with model code still at v10
    @classmethod
    def setup_class(self):
        from ckan.lib.cli import CreateTestData

        model.repo.rebuild_db()
        CreateTestData.create() # assumes model code at v10

        set_version(10)
        model.repo.upgrade_db(11)
        check_version(11)

class TestMigrate11B(object):
    # NB Run this part with model code at v11
    def test_0_basic(self):
        from ckan.lib.search import Search, SearchOptions
        result = Search().search(u'annakarenina')
        assert result['count'] == 1, result
        assert 'annakarenina' in result['results'], result['results']

    def test_1_notes(self):
        from ckan.lib.search import Search, SearchOptions
        result = Search().search(u'italicized')
        assert result['count'] == 1, result
        assert 'annakarenina' in result['results'], result['results']
        
