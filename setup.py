try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

from ckan import __version__, __description__, __long_description__, __license__

setup(
    name='ckan',
    version=__version__,
    author='Open Knowledge Foundation',
    author_email='info@okfn.org',
    license=__license__,
    url='http://www.okfn.org/ckan/',
    description=__description__,
    long_description =__long_description__,
    # Also requires: markdown 1.5 (0.6a only on the PCS)
    install_requires=[
        'vdm>=0.1',
        'Pylons>=0.9.6.1',
        'SQLObject>=0.7',
        'AuthKit==0.4.0',
        'paginate==0.3.2',
        'genshi==0.4.4'    # Not necessarily pulled in with Pylons.
        #'markdown'         # 1.5 doesn't seem to be on the PCS.
    ],
    packages=find_packages(exclude=['ez_setup']),
    scripts = ['bin/ckan-admin'],
    include_package_data=True,
    package_data={'ckan': ['i18n/*/LC_MESSAGES/*.mo']},
    #message_extractors = {'ckan': [
    #        ('**.py', 'python', None),
    #        ('templates/**.mako', 'mako', None),
    #        ('public/**', 'ignore', None)]},
    entry_points="""
    [paste.app_factory]
    main = ckan.config.middleware:make_app

    [paste.app_install]
    main = pylons.util:PylonsInstaller
    """,
    # setup.py test command needs a TestSuite so does not work with py.test
    # test_suite = 'nose.collector',
    # tests_require=[ 'py >= 0.8.0-alpha2' ]
)
