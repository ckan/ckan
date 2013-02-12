
def upgrade(migrate_engine):


    replace_string = r"""replace(replace(replace(replace(replace(replace(replace(replace(value,
                        '\\', '\'),
                        '\/', '/'),
                        '\"', '"'),
                        '\f', E'\f'),
                        '\t', E'\t'),
                        '\n', E'\n'),
                        '\r', E'\r'),
                        '\b', E'\b')"""

    update_statement = r'''
    BEGIN;

    UPDATE package_extra SET value = {replace_string} where left(value,1) = '"';
    UPDATE group_extra SET value = {replace_string} where left(value,1) = '"';

    UPDATE package_extra_revision SET value = {replace_string} where left(value,1) = '"';
    UPDATE group_extra_revision SET value = {replace_string} where left(value,1) = '"';


    UPDATE package_extra SET value = substr(value, 2 , length(value) - 2) where left(value,1) = '"';
    UPDATE group_extra SET value = substr(value, 2 , length(value) - 2) where left(value,1) = '"';

    UPDATE package_extra_revision SET value = substr(value, 2 , length(value) - 2) where left(value,1) = '"';
    UPDATE group_extra_revision SET value = substr(value, 2 , length(value) - 2) where left(value,1) = '"';

    COMMIT;

    '''.format(replace_string=replace_string)
    migrate_engine.execute(update_statement)
