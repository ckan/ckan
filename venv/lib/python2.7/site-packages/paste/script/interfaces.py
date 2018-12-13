# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
class IAppInstall(object):

    """
    The interface for objects in the entry point group
    ``paste.app_install``
    """

    def __init__(distribution, entry_group, entry_name):
        """
        An object representing a specific application (the
        distribution is a pkg_resource.Distribution object), for the
        given entry point name in the given group.  Right now the only
        group used for this is ``'paste.app_factory'``.
        """

    def description(sys_config):
        """
        Return a text description of the application and its
        configuration.  ``sys_config`` is a dictionary representing
        the system configuration, and can be used for giving more
        explicit defaults if the application preparation uses the
        system configuration.  It may be None, in which case the
        description should be more abstract.

        Applications are free to ignore ``sys_config``.
        """

    def write_config(command, filename, sys_config):
        """
        Write a fresh config file to ``filename``.  ``command`` is a
        ``paste.script.command.Command`` object, and should be used
        for the actual operations.  It handles things like simulation
        and verbosity.

        ``sys_config`` is (if given) a dictionary of system-wide
        configuration options.
        """

    def setup_config(command, config_filename,
                     config_section, sys_config):
        """
        Set up the application, using ``command`` (to ensure simulate,
        etc).  The application is described by the configuration file
        ``config_filename``.  ``sys_config`` is the system
        configuration (though probably the values from it should have
        already been encorporated into the configuration file).
        """
