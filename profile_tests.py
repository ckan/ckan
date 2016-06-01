# encoding: utf-8

# Runs all the tests and save a speed profile to ckan.tests.profile
import nose
import cProfile
command = """nose.main(argv=['--ckan','--with-pylons=test-core.ini', 'ckan/tests', '-x', '-v'])"""
cProfile.runctx( command, globals(), locals(), filename="ckan.tests.profile" )
