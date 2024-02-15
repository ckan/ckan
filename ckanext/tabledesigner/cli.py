# encoding: utf-8

import json
import click
import sqlalchemy as sa

from ckan.plugins.toolkit import get_action
from ckanext.datastore.backend.postgres import (
    identifier,
    literal_string,
    get_read_engine,
    get_write_engine,
    _get_raw_field_info,
)


@click.group(short_help='Table Designer commands')
def tabledesigner():
    pass


@tabledesigner.command(short_help='upgrade Table Designer data schemas')
@click.option('-d', '--dry-run', is_flag=True, help='make no changes')
def upgrade(dry_run):
    '''
    Upgrade Table Designer data schemas by moving keys that were stored in
    field 'info' to plugin_data.
    '''

    site_user = get_action('get_site_user')({'ignore_auth': True}, {})

    result = get_action('datastore_search')(
        {'user': site_user['name']},
        {'resource_id': '_table_metadata'}
    )

    count = 0
    skipped = 0
    noinfo = 0
    read_connection = get_read_engine()
    for record in result['records']:
        if record['alias_of']:
            continue

        raw_fields, old = _get_raw_field_info(read_connection, record['name'])
        if old:
            click.echo('Run `ckan datastore upgrade` first!')
            raise click.Abort()

        alter_sql = []
        for fid, fvalue in raw_fields.items():
            if 'tabledesigner' in fvalue:
                skipped +=1
                break

            info = fvalue.get('_info', {})
            if 'tdtype' not in info:
                continue

            fvalue['tabledesigner'] = {'tdtype': info.pop('tdtype')}
            for k in ('pkreq', 'minimum', 'maximum', 'pattern', 'immutable'):
                if k in info:
                    fvalue['tabledesigner']['td' + k] = info.pop(k)
            if 'choices' in info:
                fvalue['tabledesigner']['tdchoices'] = [
                    ch.strip() for ch in info.pop('choices').split('\n')
                ]

            # ' ' prefix for data version
            raw_sql = literal_string(' ' + json.dumps(
                fvalue, ensure_ascii=False, separators=(',', ':')))
            alter_sql.append(u'COMMENT ON COLUMN {0}.{1} is {2}'.format(
                identifier(record['name']),
                identifier(fid),
                raw_sql))
        else:
            if alter_sql:
                if not dry_run:
                    with get_write_engine().begin() as connection:
                        connection.execute(sa.text(';'.join(alter_sql
                            ).replace(':', r'\:')  # no bind params
                        ))
                count += 1
            else:
                noinfo += 1

    click.echo(
        'Upgraded %d tables (%d already upgraded, %d not table designer)' % (
            count, skipped, noinfo
        )
    )

