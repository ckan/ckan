import requests
import json

site = 'http://localhost:5000'
auth = {'X-CKAN-API-Key': '<API KEY>'}  # sysadmin api key
data_dict = {'q': '', 'rows': 10000, 'include_private': True}
sysadmin = '<sysadmin>' # sysadmin username

package_list = requests.post(site + '/api/3/action/package_search',
                             headers=auth, json=data_dict)
packages = package_list.json()['result']['results']

for package in packages:
    d = {'id': package['name']}
    print 'Package: ', package['name']
    show = requests.post(site + '/api/3/action/package_show',
                         headers=auth, json=d)
    resources = show.json()['result']['resources']

    for r in resources:
    	if r['datastore_active'] == True:
            print 'Uploading resource:', r['id']
            upload_resource = requests.post(site + '/api/3/action/datapusher_submit',
                                            headers=auth,
                                            json={'user': sysadmin,
                                            'resource_id': r['id'],
                                            'ignore_hash': 'True'})
            print upload_resource
        else:
            print 'Updating resource: ', r['id']
            update_resource = requests.post(site + '/api/3/action/update_resource',
                                            headers=auth,
                                            json=r)
            print update_resource
