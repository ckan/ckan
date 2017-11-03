# Installing extension

1. Activate the vagrant environment with `vagrant up`.
2. `vagrant ssh` to login to the vagrant machine.
3. From the `/vagrant` directory (which is the default), run:
    1. `. /home/vagrant/bin/activate` (local) or `. /webapps/iod-ckan/bin/activate` (staging/live)
    2. `cd ckanext-nameofextension/`
    3. `python setup.py develop`

# Using script

* `iodimport [OPTIONS] FILE SHEET REMOTE OWNERORG APIKEY`
    * FILE: export spreasheet and add to project folder
    * SHEET: declare with sheet to use if the spreadsheet has multiple ones
    * OWNERORG: You can find the ID of the organization via the API: 'http://[urloftheproject]/api/action/organization_show?id=[nameoforganization]'
    * APIKEY: API key of the user that can be found checking your user profile: 'http://[urloftheproject]/en/user/[username]'