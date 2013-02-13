
def upgrade(migrate_engine):




    replace_string = r"""replace(replace(replace(replace(replace(replace(replace(replace(
                         replace(replace(replace(replace(replace(replace(replace(replace(
                         replace(replace(replace(replace(replace(replace(replace(replace(
                         replace(replace(replace(replace(replace(replace(replace(replace(
                         replace(replace(replace(replace(replace(replace(replace(value,
                        '\\', '\'),
                        '\/', '/'),
                        '\"', '"'),
                        '\f', E'\f'),
                        '\t', E'\t'),
                        '\n', E'\n'),
                        '\r', E'\r'),
                        '\b', E'\b'),
                        '\u0001', E'\u0001'),
                        '\u0002', E'\u0002'),
                        '\u0003', E'\u0003'),
                        '\u0004', E'\u0004'),
                        '\u0005', E'\u0005'),
                        '\u0006', E'\u0006'),
                        '\u0007', E'\u0007'),
                        '\u0008', E'\u0008'),
                        '\u0009', E'\u0009'),
                        '\u000a', E'\u000a'),
                        '\u000b', E'\u000b'),
                        '\u000c', E'\u000c'),
                        '\u000d', E'\u000d'),
                        '\u000e', E'\u000e'),
                        '\u000f', E'\u000f'),
                        '\u0010', E'\u0010'),
                        '\u0011', E'\u0011'),
                        '\u0012', E'\u0012'),
                        '\u0013', E'\u0013'),
                        '\u0014', E'\u0014'),
                        '\u0015', E'\u0015'),
                        '\u0016', E'\u0016'),
                        '\u0017', E'\u0017'),
                        '\u0018', E'\u0018'),
                        '\u0019', E'\u0019'),
                        '\u001a', E'\u001a'),
                        '\u001b', E'\u001b'),
                        '\u001c', E'\u001c'),
                        '\u001d', E'\u001d'),
                        '\u001e', E'\u001e'),
                        '\u001f', E'\u001f')
                        """

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
