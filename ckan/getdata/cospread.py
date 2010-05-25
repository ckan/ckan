import re
import os.path
import csv

import sqlalchemy

import ckan.model as model
from ckan.lib import schema_gov
from ckan.lib import field_types

class Data(object):
    def load_csv_into_db(self, csv_filepath):
        self._basic_setup()
        self._new_file_reset()
        rev = self._new_revision()
        assert os.path.exists(csv_filepath)
        f_obj = open(csv_filepath, "r")
        self._current_filename = os.path.basename(csv_filepath)
        reader = csv.reader(f_obj)
        index = 0
        for row_list in reader:
            if 'UK Public Data Project' in row_list[0]:
                reader.next()
            cospread_dict = self._parse_line(row_list, index)
            if cospread_dict:
                self._load_line_into_db(cospread_dict, index)
            index += 1
            if index % 100 == 0:
                self._commit_and_report(index)
        self._commit_and_report(index, full=True)

    def _new_file_reset(self):
        self._titles_complete = False
        self._title_line_1 = None
        self._title_line_2 = None
        # Some packages with multiple URLs have multiple rows in the spreadsheet.
        # self._resources stores all URLs in this spreadsheet so that if a
        # duplicate package_name is found then previous URLs are added to the
        # record.
        self._resources = {} # name:[url, {'url':, 'description':, 'format':}]
        self._packages_created = []
        self._packages_updated = []
        
    def _commit_and_report(self, index, full=False):
        print 'Loaded %s lines' % index
        if full:
            print 'Packages created (%i): %s' % (len(self._packages_created), ' '.join(self._packages_created))
            print 'Packages updated (%i): %s' % (len(self._packages_updated), ' '.join(self._packages_updated))
        model.repo.commit_and_remove()

    def _parse_line(self, row_values, line_index):

        if not self._titles_complete:
            is_title_row, self._titles_complete = self._parse_row_for_titles(row_values)
            if is_title_row or not self._titles_complete:
                return None
        
        if len(row_values) < 32:
            print 'Error: Line %i has not enough values: %i' % (line_index, len(row_values))
            return None
        cospread_dict = {}
        for i, val in enumerate(row_values):
            cospread_dict[self._titles[i].lower()] = unicode(val.decode('utf8'))
        return cospread_dict

    def _parse_row_for_titles(self, row_values):
        is_title_row = False
        are_titles_complete = False
        if row_values[0] == 'Package name':
            self._title_line_1 = row_values
            is_title_row = True
            are_titles_complete = False
        elif self._title_line_1:
            self._title_line_2 = row_values
            titles = []
            previous_t1 = ''
            for i in range(len(self._title_line_1)):
                t1 = self._title_line_1[i].lower().replace('  ', ' ')
                t2 = self._title_line_2[i].lower()
                if t1 == 'package name':
                    title = 'name'
                elif not t1:
                    title = previous_t1
                else:
                    title = t1
                if title in ('geographical granularity', 'geographic coverage', 'temporal granularity'):
                    title += ' - %s' % t2
                elif title in ('contact', 'maintainer', 'author'):
                    if title == 'contact':
                        title = 'author'
                    if 'e-mail' in t2:
                        title += ' - email'
                    else:
                        title += ' - name'
                titles.append(title)
                if t1:
                    previous_t1 = t1

            self._titles = titles
            is_title_row = True
            are_titles_complete = True
        return (is_title_row, are_titles_complete)

