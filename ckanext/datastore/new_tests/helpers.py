import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories


def create_test_datastore_resource(field_name, field_type, record):
    package = factories.Package.create()
    resource = factories.Resource.create(
        package_id=package['id'], url_type='datastore')
    helpers.call_action(
        'datastore_create',
        resource_id=resource['id'],
        fields=[{'id': field_name, 'type': field_type}, ],
        records=[{field_name: record, }, ],
    )
    return resource['id']

def delete_test_datastore_resource(resource_id):
    helpers.call_action(
        'datastore_delete',
        resource_id=resource_id,
    )
