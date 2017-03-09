# encoding: utf-8

# -*- coding: utf-8 -*-


def upgrade(migrate_engine):
    update_default_q = (
        u'ALTER TABLE ONLY package ALTER COLUMN metadata_modified '
        u'SET DEFAULT (statement_timestamp() at time zone \'utc\');'
    )

    add_trigger_q = u"""
CREATE OR REPLACE FUNCTION update_metadata_modified() RETURNS TRIGGER
LANGUAGE plpgsql
AS
$$
BEGIN
    NEW.metadata_modified = (CURRENT_TIMESTAMP at time zone 'utc');
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS update_metadata_modified_t on "package";
CREATE TRIGGER update_metadata_modified_t
  BEFORE UPDATE
  ON package
  FOR EACH ROW
  EXECUTE PROCEDURE update_metadata_modified();
"""

    add_extras_trigger_q = u"""
CREATE OR REPLACE FUNCTION update_extras_metadata_modified() RETURNS TRIGGER
LANGUAGE plpgsql
AS
$$
BEGIN
    UPDATE "package" SET "metadata_modified"=
        (CURRENT_TIMESTAMP at time zone 'utc')
        WHERE package.id=NEW.package_id;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS update_extras_metadata_modified_t on "package_extra";
CREATE TRIGGER update_extras_metadata_modified_t
  BEFORE UPDATE
  ON package_extra
  FOR EACH ROW
  EXECUTE PROCEDURE update_extras_metadata_modified();
"""

    with migrate_engine.begin() as connection:
        connection.execute(update_default_q)
        connection.execute(add_trigger_q)
        connection.execute(add_extras_trigger_q)
