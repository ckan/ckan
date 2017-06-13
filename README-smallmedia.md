
# Small Media cKan Notes


1. `vagrant up` should get you a working local install.
1. `vagrant ssh` to login to the vagrant machine.
1. From the `/vagrant` directory (which is the default), run `paster serve /etc/ckan/default/ckan.ini`
1. Visit the app at http://192.168.33.10:5000/

To create a sysadmin account, run: `paster sysadmin add myusername`



## Deploy to iod-ckan-live

`cd deploy ; ansible-playbook live.yml`



## Working with paster on iod-ckan-live

* Login to `iod-ckan-live`:  `ssh iod-ckan-live.aws.smallmedia.org.uk`
* Switch to the CKAN user: `sudo su - iod-ckan`
* `paster ... /etc/ckan/default/ckan.ini`
