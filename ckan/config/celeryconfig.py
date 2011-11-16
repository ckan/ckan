## Example celery config

## It is recommended that this file be put in the /path/to/virtualenv/bin directory.  This way it will definitely get picked up by ckan and the deamons.

#Broker can be whatever you like but can be ckan database too.
BROKER_BACKEND = "sqlalchemy"
BROKER_HOST = "postgres://ckan:pass@localhost/ckan.net"


#Results backend should be the same as where the ckan database is.
CELERY_RESULT_DBURI = "postgres://ckan:pass@localhost/ckan.net"
CELERY_RESULT_BACKEND = "database"
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_SERIALIZER = 'json'



#Inports of all the tasks you need. TODO add extension point to add these.
CELERY_IMPORTS = ('ckanext.archiver.tasks', 'ckanext.webstorer.tasks')
