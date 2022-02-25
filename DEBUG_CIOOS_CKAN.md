# How to debug CKAN python code running in a container

In this tutorial we will examine a way to debug pyhton
code running in a docker container by remotly attaching to a debuger from the host system.

As an example we will debug the plugin.py file in the ckanext-cioos_theme extension. For this example we will use the debugpy module

## Install debugpy in container
to install in the container you can rebuild the image with the latest code
```bash
cd ~/ckan/contrib/docker
sudo docker-compose build ckan
./clean_reload_ckan.sh
sudo docker-compose up -d ckan
```

or install manually in a running container
```bash
sudo docker exec -u root -it ckan /bin/bash
source ../bin/activate; ckan-pip install debugpy
```

## Install debugpy on host
```bash
python -m pip install --upgrade debugpy
python3 -m pip install --upgrade debugpy
python2.7 -m pip install --upgrade debugpy
```

## Add debugpy to file and add at least one breakpoint
with your faverit edit, open `/ckan/contrib/docker/ckanext-cioos_theme/ckanext/cioos_theme/plugin.py`

at top of file, after imports, add
```python
import debugpy
import os
log = logging.getLogger(__name__)

REMOTE_DEBUG = os.environ.get('REMOTE_DEBUG')
if REMOTE_DEBUG and not debugpy.is_client_connected():
    debugpy.listen(('0.0.0.0', 5678))
    log.debug("Waiting for debugger attach")
    debugpy.wait_for_client()
    debugpy.breakpoint()
    log.debug('break on this line')
```

then add the 'REMOTE_DEBUG' enviroment variable to the docker-compose file for
the container you wish to debug

You can add breakpoints from VS Code as well but if you add one to the code the
editor will open the file for you when it hits the breakpoint, which can be handy.

## Open port in docker
You will need to make the port the debugger uses accessible outside the docker
container. To do that we map the port in the docker-compose.yml file. in this case
port 5678.
```bash
cd ~/ckan/contrib/docker
nano docker-compose.yml
```
and uncomment or add the following line to the container definition you want to debug. likely ckan.
```
ports:
   - "5678:5678" # used by the debugger during development. NOT for production
```
## Update CKAN container with new code
To update the container with the new code we can either build a new image:

cd ~/ckan/contrib/docker
sudo docker-compose build ckan
./clean_reload_ckan.sh
sudo docker-compose up -d ckan

Or copy the code into a existing volume
export VOL_CKAN_HOME=`sudo docker volume inspect docker_ckan_home | jq -r -c '.[] | .Mountpoint'`
cd ~/ckan/contrib/docker
sudo cp -r src/ckanext-cioos_theme/ $VOL_CKAN_HOME/venv/src/
sudo docker-compose restart ckan


## Start VS Code and set interpreter to host python2.7 interpreter
https://code.visualstudio.com/docs/python/python-tutorial#_select-a-python-interpreter

## Start CKAN
If CKAN is already running you will need to restart it.
```bash
cd ~/ckan/contrib/docker/
sudo docker-compose up -d ckan
# or
sudo docker-compose restart ckan
```

## Start debugging in VS Code
https://code.visualstudio.com/docs/python/python-tutorial#_configure-and-run-the-debugger
if using the workspace file shown you will be able to pick the `Python: Remote Attach` debug configuration. If this is the first time starting the debuger you will have the option to create a launch.json file or a workspace. Either will work.

### Create workspace
workspace.json
```json
{
	"folders": [
		{
			"path": "../../../../ckan/contrib/docker/src"
		}
	],
	"settings": {
		"python.pythonPath": "/usr/bin/python"
	},
	"launch": {
		"version": "0.2.0",
		"configurations": [
			{
				"name": "Python: Remote Attach",
				"type": "python",
				"request": "attach",
				"connect": {
					"host": "localhost",
					"port": 5678
				},
				"pathMappings": [
					{
						"localRoot": "/home/mfoster/ckan/contrib/docker/src",
						"remoteRoot": "/usr/lib/ckan/venv/src"
					}
				]
			}
		]
	}
}
```

### Create launch.json
launch.json
```json
{
	"version": "0.2.0",
	"configurations": [
		{
			"name": "Python: Remote Attach",
			"type": "python",
			"request": "attach",
			"connect": {
				"host": "localhost",
				"port": 5678
			},
			"pathMappings": [
				{
					"localRoot": "/home/mfoster/ckan/contrib/docker/src",
					"remoteRoot": "/usr/lib/ckan/venv/src"
				}
			]
		}
	]
}
```


# Other IDE's
other IDE's that support remote debugging other then VS codes
- PyCharm
- Visual Studio
- Eclipse
  - https://stackoverflow.com/questions/35066784/how-to-setup-remote-debugging-with-eclipse-and-pydev
