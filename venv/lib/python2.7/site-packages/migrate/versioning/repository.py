"""
   SQLAlchemy migrate repository management.
"""
import os
import shutil
import string
import logging

from pkg_resources import resource_filename
from tempita import Template as TempitaTemplate

from migrate import exceptions
from migrate.versioning import version, pathed, cfgparse
from migrate.versioning.template import Template
from migrate.versioning.config import *


log = logging.getLogger(__name__)

class Changeset(dict):
    """A collection of changes to be applied to a database.

    Changesets are bound to a repository and manage a set of
    scripts from that repository.

    Behaves like a dict, for the most part. Keys are ordered based on step value.
    """

    def __init__(self, start, *changes, **k):
        """
        Give a start version; step must be explicitly stated.
        """
        self.step = k.pop('step', 1)
        self.start = version.VerNum(start)
        self.end = self.start
        for change in changes:
            self.add(change)

    def __iter__(self):
        return iter(self.items())

    def keys(self):
        """
        In a series of upgrades x -> y, keys are version x. Sorted.
        """
        ret = list(super(Changeset, self).keys())
        # Reverse order if downgrading
        ret.sort(reverse=(self.step < 1))
        return ret

    def values(self):
        return [self[k] for k in self.keys()]

    def items(self):
        return zip(self.keys(), self.values())

    def add(self, change):
        """Add new change to changeset"""
        key = self.end
        self.end += self.step
        self[key] = change

    def run(self, *p, **k):
        """Run the changeset scripts"""
        for ver, script in self:
            script.run(*p, **k)


class Repository(pathed.Pathed):
    """A project's change script repository"""

    _config = 'migrate.cfg'
    _versions = 'versions'

    def __init__(self, path):
        log.debug('Loading repository %s...' % path)
        self.verify(path)
        super(Repository, self).__init__(path)
        self.config = cfgparse.Config(os.path.join(self.path, self._config))
        self.versions = version.Collection(os.path.join(self.path,
                                                      self._versions))
        log.debug('Repository %s loaded successfully' % path)
        log.debug('Config: %r' % self.config.to_dict())

    @classmethod
    def verify(cls, path):
        """
        Ensure the target path is a valid repository.

        :raises: :exc:`InvalidRepositoryError <migrate.exceptions.InvalidRepositoryError>`
        """
        # Ensure the existence of required files
        try:
            cls.require_found(path)
            cls.require_found(os.path.join(path, cls._config))
            cls.require_found(os.path.join(path, cls._versions))
        except exceptions.PathNotFoundError:
            raise exceptions.InvalidRepositoryError(path)

    @classmethod
    def prepare_config(cls, tmpl_dir, name, options=None):
        """
        Prepare a project configuration file for a new project.

        :param tmpl_dir: Path to Repository template
        :param config_file: Name of the config file in Repository template
        :param name: Repository name
        :type tmpl_dir: string
        :type config_file: string
        :type name: string
        :returns: Populated config file
        """
        if options is None:
            options = {}
        options.setdefault('version_table', 'migrate_version')
        options.setdefault('repository_id', name)
        options.setdefault('required_dbs', [])
        options.setdefault('use_timestamp_numbering', False)

        tmpl = open(os.path.join(tmpl_dir, cls._config)).read()
        ret = TempitaTemplate(tmpl).substitute(options)

        # cleanup
        del options['__template_name__']

        return ret

    @classmethod
    def create(cls, path, name, **opts):
        """Create a repository at a specified path"""
        cls.require_notfound(path)
        theme = opts.pop('templates_theme', None)
        t_path = opts.pop('templates_path', None)

        # Create repository
        tmpl_dir = Template(t_path).get_repository(theme=theme)
        shutil.copytree(tmpl_dir, path)

        # Edit config defaults
        config_text = cls.prepare_config(tmpl_dir, name, options=opts)
        fd = open(os.path.join(path, cls._config), 'w')
        fd.write(config_text)
        fd.close()

        opts['repository_name'] = name

        # Create a management script
        manager = os.path.join(path, 'manage.py')
        Repository.create_manage_file(manager, templates_theme=theme,
            templates_path=t_path, **opts)

        return cls(path)

    def create_script(self, description, **k):
        """API to :meth:`migrate.versioning.version.Collection.create_new_python_version`"""

        k['use_timestamp_numbering'] = self.use_timestamp_numbering
        self.versions.create_new_python_version(description, **k)

    def create_script_sql(self, database, description, **k):
        """API to :meth:`migrate.versioning.version.Collection.create_new_sql_version`"""
        k['use_timestamp_numbering'] = self.use_timestamp_numbering
        self.versions.create_new_sql_version(database, description, **k)

    @property
    def latest(self):
        """API to :attr:`migrate.versioning.version.Collection.latest`"""
        return self.versions.latest

    @property
    def version_table(self):
        """Returns version_table name specified in config"""
        return self.config.get('db_settings', 'version_table')

    @property
    def id(self):
        """Returns repository id specified in config"""
        return self.config.get('db_settings', 'repository_id')

    @property
    def use_timestamp_numbering(self):
        """Returns use_timestamp_numbering specified in config"""
        if self.config.has_option('db_settings', 'use_timestamp_numbering'):
            return self.config.getboolean('db_settings', 'use_timestamp_numbering')
        return False

    def version(self, *p, **k):
        """API to :attr:`migrate.versioning.version.Collection.version`"""
        return self.versions.version(*p, **k)

    @classmethod
    def clear(cls):
        # TODO: deletes repo
        super(Repository, cls).clear()
        version.Collection.clear()

    def changeset(self, database, start, end=None):
        """Create a changeset to migrate this database from ver. start to end/latest.

        :param database: name of database to generate changeset
        :param start: version to start at
        :param end: version to end at (latest if None given)
        :type database: string
        :type start: int
        :type end: int
        :returns: :class:`Changeset instance <migration.versioning.repository.Changeset>`
        """
        start = version.VerNum(start)

        if end is None:
            end = self.latest
        else:
            end = version.VerNum(end)

        if start <= end:
            step = 1
            range_mod = 1
            op = 'upgrade'
        else:
            step = -1
            range_mod = 0
            op = 'downgrade'

        versions = range(int(start) + range_mod, int(end) + range_mod, step)
        changes = [self.version(v).script(database, op) for v in versions]
        ret = Changeset(start, step=step, *changes)
        return ret

    @classmethod
    def create_manage_file(cls, file_, **opts):
        """Create a project management script (manage.py)

        :param file_: Destination file to be written
        :param opts: Options that are passed to :func:`migrate.versioning.shell.main`
        """
        mng_file = Template(opts.pop('templates_path', None))\
            .get_manage(theme=opts.pop('templates_theme', None))

        tmpl = open(mng_file).read()
        fd = open(file_, 'w')
        fd.write(TempitaTemplate(tmpl).substitute(opts))
        fd.close()
