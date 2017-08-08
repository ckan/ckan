
# Small Media CKAN Notes


1. `vagrant up` should get you a working local install.
2. `vagrant ssh` to login to the vagrant machine.
3. From the `/vagrant` directory (which is the default), run `paster serve /etc/ckan/default/ckan.ini`
4. Visit the app at http://192.168.33.10:5000/

## Working with paster on local

* To create a sysadmin account, run: `paster sysadmin add myusername -c /etc/ckan/default/ckan.ini`
* If you build a new extension remember to run the installation commands before adding it to plugins list in the config file:
  1. `. /home/vagrant/bin/activate` (local) or `. /webapps/iod-ckan/bin/activate` if (staging/live)
  2. `cd ckanext-nameofextension/`
  3. `python setup.py develop`
* To edit your local config file: `sudo vi /etc/ckan/default/ckan.ini`


## Deploy to iod-ckan-live

1. Go to the deploy folder: `cd deploy`
2. Run the deploy script: `ansible-playbook live.yml`

## Working with paster on iod-ckan-live

* Login to `iod-ckan-live`:  `ssh iod-ckan-live.aws.smallmedia.org.uk`
* Switch to the CKAN user: `sudo su - iod-ckan`
* `paster ... /etc/ckan/default/ckan.ini`
