class MetaEntryPointDescription(object):
    description = """
    This is an entry point that describes other entry points.
    """

class CreateTemplateDescription(object):
    description = """
    Entry point for creating the file layout for a new project
    from a template.
    """

class PasterCommandDescription(object):
    description = """
    Entry point that adds a command to the ``paster`` script
    to a project that has specifically enabled the command.
    """

class GlobalPasterCommandDescription(object):
    description = """
    Entry point that adds a command to the ``paster`` script
    globally.
    """

class AppInstallDescription(object):
    description = """
    This defines a runner that can install the application given a
    configuration file.
    """

##################################################
## Not in Paste per se, but we'll document
## them...

class ConsoleScriptsDescription(object):
    description = """
    When a package is installed, any entry point listed here will be
    turned into a command-line script.
    """

class DistutilsCommandsDescription(object):
    description = """
    This will add a new command when running
    ``python setup.py entry-point-name`` if the
    package uses setuptools.
    """

class SetupKeywordsDescription(object):
    description = """
    This adds a new keyword to setup.py's setup() function, and a
    validator to validate the value.
    """

class EggInfoWriters(object):
    description = """
    This adds a new writer that creates files in the PkgName.egg-info/
    directory.
    """
