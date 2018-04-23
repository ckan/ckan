import requests

site = 'http://localhost:5000'  # no trailing slash

auth = {'X-CKAN-API-Key': '<API key>'}  # sysadmin api key

data_dict = {'q': '', 'rows': 10000, 'include_private': True}

package_list = requests.post(site + '/api/3/action/package_search',
                             headers=auth, json=data_dict)
packages = package_list.json()['result']['results']

for package in packages:
    d = {'id': package['name']}
    show = requests.post(site + '/api/3/action/package_show',
                         headers=auth, json=d)

    data = {'package': show.json()['result']}
    views = requests.post(
        site + '/api/3/action/package_create_default_resource_views',
        headers=auth, json=data)

    data_in_ds = {'package': show.json()['result'], 'create_datastore_views': True }
    views = requests.post(
        site + '/api/3/action/package_create_default_resource_views',
        headers=auth, json=data_in_ds)
