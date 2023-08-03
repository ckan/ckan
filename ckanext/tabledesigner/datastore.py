from ckan.plugins.toolkit import get_action

from ckanext.datastore.backend.postgres import identifier, literal_string

from .column_types import column_types


def create_table(resource_id, info):
    '''
    Set up datastore table + validation
    '''
    primary_key = [(f['id'], f['tdtype']) for f in info if f.get('pk')]

    validate_rules = []
    for colname, tdtype in primary_key:
        ct = column_types[tdtype]
        condition = ct.sql_is_empty.format(
            column='NEW.{0}'.format(identifier(colname))
        )
        validate_rules.append('''
IF {0} THEN
    errors := errors || ARRAY[
        {1}, 'Primary key must not be empty'
    ];
END IF;
'''.format(condition, literal_string(colname)))

    if validate_rules:
        validate_def = u'''
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
                'name': u'{0}_tabledesigner_validate'.format(resource_id),
                'or_replace': True,
                'rettype': u'trigger',
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
                'type': column_types[i['tdtype']].datastore_type,
                'info': {
                    k:v for (k, v) in i.items()
                    if k != 'id'
                },
            } for i in info],
            'triggers': [
                {'function': u'{0}_tabledesigner_validate'.format(resource_id)}
            ] if validate_rules else [],
        }
    )
