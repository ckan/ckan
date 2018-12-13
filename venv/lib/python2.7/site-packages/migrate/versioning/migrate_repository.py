"""
   Script to migrate repository from sqlalchemy <= 0.4.4 to the new
   repository schema. This shouldn't use any other migrate modules, so
   that it can work in any version.
"""

import os
import sys
import logging

log = logging.getLogger(__name__)


def usage():
    """Gives usage information."""
    print("Usage: %s repository-to-migrate" % sys.argv[0])
    print("Upgrade your repository to the new flat format.")
    print("NOTE: You should probably make a backup before running this.")
    sys.exit(1)


def delete_file(filepath):
    """Deletes a file and prints a message."""
    log.info('Deleting file: %s' % filepath)
    os.remove(filepath)


def move_file(src, tgt):
    """Moves a file and prints a message."""
    log.info('Moving file %s to %s' % (src, tgt))
    if os.path.exists(tgt):
        raise Exception(
            'Cannot move file %s because target %s already exists' % \
                (src, tgt))
    os.rename(src, tgt)


def delete_directory(dirpath):
    """Delete a directory and print a message."""
    log.info('Deleting directory: %s' % dirpath)
    os.rmdir(dirpath)


def migrate_repository(repos):
    """Does the actual migration to the new repository format."""
    log.info('Migrating repository at: %s to new format' % repos)
    versions = '%s/versions' % repos
    dirs = os.listdir(versions)
    # Only use int's in list.
    numdirs = [int(dirname) for dirname in dirs if dirname.isdigit()]
    numdirs.sort()  # Sort list.
    for dirname in numdirs:
        origdir = '%s/%s' % (versions, dirname)
        log.info('Working on directory: %s' % origdir)
        files = os.listdir(origdir)
        files.sort()
        for filename in files:
            # Delete compiled Python files.
            if filename.endswith('.pyc') or filename.endswith('.pyo'):
                delete_file('%s/%s' % (origdir, filename))

            # Delete empty __init__.py files.
            origfile = '%s/__init__.py' % origdir
            if os.path.exists(origfile) and len(open(origfile).read()) == 0:
                delete_file(origfile)

            # Move sql upgrade scripts.
            if filename.endswith('.sql'):
                version, dbms, operation = filename.split('.', 3)[0:3]
                origfile = '%s/%s' % (origdir, filename)
                # For instance:  2.postgres.upgrade.sql ->
                #  002_postgres_upgrade.sql
                tgtfile = '%s/%03d_%s_%s.sql' % (
                    versions, int(version), dbms, operation)
                move_file(origfile, tgtfile)

        # Move Python upgrade script.
        pyfile = '%s.py' % dirname
        pyfilepath = '%s/%s' % (origdir, pyfile)
        if os.path.exists(pyfilepath):
            tgtfile = '%s/%03d.py' % (versions, int(dirname))
            move_file(pyfilepath, tgtfile)

        # Try to remove directory. Will fail if it's not empty.
        delete_directory(origdir)


def main():
    """Main function to be called when using this script."""
    if len(sys.argv) != 2:
        usage()
    migrate_repository(sys.argv[1])


if __name__ == '__main__':
    main()