# ['name', 'title', 'co identifier', 'notes', 'date released', 'date updated', 'update frequency', 'geographical granularity - standard', 'geographical granularity - other', 'geographic coverage - england', 'geographic coverage - n. ireland', 'geographic coverage - scotland', 'geographic coverage - wales', 'geographic coverage - overseas', 'geographic coverage - global', 'temporal granularity - standard', 'temporal granularity - other', 'file format', 'categories', 'national statistic', 'precision', 'url', 'download url', 'taxonomy url', 'department', 'agency responsible', 'contact - name', 'contact - email', 'maintainer - name', 'maintainer - email', 'licence', 'tags']

    def _name_munge(self, input_name):
        '''Munges the name field in case it is not to spec.'''
        return self._munge(input_name.replace(' ', '').replace('.', '_').replace('&', 'and'))

    def _parse_tags(self, tags_str):
        tag_list = re.split(',\s?|\s', tags_str)
        return [schema_gov.tag_munge(tag_name) for tag_name in tag_list]

    def _load_line_into_db(self, _dict, line_index):
        # Create package
        rev = self._new_revision()
        name = self._name_munge(_dict['name'])
        title = _dict['title']
        url = _dict['url']
        notes = _dict['notes']

        if self._resources.has_key(name):
            resources = self._resources[name]
            line_is_just_adding_multiple_resources = True
        else:
            resources = []
            line_is_just_adding_multiple_resources = False
        multiple_urls = False
        description = _dict.get('download description', u'').strip()
        format = _dict.get('file format', u'')
        for split_char in '\n, ':
            if split_char in _dict['download url']:
                for url_ in _dict['download url'].split(split_char):
                    if url_.strip():
                        resources.append({'url':url_, 'description':description, 'format':format})
                multiple_urls = True
                break
        if not multiple_urls and _dict['download url']:
            resources.append({'url':_dict['download url'], 'description':description, 'format':format})
        if resources:
            self._resources[name] = resources
            
        author = _dict['author - name']
        author_email = _dict['author - email']
        maintainer = _dict['maintainer - name']
        maintainer_email = _dict['maintainer - email']

        for field in ('geographical granularity', 'temporal granularity'):
            _dict[field] = _dict['%s - other' % field] if \
                           _dict['%s - standard' % field] == 'Other (specify)' else \
                           _dict['%s - standard' % field]
        license_id = license_map.get(_dict['licence'], '')
        if not license_id:
            print 'Warning: license not recognised: %s. Defaulting to UK Crown Copyright.' % _dict['licence']
            license_name = u'ukcrown'

        # extras
        extras_dict = {}
        geo_cover = []
        geo_coverage_type = schema_gov.GeoCoverageType.get_instance()
        spreadsheet_regions = ('england', 'n. ireland', 'scotland', 'wales', 'overseas', 'global')
        for region in spreadsheet_regions:
            munged_region = region.replace('n. ', 'northern_')
            field = 'geographic coverage - %s' % region
            if _dict[field] == u'Yes':
                geo_cover.append(munged_region)
        extras_dict['geographic_coverage'] = geo_coverage_type.form_to_db(geo_cover)
        
        for column in ['date released', 'date updated']:
            try:
                val = field_types.DateType.form_to_db(_dict[column])
            except TypeError, e:
                print "WARNING: Value for column '%s' of '%s' is not understood as a date format." % (column, _dict[column])
                val = _dict[column]
            extras_dict[column.replace(' ', '_')] = val

        given_tags = self._parse_tags(_dict['tags'])
            
        field_map = [
            ['co identifier'],
            ['update frequency'],
            ['temporal granularity', schema_gov.temporal_granularity_options],
            ['geographical granularity', schema_gov.geographic_granularity_options],
            ['categories', schema_gov.category_options],
            ['taxonomy url'],
            ['agency responsible'],
            ['precision'],
            ['department', schema_gov.government_depts],
            ]
        for field_mapping in field_map:
            column = field_mapping[0]
            extras_key = column.replace(' ', '_')
            if column == 'agency responsible':
                extras_key = 'agency'
            elif column in ('co identifier', 'co reference'):
                if _dict.has_key('co reference'):
                    column = 'co reference'
                extras_key = 'external_reference'
            val = _dict[column]
            if len(field_mapping) > 1:
                suggestions = field_mapping[1]
                if val and val not in suggestions:
                    suggestions_lower = [sugg.lower() for sugg in suggestions]
                    if val.lower() in suggestions_lower:
                        val = suggestions[suggestions_lower.index(val.lower())]
                    elif schema_gov.expand_abbreviations(val) in suggestions:
                        val = schema_gov.expand_abbreviations(val)
                    elif val.lower() + 's' in suggestions:
                        val = val.lower() + 's'
                    elif val.replace('&', 'and').strip() in suggestions:
                        val = val.replace('&', 'and').strip()
                if val and val not in suggestions:
                    print "WARNING: Value for column '%s' of '%s' is not in suggestions '%s'" % (column, val, suggestions)
            extras_dict[extras_key] = val
        
        extras_dict['national_statistic'] = u'' # Ignored: _dict['national statistic'].lower()
        extras_dict['import_source'] = 'COSPREAD-%s' % self._current_filename
        for field in ['temporal_coverage_from', 'temporal_coverage_to']:
            extras_dict[field] = u''

        # Create/Update the package object
        existing_pkg = None
        if extras_dict.get('external_reference', None):
            external_ref_query = \
               model.Session.query(model.Package).\
               join('_extras', aliased=True).\
               filter(sqlalchemy.and_(\
                  model.PackageExtra.state==model.State.ACTIVE,\
                  model.PackageExtra.key==unicode('external_reference'))).\
               filter(model.PackageExtra.value == extras_dict['external_reference'])
            if external_ref_query.count() == 1:
                existing_pkg = external_ref_query.one()
            elif external_ref_query.count() > 1:
                print "Warning: More than one package has external reference '%s'." % (extras_dict['external_reference'])
        if not existing_pkg:
            existing_pkg = model.Package.by_name(name)
        if existing_pkg:
            pkg = existing_pkg
            if not line_is_just_adding_multiple_resources:
                self._packages_updated.append(name)
        else:
            pkg = model.Package(name=name)
            self._packages_created.append(name)
        pkg.title = title
        pkg.author = author
        pkg.author_email = author_email
        pkg.maintainer = maintainer
        pkg.maintainer_email = maintainer_email
        pkg.url=url
        pkg.resources = []
        for resource in resources:
            pkg.add_resource(resource['url'], format=resource['format'], description=resource['description'])
        pkg.notes=notes
        pkg.license_id = license_id
        assert pkg.license
        if not existing_pkg:
            user = model.User.by_name(self._username)

            # Setup authz
            model.setup_default_user_roles(pkg, [user]) # does commit & remove
            rev = self._new_revision()

        # Create extras
        pkg.extras = extras_dict

        # Update tags
        pkg_dict = {'name':pkg.name, 'title':pkg.title, 'notes':pkg.notes, 'categories':pkg.extras['categories'],
                    'agency':pkg.extras['agency']}
        tag_set = schema_gov.TagSuggester.suggest_tags(pkg_dict)
        for tag in given_tags:
            tag_set.add(tag)
        current_tags = pkg.tags
        for name in tag_set:
            if name not in current_tags:
                pkg.add_tag_by_name(unicode(name))
        for pkgtag in pkg.package_tags:
            if pkgtag.tag.name not in tag_set:
                pkgtag.delete()

        # Put package in the group
        group = model.Group.by_name(self._groupname)
        if pkg not in group.packages:
            group.packages.append(pkg)
        
        model.Session.commit()

    def _munge(self, name):
        '''Munge a title into a name'''
        # convert spaces to underscores
        name = re.sub(' ', '_', name).lower()        
        # convert symbols to dashes
        name = re.sub('[:]', '_-', name).lower()        
        name = re.sub('[/]', '-', name).lower()        
        # take out not-allowed characters
        name = re.sub('[^a-zA-Z0-9-_]', '', name).lower()
        # remove double underscores
        name = re.sub('__', '_', name).lower()                
        return name[:100]

    def _basic_setup(self):
        # ensure there is a user hmg
        self._username = u'hmg'
        user = model.User.by_name(self._username)
        if not user:
            user = model.User(name=self._username)
            
        # ensure there is a group ukgov
        self._groupname = u'ukgov'
        group = model.Group.by_name(self._groupname)
        if not group:
            group = model.Group(name=self._groupname)
            model.Session.add(group)
            user = model.User.by_name(self._username)
            model.setup_default_user_roles(group, [user])

    def _new_revision(self):
        # Revision info
        rev = model.repo.new_revision()
        rev.author = u'auto-loader'
        rev.log_message = u'Load from cospread database'
        return rev

license_map = {
    u'UK Crown Copyright with data.gov.uk rights':u'ukcrown-withrights',
    u'\xa9 HESA. Not core Crown Copyright.':u'hesa-withrights',
    u'UK Crown Copyright':u'ukcrown',
    u'Crown Copyright':u'ukcrown', }
#agencies_raw = ['Health Protection Agency', 'Office for National Statistics', 'Census', 'Performance Assessment Framework', 'Annual Population Survey', 'Annual Survey of Hours and Earnings', 'Business Registers Unit', 'UK Hydrographic Office', 'Defence Analytical Services and Advice', 'Housing and Communities Agency', 'Tenants Service Authority', 'Higher Education Statistics Agency']
geographic_regions = ['england', 'n. ireland', 'scotland', 'wales', 'overseas', 'global']
