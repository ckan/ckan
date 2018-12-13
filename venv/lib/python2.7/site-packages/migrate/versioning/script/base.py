#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from migrate import exceptions
from migrate.versioning.config import operations
from migrate.versioning import pathed


log = logging.getLogger(__name__)

class BaseScript(pathed.Pathed):
    """Base class for other types of scripts.
    All scripts have the following properties:

    source (script.source())
      The source code of the script
    version (script.version())
      The version number of the script
    operations (script.operations())
      The operations defined by the script: upgrade(), downgrade() or both.
      Returns a tuple of operations.
      Can also check for an operation with ex. script.operation(Script.ops.up)
    """ # TODO: sphinxfy this and implement it correctly

    def __init__(self, path):
        log.debug('Loading script %s...' % path)
        self.verify(path)
        super(BaseScript, self).__init__(path)
        log.debug('Script %s loaded successfully' % path)

    @classmethod
    def verify(cls, path):
        """Ensure this is a valid script
        This version simply ensures the script file's existence

        :raises: :exc:`InvalidScriptError <migrate.exceptions.InvalidScriptError>`
        """
        try:
            cls.require_found(path)
        except:
            raise exceptions.InvalidScriptError(path)

    def source(self):
        """:returns: source code of the script.
        :rtype: string
        """
        fd = open(self.path)
        ret = fd.read()
        fd.close()
        return ret

    def run(self, engine):
        """Core of each BaseScript subclass.
        This method executes the script.
        """
        raise NotImplementedError()
