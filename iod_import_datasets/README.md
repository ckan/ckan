# Installing instructions

1. Activate the vagrant environment with `vagrant up`.
2. `vagrant ssh` to login to the vagrant machine.
3. From the `/vagrant` directory (which is the default), run `pip install iod_import_datasets`.
4. Install requirements `pip install -r iod_import_datasets/requirements.txt`


# Using instructions

1. Activate the vagrant environment with `vagrant up`.
2. `vagrant ssh` to login to the vagrant machine.
3. `iodimport [OPTIONS] FILE SHEET REMOTE OWNERORG APIKEY`

## Example

`iodimport "IOD - CKAN (Master sheet).xlsx" "CKAN Upload (Master)" http://192.168.33.10:5000 9c8f2b01-aa98-42f6-8d49-6a839642f2ba 75379c9f-2204-4ea7-b728-872c65a8117b`