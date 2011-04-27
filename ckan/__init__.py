__version__ = '1.4a'
__description__ = 'Comprehensive Knowledge Archive Network (CKAN) Software'
__long_description__ = \
'''The CKAN software is used to run the Comprehensive Knowledge Archive
Network (CKAN) site: http://www.ckan.net.

The Comprehensive Knowledge Archive Network is a registry of open
knowledge packages and projects (and a few closed ones). CKAN is the
place to search for open knowledge resources as well as register your
own - be that a set of Shakespeare's works, a global population density
database, the voting records of MPs, or 30 years of US patents.

Those familiar with freshmeat or CPAN can think of CKAN as providing an
analogous service for open knowledge. 
'''
__license__ = 'AGPL'

try:
    # Ths automatically modifies sys.path so that the CKAN versions of
    # key dependencies are used instead of the ones already installed.
    import ckan_deps
except ImportError:
    # This installation of CKAN probably isn't using the ckan_deps
    pass

