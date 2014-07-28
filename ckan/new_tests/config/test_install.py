'''Tests for install.py.'''
import subprocess
import tempfile
import ConfigParser
import os


def test_make_config_with_defaults():
    '''Test the paster make-config command with the default settings.'''
    # This actually creates a temp file and then deletes it, which is silly,
    # but it gets us the random temp file name that we need.
    config_file = tempfile.NamedTemporaryFile().name

    # Run `paster make-config` as a subprocess.
    # We redirect stdin and stdout to /dev/null to avoid cluttering up the
    # test output.
    FNULL = open(os.devnull, 'w')
    subprocess.check_call(['paster', 'make-config', 'ckan', config_file],
                          stdout=FNULL, stderr=subprocess.STDOUT)

    # Parse the config file that we created.
    parser = ConfigParser.ConfigParser()
    parser.read(config_file)

    # We won't check all the config settings, just one from the top, one
    # from the middle and one from the bottom of the config file.
    assert parser.get('app:main', 'sqlalchemy.url') == (
        'postgresql://ckan_default:pass@localhost/ckan_default')
    assert parser.get('app:main', 'ckan.site_title') == 'CKAN'
    assert parser.get('app:main', 'smtp.starttls') == 'False'


def test_make_config_with_custom_values():
    '''Test the paster make-config command with some custom settings.

    make-config accepts custom values for config settings via environment
    variables.

    '''
    # This actually creates a temp file and then deletes it, which is silly,
    # but it gets us the random temp file name that we need.
    config_file = tempfile.NamedTemporaryFile().name

    # The environment variables that we'll pass to the paster make-config
    # subprocess. We start with a copy of this process's environment, needed
    # for `paster` to work without an absolute path.
    environment_variables = os.environ.copy()
    environment_variables.update({
        'CKAN_SQLALCHEMY_URL': 'custom sqlalchemy url',
        'CKAN_SITE_TITLE': 'custom site title',
        'CKAN_SMTP_STARTTLS': 'custom smtp starttls'})

    # Run `paster make-config` as a subprocess.
    # We redirect stdin and stdout to /dev/null to avoid cluttering up the
    # test output.
    FNULL = open(os.devnull, 'w')
    subprocess.check_call(['paster', 'make-config', 'ckan', config_file],
                          stdout=FNULL, stderr=subprocess.STDOUT,
                          env=environment_variables)

    # Parse the config file that we created.
    parser = ConfigParser.ConfigParser()
    parser.read(config_file)

    # Check the config settings that we customized.
    assert parser.get('app:main', 'sqlalchemy.url') == (
        'custom sqlalchemy url')
    assert parser.get('app:main', 'ckan.site_title') == 'custom site title'
    assert parser.get('app:main', 'smtp.starttls') == 'custom smtp starttls'

    # Check that other settings still have their default values.
    assert parser.get('app:main', 'ckan.preview.loadable') == (
        'html htm rdf+xml owl+xml xml n3 n-triples turtle plain atom csv tsv '
        'rss txt json')
    assert parser.get('app:main', 'ckan.locale_default') == 'en'
