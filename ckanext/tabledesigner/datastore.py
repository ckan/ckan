from __future__ import annotations

from typing import Any, List

from ckan.plugins.toolkit import get_action, h


VALIDATE_DEFINITION_SQL = '''
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


def create_table(resource_id: str, fields: List[dict[str, Any]]):
    '''
    Set up datastore table + validation
    '''
    primary_key = []
    validate_rules = []
    for f in fields:
        ct = h.tabledesigner_column_type(f)

        if f['info'].get('pkreq') == 'pk':
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
                'name': f'{resource_id}_tabledesigner_validate',
                'or_replace': True,
                'rettype': 'trigger',
                'definition': validate_def,
            }
        )

    get_action('datastore_create')(
        {},
        {
            'resource_id': resource_id,
            'force': True,
            'primary_key': primary_key,
            'fields': [{
                'id': f['id'],
                'type': f['type'],
                'info': {
                    k: v for (k, v) in f['info'].items()
                    if k != 'id'
                },
            } for f in fields],
            'triggers': [
                {'function': f'{resource_id}_tabledesigner_validate'}
            ] if validate_rules else [],
        }
    )
