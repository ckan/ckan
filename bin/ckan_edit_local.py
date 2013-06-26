'''Script for doing various edits to ckan data that is stored on a local
CKAN instance'''

import os
import sys
from optparse import OptionParser

from running_stats import StatsCount, StatsList
from revision_manager import RevisionManager

def ons_prefix():
    '''Remove "http://www.statistics.gov.uk/" from resource IDs derived from ONS'''
    from ckan import model
    prefix = 'http://www.statistics.gov.uk/'
    pkgs_changed = []
    for pkg in model.Session.query(model.Package):
        is_changed = False
        for resource in pkg.resources:
            is_changed = is_changed or prefix in resource.description
            if is_changed:
                resource.description = resource.description.replace(prefix, '')
        if is_changed:
            rev = model.repo.new_revision() 
            rev.author = u'auto-loader'
            rev.message = u'Removed domain from ONS IDs'

            model.Session.commit()

            pkgs_changed.append(pkg.name)
    
    model.Session.remove()
    print 'Removed ONS prefix from %i packages out of %i' % (len(pkgs_changed), model.Session.query(model.Package).count())
            
def dump_data4nr_names(csv_filepath):
    '''Dumps a list of the old and new names for packages in data4nr csv data'''
    from ckan.getdata.data4nr import Data4Nr
    import csv

    data4nr = Data4Nr()
    assert os.path.exists(csv_filepath)
    f_obj = open(csv_filepath, "r")
    reader = csv.reader(f_obj)
    index = 0
    reader.next()
    for row_list in reader:
        data4nr_dict = data4nr._parse_line(row_list, index)
        if data4nr_dict:
            old_name, new_name = data4nr._create_name(data4nr_dict)
            print '%s %s' % (old_name, new_name)
        index += 1

def munge_old_data4nr_names(old_names_filepath):
    '''Matches list of old Data4Nr names to new names
    Format of a line of old_names file is like:
       [0] => accident_and_emergency_statistics_2000-2001_to_2008-2009
    This routine tries to match this old_name to a name in the current database
    '''
    from ckan import model
    assert os.path.exists(old_names_filepath)
    f_obj = open(old_names_filepath, 'r')
    for line in f_obj:
        ignore, old_name = line.split('=>')
        old_name = old_name.strip()
        bit_of_name = old_name
        new_name = None
        while bit_of_name:
            if model.Package.by_name(unicode(bit_of_name)):
                new_name = bit_of_name
                break
            bit_of_name = bit_of_name[:-1]
        if new_name:
            print '%s %s' % (old_name, new_name)
        else:
            print '%s UNKNOWN' % old_name
    f_obj.close()
            
def canada_extras():
    keys_changed = StatsCount()
    unmapped_keys = StatsList()
    licenses_changed = StatsCount()
    unmapped_licenses = StatsList()
    licenses = StatsList()
    key_mapping = {
        'Level of Government':'level_of_government',
        }
    license_mapping = {
        # CS: bad_spelling ignore
        'http://geogratis.ca/geogratis/en/licence.jsp':'geogratis',
        'Crown Copyright':'canada-crown',
        }
    from ckan import model
    rev = RevisionManager('Standardize extra keys', 10)
    for pkg in model.Session.query(model.Package):
        for old_key, new_key in key_mapping.items():
            if pkg.extras.has_key(old_key):
                rev.before_change()
                pkg.extras[new_key] = pkg.extras[old_key]
                del pkg.extras[old_key]
                keys_changed.increment(old_key)
                rev.after_change()
        for license_key in ('License', 'License URL'):
            if pkg.extras.has_key(license_key):
                old_license = pkg.extras[license_key]
                if old_license in license_mapping:
                    rev.before_change()
                    pkg.license_id = unicode(license_mapping[old_license])
                    del pkg.extras[license_key]
                    licenses_changed.increment(old_license)
                    rev.after_change()
                else:
                    unmapped_licenses.add(old_license, pkg.name)
        licenses.add(pkg.license_id, pkg.name)
        for key in pkg.extras.keys():
            if key not in key_mapping.keys() and \
               key not in key_mapping.values():
                unmapped_keys.add(key, pkg.name)
    rev.finished()
    print 'Packages: %i' % model.Session.query(model.Package).count()
    print 'Changed keys:\n', keys_changed.report()
    print 'Unmapped keys:\n', unmapped_keys.report()
    print 'Changed licenses:\n', licenses_changed.report()
    print 'Unmapped licenses:\n', unmapped_licenses.report()
    print 'Licenses:\n', licenses.report()

if __name__ == '__main__':
    usage = '''usage: %prog [options] <command>
    commands:
        ons-prefix - Remove ONS prefix in resources
        dump_data4nr_names - Dump list of old/new package names for Data4Nr csv file
        munge_old_data4nr_names - Matches list of old Data4Nr names to new names
        canada_extras - Standardise keys of Canada extra fields
    ''' # NB Options are automatically listed
    parser = OptionParser(usage=usage)
    parser.add_option('-c', '--config', dest='config', help='Config filepath', default='development.ini')
    parser.add_option('-f', '--file', dest='filepath', help='Input filepath')

    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.print_help()
        sys.exit(0)
    command = args[0]

    if options.config:
        import loadconfig
        path = os.path.abspath(options.config)
        loadconfig.load_config(path)
            
    if command == 'ons-prefix':
        ons_prefix()
    elif command == 'dump_data4nr_names':
        dump_data4nr_names(options.filepath)
    elif command == 'munge_old_data4nr_names':
        munge_old_data4nr_names(options.filepath)
    elif command == 'canada_extras':
        canada_extras()
    else:
        print 'Command %r not found' % command
        print usage
