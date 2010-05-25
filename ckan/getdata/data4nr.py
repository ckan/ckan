import re
import os.path
import csv

import ckan.model as model
from ckan.lib import schema_gov
from ckan.lib import field_types

class Data4Nr(object):
    def load_csv_into_db(self, csv_filepath):
        self._basic_setup()
        rev = self._new_revision()
        assert os.path.exists(csv_filepath)
        f_obj = open(csv_filepath, "r")
        self._current_filename = os.path.basename(csv_filepath)
        reader = csv.reader(f_obj)
        index = 0
        reader.next()
        for row_list in reader:
            data4nr_dict = self._parse_line(row_list, index)
            if data4nr_dict:
                self._load_line_into_db(data4nr_dict, index)
            index += 1
            if index % 100 == 0:
                self._commit_and_report(index)
        self._commit_and_report(index)

    def _commit_and_report(self, index):
        print 'Loaded %s lines (%s new, %s existing packages)' % (index, len(self._new_pkgs), len(self._existing_pkgs))
        model.repo.commit_and_remove()

    def _parse_line(self, row_list, line_index):
        values = row_list
        if len(values) < 24:
            print 'Error: Line %i has not enough values: %i' % (line_index, len(values))
            return None
        if line_index == 0:
            # titles line
            self._titles = values
            return None
        data4nr_dict = {}
        for i, val in enumerate(values):
            data4nr_dict[self._titles[i].lower()] = unicode(val)
        return data4nr_dict

    def _load_line_into_db(self, _dict, line_index):
        # Create package
        rev = self._new_revision()
        old_name, new_name = self._create_name(_dict)
        title = _dict['title']
        url = _dict['data4nr link']
        res_url = _dict['url 1']
        def add_fullstop(str):
            if str:
                str = str + '.'
            return str
        res_description = ' '.join([add_fullstop(_dict['url notes']),
                                    add_fullstop(_dict['url description 1'])])
        notes = _dict['description']
        author = _dict['publisher']
        for column in ['source', 'publisher', 'geographies',
                       'geographic coverage', 'time coverage',
                       'type of data', 'notes', 'guidelines',
                       ]:
            if _dict[column]:
                notes += '\n\n%s: %s' % (column.capitalize(), _dict[column])

        department = u''
        dept_fields = '%s %s' % (_dict['source'], _dict['publisher'])
        dept_fields = schema_gov.expand_abbreviations(dept_fields).lower().replace(',', '')
        if not hasattr(self, 'munged_government_depts'):
            self.munged_government_depts = [(dept, dept.lower().replace(',', '')) for dept in schema_gov.government_depts]
        for dept, munged_dept in self.munged_government_depts:
            if munged_dept in dept_fields:
                department = dept
        extras_dict = {
            'update_frequency': _dict['update frequency'],
            'department':department,
            }
        for extra_key in ['categories', 'geographic_granularity', 'temporal_granularity', 'date_updated', 'agency', 'taxonomy_url', 'date_released']:
            extras_dict[extra_key] = u''
        extras_dict['national_statistic'] = u'' #u'no'
        geo_cover = []
        geo_coverage_type = schema_gov.GeoCoverageType.get_instance()
        geo_val = _dict['geographic coverage']
        geo_val_munged = schema_gov.GeoCoverageType.munge(geo_val.replace('n. ', 'northern '))
        for munged_region in geo_coverage_type.regions_munged:
            if munged_region in geo_val_munged:
                geo_cover.append(munged_region)
        extras_dict['geographic_coverage'] = geo_coverage_type.form_to_db(geo_cover)
        extras_dict['temporal_coverage_from'], extras_dict['temporal_coverage_to'] = self._parse_temporal_coverage(_dict['time coverage'])
        extras_dict['external_reference'] = 'DATA4NR-%s' % _dict['id'] if _dict['id'] else u''
        extras_dict['precision'] = _dict['reliability'] or u''
        extras_dict['import_source'] = 'DATA4NR-%s' % self._current_filename

        # Edit package object
        if not url:
            print "Error: No url for package '%s' - cannot insert in db" % title
            return
        q = model.Session.query(model.Package).filter_by(url=url)
        if q.count() == 1:
            pkg = q.one()
            self._existing_pkgs.append(pkg.name)
            existing_pkg = True
        elif q.count() > 1:
            print "Error: Duplicate url discovered '%s', not updating record." % url
            return
        else:
            pkg_same_name = model.Package.by_name(new_name)
            if pkg_same_name:
                prev_name = new_name
                while model.Package.by_name(new_name):
                    new_name += '_'
                print "Warning: New data4nr ID '%s' but name already taken. Reverting to %s" % (prev_name, new_name)
            pkg = model.Package(name=new_name)
            model.Session.add(pkg)
            self._new_pkgs.append(pkg.name)
            print 'New package: %s (old name=%s)' % (new_name, old_name)
            existing_pkg = False
        pkg.title = title
        pkg.author = author
        pkg.url=url
        pkg.resources = []
        pkg.add_resource(res_url, description=res_description)
        pkg.notes=notes
        pkg.license_id = u'ukcrown-withrights'
        if not existing_pkg:
            user = model.User.by_name(self._username)

            # Setup authz
            model.setup_default_user_roles(pkg, [user]) # does commit & remove
            rev = self._new_revision()

        # Create extras
        new_extra_keys = []
        pkg.extras = {}
        for key, value in extras_dict.items():
            pkg.extras[key] = value

        # Update tags
        pkg_dict = {'name':pkg.name, 'title':pkg.title, 'notes':pkg.notes,
                    'categories':'',
                    'agency':dept_fields}
        taglist = schema_gov.TagSuggester.suggest_tags(pkg_dict)
        current_tags = pkg.tags
        for name in taglist:
            if name not in current_tags:
                pkg.add_tag_by_name(unicode(name))
        for pkgtag in pkg.package_tags:
            if pkgtag.tag.name not in taglist:
                pkgtag.delete()

        # Put package in the group
        group = model.Group.by_name(self._groupname)
        if pkg not in group.packages:
            group.packages.append(pkg)
        
        model.Session.commit()

    def _create_name(self, data4nr_dict):
        old_name = u'%s_%s' % (data4nr_dict['title'], data4nr_dict['time coverage'])
        new_name = u'%s' % data4nr_dict['title']
        return self._munge(old_name), self._munge(new_name)

    def _munge(self, name):
        # convert spaces to underscores
        name = re.sub(' ', '_', name).lower()        
        # convert symbols to dashes
        name = re.sub('[:]', '_-', name).lower()        
        name = re.sub('[/]', '-', name).lower()        
        # take out not allowed characters
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
            model.Session.add(user)
            
        # ensure there is a group ukgov
        self._groupname = u'ukgov'
        group = model.Group.by_name(self._groupname)
        if not group:
            group = model.Group(name=self._groupname)
            model.Session.add(group)
            user = model.User.by_name(self._username)
            model.setup_default_user_roles(group, [user])

        self._existing_pkgs = []
        self._new_pkgs = []

    def _new_revision(self):
        # Revision info
        rev = model.repo.new_revision()
        rev.author = u'auto-loader'
        rev.log_message = u'Load from data4nr database'
        return rev

    def _parse_temporal_coverage(self, field):
        # Temporal coverage
        # 2000 to 2006       -> 2000 - 2006
        # 2003/04 to 2005/06 -> 2003 - 2006
        # 2003-05, 2007      -> 2003 - 2007
        # 2006-2007          -> 2006 - 2007
        # 2001               -> 2001 - 2001
        if not hasattr(self, 'temporal_point'):
            self.temporal_point = re.compile('^(?:[^\d]*)(\d{2,4})(?:\s\(.+\))?$')
            self.temporal_period_simple = re.compile('^(?:[^\d]*)(\d{2,4})\s?[/\-]\s?(\d{2,4})(?:\s\(.+\))?(?:\s[^\d]+)?$')
            self.temporal_period_complex = re.compile('^(?:[^\d]*)(\d{2,4})(\s?[/\-]\s?\d{2,4})?\s?[a-z,]+\s?(\d{2,4}\s?[/\-]\s?)?(\d{2,4})')
            self.months_lower = [month.lower() for month in field_types.months]
            self.full_date = re.compile('\d{1,2}/\d{1,2}/(\d{1,4})')
        from1, from2, to1, to2 = [None]*4
        # remove any month words - confuses things
        field = field.lower()
        for month in self.months_lower:
            field = re.sub(month, '', field)
        field = re.sub('  ', ' ', field)
        # convert full_date to a year - confuses things
        field = self.full_date.sub(r'\1', field)
        # special cases
        if field == u'2004/05, to 2008/09':
            field = u'2004/05 to 2008/09'
        # match against known formats
        if not field:
            return (u'', u'')
        match = self.temporal_point.match(field)
        if match:
            from1 = to1 = match.groups()[0]
        else:
            match = self.temporal_period_simple.match(field)
            if match:
                from1, to1 = match.groups()                
            else:
                match = self.temporal_period_complex.match(field)
                if match:
                    from1, from2, to1, to2 = match.groups()
                else:
                    print "WARNING: Temporal coverage format not recognised: '%s'" % field
                    return (field, u'')
        from_ = self._process_years(from1, from2, min)
        to = self._process_years(to1, to2, max)
        return (unicode(from_), unicode(to))

    def _process_years(self, y1, y2, choose_func):
        add_centurys = field_types.DateType.add_centurys_to_two_digit_year
        if y1 is None and y2 is None:
            return None
        elif y1 is not None and y2 is not None:
            years = []
            if y1 is not None:
                y1 = y1.strip('/- ')
            if y2 is not None:
                y2 = y2.strip('/- ')
            for y, other_y in [(y1, y2), (y2, y1)]:
                if y:
                    y_int = int(y)
                    other_y_int = int(other_y)
                    if other_y is not None and len(y) < 4 and len(other_y) == 4:
                        y_int = add_centurys(y_int, other_y_int)
                    elif len(y) < 4:
                        y_int = add_centurys(y_int, 2010)
                    years.append(y_int)
            return choose_func(years)
        else:
            y = y1 or y2
            y = y.strip('/-')
            y_int = int(y)
            if len(y) < 4:
                y_int = add_centurys(y_int, 2010)
            return y_int
