# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
This module contains default sysconfig settings.

The command object is inserted into this module as a global variable
``paste_command``, and can be used inside functions.
"""

def add_custom_options(parser):
    """
    This method can modify the ``parser`` object (which is an
    ``optparse.OptionParser`` instance).  This can be used to add new
    options to the command.
    """
    pass

def default_config_filename(installer):
    """
    This function can return a default filename or directory for the
    configuration file, if none was explicitly given.

    Return None to mean no preference.  The first non-None returning
    value will be used.

    Pay attention to ``installer.expect_config_directory`` here,
    and to ``installer.default_config_filename``.
    """
    return installer.default_config_filename

def install_variables(installer):
    """
    Returns a dictionary of variables for use later in the process
    (e.g., filling a configuration file).  These are combined from all
    sysconfig files.
    """
    return {}

def post_setup_hook(installer, config_file):
    """
    This is called at the very end of ``paster setup-app``.  You
    might use it to register an application globally.
    """
    pass
