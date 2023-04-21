from ckan.plugins.toolkit import get_action

from ckanext.datastore.backend.postgres import identifier, literal_string


def create_table(resource_id, info):
    '''
    Set up datastore table + validation
    '''
    primary_key = [f['id'] for f in info if f.get('pk')]

    validate_def = None
    if primary_key:
        validate_def = '''
DECLARE
  errors text[] := '{}';
BEGIN
''' + ''.join(f'''
  IF (NEW.{identifier(f)} = '') IS NOT FALSE THEN
    errors := errors || ARRAY[{literal_string(f)}, 'Primary key must not be empty'];
  END IF;
''' for f in primary_key) + '''
  IF errors = '{}' THEN
    RETURN NEW;
  END IF;
  RAISE EXCEPTION E'TAB-DELIMITED\\t%', array_to_string(errors, E'\\t');
END;
'''
        get_action('datastore_function_create')(
            {
                'ignore_auth': True,
            },
            {
                'name': f'{resource_id}_tabledesigner_validate',
                'or_replace': True,
                'rettype': 'trigger',
                'definition': validate_def,
            }
        )

    get_action('datastore_create')(
        None, {
            'resource_id': resource_id,
            'force': True,
            'primary_key': primary_key,
            'fields': [{
                'id': i['id'],
                'type': i['type'],
                'info': {
                    k:v for (k, v) in i.items()
                    if k != 'id' and k != 'type'
                },
            } for i in info],
            'triggers': [
                {'function': f'{resource_id}_tabledesigner_validate'}
            ] if validate_def else [],
        }
    )

