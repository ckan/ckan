
def upgrade(migrate_engine):

    replace_string =    "replace("*39 + r"""value,
                        '\\', '\'),
                        '\/', '/'),
                        '\"', '"'),
                        '\f', E'\f'),
                        '\t', E'\t'),
                        '\n', E'\n'),
                        '\r', E'\r'),
                        '\b', E'\b'),
                        '\u0001', E'\x01'),
                        '\u0002', E'\x02'),
                        '\u0003', E'\x03'),
                        '\u0004', E'\x04'),
                        '\u0005', E'\x05'),
                        '\u0006', E'\x06'),
                        '\u0007', E'\x07'),
                        '\u0008', E'\x08'),
                        '\u0009', E'\x09'),
                        '\u000a', E'\x0a'),
                        '\u000b', E'\x0b'),
                        '\u000c', E'\x0c'),
                        '\u000d', E'\x0d'),
                        '\u000e', E'\x0e'),
                        '\u000f', E'\x0f'),
                        '\u0010', E'\x10'),
                        '\u0011', E'\x11'),
                        '\u0012', E'\x12'),
                        '\u0013', E'\x13'),
                        '\u0014', E'\x14'),
                        '\u0015', E'\x15'),
                        '\u0016', E'\x16'),
                        '\u0017', E'\x17'),
                        '\u0018', E'\x18'),
                        '\u0019', E'\x19'),
                        '\u001a', E'\x1a'),
                        '\u001b', E'\x1b'),
                        '\u001c', E'\x1c'),
                        '\u001d', E'\x1d'),
                        '\u001e', E'\x1e'),
                        '\u001f', E'\x1f')
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
