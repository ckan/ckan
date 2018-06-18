# encoding: utf-8

import os
import subprocess
import urllib2
import time

from ckan.common import config

import ckan.model as model
from ckan.tests.legacy import *
from ckan.lib.create_test_data import CreateTestData
from ckan.common import json

instance_dir = config['here']

class Options:
    pid_file = 'paster.pid'

# TODO: Reenable this when sync functionality is in place
class _TestSync(TestController):
    @classmethod
    def setup_class(self):
        # setup Server A (sub process)
        subprocess.call('paster db clean --config=test_sync.ini', shell=True)
        subprocess.call('paster db init --config=test_sync.ini', shell=True)
        subprocess.call('paster create-test-data --config=test_sync.ini', shell=True)
        self.sub_proc = subprocess.Popen(['paster', 'serve', 'test_sync.ini'])
        # setup Server B (this process)
        # (clean)

        self._last_synced_revision_id = {'http://localhost:5050':None}

    @classmethod
    def teardown_class(self):
        self.sub_proc.kill()
        model.repo.rebuild_db()

    def sub_app_get(self, offset):
        count = 0
        while True:
            try:
                f = urllib2.urlopen('http://localhost:5050%s' % offset)
            except urllib2.URLError as e:
                if hasattr(e, 'reason') and type(e.reason) == urllib2.socket.error:
                    # i.e. process not started up yet
                    count += 1
                    time.sleep(1)
                    assert count < 5, '%s: %r; %r' % (offset, e, e.args)
                else:
                    print('Error opening url: %s' % offset)
                    assert 0, e  # Print exception
            else:
                break
        return f.read()

    def sub_app_get_deserialized(offset):
        res = sub_app_get(offset)
        if res == None:
            return None
        else:
            return json.loads(res)

    def test_1_first_sync(self):
        server = self._last_synced_revision_id.keys()[0]
        assert server == 'http://localhost:5050'

        # find id of last revision synced
        last_sync_rev_id = self._last_synced_revision_id[server]
        assert last_sync_rev_id == None # no syncs yet

        # get revision ids since then
        remote_rev_ids = self.sub_app_get_deserialized('%s/api/search/revision?since=%s' % (server, last_sync_rev_id))
        assert len(remote_rev_ids) == 3
        remote_latest_rev_id = remote_rev_ids[-1]

        # get revision diffs
        diffs = self.sub_app_get_deserialized('%s/api/diff/revision?diff=%s&oldid=%s' % (server, remote_latest_rev_id, last_sync_rev_id))
        assert len(diffs) == 3

        # apply diffs
