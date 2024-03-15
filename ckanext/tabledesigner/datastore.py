from ckan.plugins.toolkit import get_action, h


VALIDATE_DEFINITION_SQL = u'''
<<validation>>
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


def create_table(resource_id, fields):
    '''
    Set up datastore table + validation
    '''
    primary_key = []
    validate_rules = []
    for f in fields:
        ct = h.tabledesigner_column_type(f)

        if f['tdpkreq'] == 'pk':
            primary_key.append(ct.colname)

        col_validate = ct.sql_validate_rule()
        if col_validate:
            validate_rules.append(col_validate)

        for cc in ct.column_constraints():
            cc_validate = cc.sql_constraint_rule()
            if cc_validate:
                validate_rules.append(cc_validate)

        # required check last in case other rules modify value
        req_validate = ct.sql_required_rule()
        if req_validate:
            validate_rules.append(req_validate)

    if validate_rules:
        validate_def = VALIDATE_DEFINITION_SQL.format(
            validate_rules=''.join(validate_rules),
        )
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
            'delete_fields': True,
            'primary_key': primary_key,
            'fields': fields,
            'triggers': [
                {'function': u'{0}_tabledesigner_validate'.format(resource_id)}
            ] if validate_rules else [],
        }
    )
