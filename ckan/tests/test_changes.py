import os
import subprocess
import urllib2
import time
import simplejson as json

from pylons import config

import ckan.model as model
from ckan.tests import *

instance_dir = config['here']

class Options:
    pid_file = 'paster.pid'

class TestControllerWithForeign(TestController):

    def system(self, cmd):
        #import commands
        #(status, output) = commands.getstatusoutput(cmd)
        #if status:
        #    raise Exception, "Couldn't execute cmd: %s: %s" % (cmd, output)
        import os
        if os.system(cmd):
            raise Exception, "Couldn't execute cmd: %s" % cmd

    def paster(self, cmd, config_filename):
        config_fpath = os.path.join(instance_dir, config_filename)
        self.system('paster --plugin ckan %s --config=%s' % (cmd, config_fpath))

    def setup(self):
        # setup Server A (sub process)
        self.paster('db clean', 'test_sync.ini')
        self.paster('db init', 'test_sync.ini')
        self.paster('create-test-data', 'test_sync.ini')
        self.sub_proc = subprocess.Popen(['paster', 'serve',
                         os.path.join(instance_dir, 'test_sync.ini')])
        # setup Server B (sub process)
        self.paster('db clean', 'test_sync2.ini')
        self.paster('db init', 'test_sync2.ini')
        self.paster('create-test-data', 'test_sync2.ini')
        self.sub_proc2 = subprocess.Popen(['paster', 'serve',
                        os.path.join(instance_dir, 'test_sync2.ini')])

    def teardown(self):
        #self.sub_proc.kill()  # Only in Python 2.6
        pid = self.sub_proc.pid
        pid = int(pid)
        try:
            if os.system("kill -9 %d" % pid):
                raise Exception, "Can't kill foreign CKAN instance."
        finally:
            pid = self.sub_proc2.pid
            pid = int(pid)
            try:
                if os.system("kill -9 %d" % pid):
                    raise Exception, "Can't kill local CKAN instance."
            finally:
                model.repo.rebuild_db()

    def sub_app_get(self, offset):
        count = 0
        while True:
            try:
                f = urllib2.urlopen('http://localhost:5050%s' % offset)
            except urllib2.URLError, e:
                if hasattr(e, 'reason') and type(e.reason) == urllib2.socket.error:
                    # i.e. process not started up yet
                    count += 1
                    time.sleep(1)
                    assert count < 5, '%s: %r; %r' % (offset, e, e.args)
                else:
                    print 'Error opening url: %s' % offset
                    assert 0, e # Print exception
            else:
                break
        return f.read()


class TestDistributingChanges(TestControllerWithForeign):

    def commit(self):
        self.paster('changes commit', 'test_sync.ini')

    def pull(self):
        self.paster('changes pull', 'test_sync.ini')

    def update(self):
        self.paster('changes update', 'test_sync.ini')

    def test_pull(self):
        self.sub_app_get('/')
        self.app.get('/')
        self.commit()
        self.pull()
        self.update()
        self.make_changeset1()
        self.pull()
        self.update()
        self.make_changeset2()
        self.pull()
        self.update()
        self.make_changeset3()
        self.pull()
        self.update()
        # Todo: Read the entities on the sub app...

    def make_changeset1(self):
        self.create_package(name=u'fordistribution')

    def make_changeset2(self):
        self.update_package(name=u'fordistribution')

    def make_changeset3(self):
        self.update_package(name=u'fordistribution', title="My Title", license_id=u'other-pd')

    def create_package(self, name):
        assert not model.Package.by_name(name)
        offset = url_for(controller='package', action='new')
        res = self.app.get(offset)
        assert 'Packages - New' in res
        fv = res.forms[0]
        prefix = 'Package--'
        fv[prefix + 'name'] = name
        res = fv.submit('commit')
        offset = url_for(controller='package', action='read', id=name)
        res = self.app.get(offset, status=200)
        assert not 'Error' in res, res

    def update_package(self, name, title=u'Test Title', license_id=u'gpl-3.0'):

        offset = url_for(controller='package', action='edit', id=name)
        res = self.app.get(offset, status=200, extra_environ={'REMOTE_USER':'testadmin'})
        assert 'Packages - Edit' in res, res

        version = u'1.1'
        url = u'http://something.com/somewhere.zip'
        resources = (
        #    (u'http://something.com/somewhere-else.xml', u'xml', u'Best', u'hash1'),
            (u'http://something.com/somewhere-else2.xml', u'xml2', u'Best2', u'hash2'),
        )

        assert len(resources[0]) == len(model.PackageResource.get_columns())
        notes = u'Very important'
        state = model.State.ACTIVE
        tags = (u'tag1', u'tag2', u'tag3')
        tags_txt = u' '.join(tags)
        extra_changed = 'key1', 'value1 CHANGED'
        extra_new = 'newkey', 'newvalue'
        log_message = 'This is a comment'
        pkg = model.Package.by_name(name)
        fv = res.forms[0]
        prefix = 'Package-%s-' % pkg.id
        fv[prefix+'name'] = name
        fv[prefix+'title'] = title
        fv[prefix+'version'] = version
        fv[prefix+'url'] = url
        for res_index, resource in enumerate(resources):
            for field_index, res_field in enumerate(model.PackageResource.get_columns()):
                fv[prefix+'resources-%s-%s' % (res_index, res_field)] = resource[field_index]
        fv[prefix+'notes'] = notes
        fv[prefix+'license_id'] = license_id
        fv[prefix+'tags'] = tags_txt
        #fv[prefix+'extras-%s' % extra_changed[0]] = extra_changed[1]
        #fv[prefix+'extras-newfield0-key'] = extra_new[0]
        #fv[prefix+'extras-newfield0-value'] = extra_new[1]
        #fv[prefix+'extras-key3-checkbox'] = True
        fv['log_message'] = log_message

        # Submit
        res = fv.submit('commit', extra_environ={'REMOTE_USER':'testadmin'})
        assert not 'Error' in res, res


