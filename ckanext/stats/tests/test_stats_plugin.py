import os

from ckan.tests import url_for

from ckanext.stats.tests import StatsFixture

class TestStatsPlugin(StatsFixture):

    def test_01_config(self):
        from pylons import config
        paths = config['extra_public_paths']
        publicdir = os.path.join(os.path.dirname(os.path.dirname(__file__)),
            'public')
        assert paths.startswith(publicdir), (publicdir, paths)

    def test_02_index(self):
        url = url_for('stats')
        out = self.app.get(url)
        assert 'Total number of Datasets' in out, out
        assert 'Most Edited Datasets' in out, out

    def test_03_leaderboard(self):
        url = url_for('stats_action', action='leaderboard')
        out = self.app.get(url)
        assert 'Leaderboard' in out, out

