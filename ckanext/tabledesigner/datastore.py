from ckan.plugins.toolkit import get_action

from ckanext.datastore.backend.postgres import identifier, literal_string

from .column_types import column_types


def create_table(resource_id, info):
    '''
    Set up datastore table + validation
    '''
    primary_key = [(f['id'], f['type']) for f in info if f.get('pk')]

    validate_rules = []
    for colname, typ in primary_key:
        ct = column_types[typ]
        condition = ct.sql_is_empty.format(
            column=f'NEW.{identifier(colname)}'
        )
        validate_rules.append(f'''
IF {condition} THEN
    errors := errors || ARRAY[
        {literal_string(colname)}, 'Primary key must not be empty'
    ];
END IF;
''')

    if validate_rules:
        validate_def = '''
DECLARE
  errors text[] := '{}';
BEGIN
''' + ''.join(validate_rules) + '''
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
            'primary_key': [f for f, typ in primary_key],
            'fields': [{
                'id': i['id'],
                'type': column_types[i['type']].datastore_type,
                'info': {
                    k:v for (k, v) in i.items()
                    if k != 'id' and k != 'type'
                },
            } for i in info],
            'triggers': [
                {'function': f'{resource_id}_tabledesigner_validate'}
            ] if validate_rules else [],
        }
    )
