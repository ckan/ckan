## This plugin is to enable PyCharm remote debugging in CKAN

### Installation

1. On your CKAN instance, install the required Python packages:
```bash
pip -r requirements.txt
```
or what matches your pycharm client version:
```bash
pydevd-pycharm~=241.18034.82
```
2. Add the following lines to your CKAN configuration file (usually `ckan.ini` ):
```ini
ckan.plugins = pycharm_debugger
debug.remote = True
```
Optionally update remote debugger server ip/host. See plugin.py for more config options
```ini
debug.remote.host.ip = host.docker.internal
```
3. Ensure that pycharm remote debugging server is running on port `5678` (default) '
4. Start CKAN
```bash
  cd test-infrasturcture
  docker compose exec ckan  ckan -c ckan.ini run -H 0.0.0.0
```

If you wish to use in pytest, place the following above your test class
```python
  @pytest.mark.ckan_config(u'ckan.plugins', u'pycharm_debugger')
```
