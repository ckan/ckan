from ckan.plugins.toolkit import get_action

from ckanext.datastore.backend.postgres import identifier, literal_string

from .column_types import column_types
from .helpers import tabledesigner_choice_list


PK_REQUIRED_SQL = '''
IF {condition} THEN
    errors := errors || ARRAY[
        {colname}, 'Primary key must not be empty'
    ];
END IF;
'''

REQUIRED_SQL = '''
IF {condition} THEN
    errors := errors || ARRAY[
        {colname}, 'Missing value'
    ];
END IF;
'''

# \t is used when converting errors to string
CHOICE_CLEAN_SQL = '''
IF {value} IS NOT NULL AND {value} <> '' AND NOT ({value} = ANY ({choices}))
    THEN
    errors := errors || ARRAY[[{colname}, 'Invalid choice: "'
        || replace({value}, E'\t', ' ') || '"']];
END IF;
'''

VALIDATE_DEFINITION_SQL = '''
DECLARE
  errors text[] := '{{}}';
BEGIN
  {validate_rules}
  IF errors = '{{}}' THEN
    RETURN NEW;
  END IF;
  RAISE EXCEPTION E'TAB-DELIMITED\\t%', array_to_string(errors, E'\\t');
END;
'''

def create_table(resource_id, info):
    '''
    Set up datastore table + validation
    '''
    primary_key = []
    validate_rules = []
    for f in info:
        colname, tdtype = f['id'], f['tdtype']
        ct = column_types[tdtype]

        sql = REQUIRED_SQL
        if f.get('pkreq'):
            if f.get('pkreq') == 'pk':
                sql = PK_REQUIRED_SQL
                primary_key.append((colname, tdtype))

            validate_rules.append(sql.format(
                condition=ct.sql_is_empty.format(
                    column=f'NEW.{identifier(colname)}'
                ),
                colname=literal_string(colname),
            ))

        if tdtype == 'choice':
            choices = 'ARRAY[' + ','.join(
                literal_string(c) for c in tabledesigner_choice_list(
                    f.get('choices', '')
                )
            ) + ']'
            validate_rules.append(CHOICE_CLEAN_SQL.format(
                value=f'NEW.{identifier(colname)}',
                colname=literal_string(colname),
                choices=choices,
            ))

    if validate_rules:
        validate_def = VALIDATE_DEFINITION_SQL.format(
            validate_rules = ''.join(validate_rules),
        )
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
                'type': column_types[i['tdtype']].datastore_type,
                'info': {
                    k:v for (k, v) in i.items()
                    if k != 'id'
                },
            } for i in info],
            'triggers': [
                {'function': f'{resource_id}_tabledesigner_validate'}
            ] if validate_rules else [],
        }
    )
