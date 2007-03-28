from setuptools import setup, find_packages

setup(
    name='ckan',
    version='0.3dev',
    author='Open Knowledge Foundation',
    author_email='info@okfn.org',
    license='MIT',
    url='http://www.okfn.org/ckan/',
    description='Comprehensive Knowledge Archive Network Software',
    long_description =\
'''
CKAN is a web application to manage listings of knowledge packages.
''',
    # markdown should install automatically but might need to check
    install_requires=["Pylons>=0.9.4", "SQLObject>=0.7", "AuthKit>=0.3.0pre5",
        "markdown>=1.5"],
    packages=find_packages(),
    include_package_data=True,
    package_data={'ckan': ['i18n/*/LC_MESSAGES/*.mo']},
    entry_points='''
    [paste.app_factory]
    main=ckan:make_app
    [paste.app_install]
    main=paste.script.appinstall:Installer
    ''', 
    # setup.py test command needs a TestSuite so does not work with pyt.test
    # test_suite = 'nose.collector',
    # tests_require=[ 'py >= 0.8.0-alpha2' ]
)
