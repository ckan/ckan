#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
import warnings
import logging
import inspect

import migrate
from migrate.versioning import genmodel, schemadiff
from migrate.versioning.config import operations
from migrate.versioning.template import Template
from migrate.versioning.script import base
from migrate.versioning.util import import_path, load_model, with_engine
from migrate.exceptions import MigrateDeprecationWarning, InvalidScriptError, ScriptError
import six
from six.moves import StringIO

log = logging.getLogger(__name__)
__all__ = ['PythonScript']


class PythonScript(base.BaseScript):
    """Base for Python scripts"""

    @classmethod
    def create(cls, path, **opts):
        """Create an empty migration script at specified path

        :returns: :class:`PythonScript instance <migrate.versioning.script.py.PythonScript>`"""
        cls.require_notfound(path)

        src = Template(opts.pop('templates_path', None)).get_script(theme=opts.pop('templates_theme', None))
        shutil.copy(src, path)

        return cls(path)

    @classmethod
    def make_update_script_for_model(cls, engine, oldmodel,
                                     model, repository, **opts):
        """Create a migration script based on difference between two SA models.

        :param repository: path to migrate repository
        :param oldmodel: dotted.module.name:SAClass or SAClass object
        :param model: dotted.module.name:SAClass or SAClass object
        :param engine: SQLAlchemy engine
        :type repository: string or :class:`Repository instance <migrate.versioning.repository.Repository>`
        :type oldmodel: string or Class
        :type model: string or Class
        :type engine: Engine instance
        :returns: Upgrade / Downgrade script
        :rtype: string
        """

        if isinstance(repository, six.string_types):
            # oh dear, an import cycle!
            from migrate.versioning.repository import Repository
            repository = Repository(repository)

        oldmodel = load_model(oldmodel)
        model = load_model(model)

        # Compute differences.
        diff = schemadiff.getDiffOfModelAgainstModel(
            model,
            oldmodel,
            excludeTables=[repository.version_table])
        # TODO: diff can be False (there is no difference?)
        decls, upgradeCommands, downgradeCommands = \
            genmodel.ModelGenerator(diff,engine).genB2AMigration()

        # Store differences into file.
        src = Template(opts.pop('templates_path', None)).get_script(opts.pop('templates_theme', None))
        f = open(src)
        contents = f.read()
        f.close()

        # generate source
        search = 'def upgrade(migrate_engine):'
        contents = contents.replace(search, '\n\n'.join((decls, search)), 1)
        if upgradeCommands:
            contents = contents.replace('    pass', upgradeCommands, 1)
        if downgradeCommands:
            contents = contents.replace('    pass', downgradeCommands, 1)
        return contents

    @classmethod
    def verify_module(cls, path):
        """Ensure path is a valid script

        :param path: Script location
        :type path: string
        :raises: :exc:`InvalidScriptError <migrate.exceptions.InvalidScriptError>`
        :returns: Python module
        """
        # Try to import and get the upgrade() func
        module = import_path(path)
        try:
            assert callable(module.upgrade)
        except Exception as e:
            raise InvalidScriptError(path + ': %s' % str(e))
        return module

    def preview_sql(self, url, step, **args):
        """Mocks SQLAlchemy Engine to store all executed calls in a string
        and runs :meth:`PythonScript.run <migrate.versioning.script.py.PythonScript.run>`

        :returns: SQL file
        """
        buf = StringIO()
        args['engine_arg_strategy'] = 'mock'
        args['engine_arg_executor'] = lambda s, p = '': buf.write(str(s) + p)

        @with_engine
        def go(url, step, **kw):
            engine = kw.pop('engine')
            self.run(engine, step)
            return buf.getvalue()

        return go(url, step, **args)

    def run(self, engine, step):
        """Core method of Script file.
        Exectues :func:`update` or :func:`downgrade` functions

        :param engine: SQLAlchemy Engine
        :param step: Operation to run
        :type engine: string
        :type step: int
        """
        if step in ('downgrade', 'upgrade'):
            op = step
        elif step > 0:
            op = 'upgrade'
        elif step < 0:
            op = 'downgrade'
        else:
            raise ScriptError("%d is not a valid step" % step)

        funcname = base.operations[op]
        script_func = self._func(funcname)

        # check for old way of using engine
        if not inspect.getargspec(script_func)[0]:
            raise TypeError("upgrade/downgrade functions must accept engine"
                " parameter (since version 0.5.4)")

        script_func(engine)

    @property
    def module(self):
        """Calls :meth:`migrate.versioning.script.py.verify_module`
        and returns it.
        """
        if not hasattr(self, '_module'):
            self._module = self.verify_module(self.path)
        return self._module

    def _func(self, funcname):
        if not hasattr(self.module, funcname):
            msg = "Function '%s' is not defined in this script"
            raise ScriptError(msg % funcname)
        return getattr(self.module, funcname)
