import subprocess

class TestVersions(object):

    no_db = True

    def test_pylons(self):
        p = subprocess.Popen(
                'pip freeze | grep Pylons', shell=True,
                stdout=subprocess.PIPE)
        pylons_version = p.communicate()[0].strip()
        assert pylons_version == "Pylons==0.9.7"
