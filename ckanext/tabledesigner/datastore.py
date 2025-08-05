from __future__ import annotations

from typing import Any, List

from ckan.plugins.toolkit import get_action, h
from ckan.types import Context


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


def create_table(context: Context, resource_id: str, fields: List[dict[str, Any]]):
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
            context,
            {
                'name': f'{resource_id}_tabledesigner_validate',
                'or_replace': True,
                'rettype': 'trigger',
                'definition': validate_def,
            }
        )

    get_action('datastore_create')(
        context,
        {
            'resource_id': resource_id,
            'force': True,
            'delete_fields': True,
            'primary_key': primary_key,
            'fields': fields,
            'triggers': [
                {'function': f'{resource_id}_tabledesigner_validate'}
            ] if validate_rules else [],
        }
    )
