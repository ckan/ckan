import pkg_resources

ENTRY_POINT = 'fanstatic.libraries'


class LibraryRegistry(dict):
    """A dictionary-like registry of libraries.

    This is a dictionary that mains libraries. A value is
    a :py:class:`Library` instance, and a key is its
    library ``name``.

    Normally there is only a single global LibraryRegistry,
    obtained by calling ``get_library_registry()``.

    :param libraries: a sequence of libraries
    """
    def __init__(self, libraries):
        for library in libraries:
            self[library.name] = library

    def add(self, library):
        """Add a Library instance to the registry.

        :param add: add a library to the registry.
        """
        self[library.name] = library


def get_libraries_from_entry_points():
    libraries = []
    for entry_point in pkg_resources.iter_entry_points(ENTRY_POINT):
        library = entry_point.load()
        # If the distribution is in development mode we don't use its version.
        # See http://peak.telecommunity.com/DevCenter/setuptools#develop
        if entry_point.dist.precedence > pkg_resources.DEVELOP_DIST:
            library.version = entry_point.dist.version  # pragma: no cover
        libraries.append(library)
    return libraries

_library_registry = None


def get_library_registry():
    '''Get the global :py:class:`LibraryRegistry`.

    It gets filled with the libraries registered using the fanstatic
    entry point.

    You can also add libraries to it later.
    '''
    global _library_registry
    if _library_registry is not None:
        return _library_registry
    _library_registry = LibraryRegistry(get_libraries_from_entry_points())
    return _library_registry
