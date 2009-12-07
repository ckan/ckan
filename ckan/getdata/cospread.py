import re
import os.path
import csv

import ckan.model as model

class Data(object):
    def __init__(self):
        self._download_urls = {} # name:[url, url]
        self._titles_complete = False
        self._title_line_1 = None
        self._title_line_2 = None
        self._gvt_depts = []
        for raw_dept in gvt_depts_raw + agencies_raw:
            self._gvt_depts.append(self._normalise(raw_dept))
    
    def load_csv_into_db(self, csv_filepath):
        self._basic_setup()
        rev = self._new_revision()
        assert os.path.exists(csv_filepath)
        f_obj = open(csv_filepath, "r")
        reader = csv.reader(f_obj)
        index = 0
        reader.next()
        for row_list in reader:
            cospread_dict = self._parse_line(row_list, index)
            if cospread_dict:
                self._load_line_into_db(cospread_dict, index)
            index += 1
            if index % 100 == 0:
                self._commit_and_report(index)
        self._commit_and_report(index)

    def _commit_and_report(self, index):
        print 'Loaded %s lines' % index
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
                elif title in ('contact', 'maintainer'):
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

    def _load_line_into_db(self, _dict, line_index):
        # Create package
        rev = self._new_revision()
        name = self._munge(_dict['name'].replace(' ', '').replace('.', '_').replace('&', 'and'))
        print "NAME", name
        if self._download_urls.has_key(name):
            download_urls = self._download_urls[name]
        else:
            download_urls = []
        title = _dict['title']
        url = _dict['url']
        notes = _dict['notes']
        for split_char in '\n, ':
            if split_char in _dict['download url']:
                download_urls = [url_.strip() for url_ in _dict['download url'].split(split_char)]
                break
        if download_urls:
            download_urls.append(_dict['download url'])
            notes += '\n\nDownload URLs:'
            for download_url in download_urls:
                notes += '\n * %s' % download_url
            download_url = None
            self._download_urls[name] = download_urls
        else:
            download_url = _dict['download url']
            self._download_urls[name] = [download_url]
        author = _dict['contact - name']
        author_email = _dict['contact - email']
        maintainer = _dict['maintainer - name']
        maintainer_email = _dict['maintainer - email']

        for field in ('geographical granularity', 'temporal granularity'):
            _dict[field] = _dict['%s - other' % field] if \
                           _dict['%s - standard' % field] == 'Other (specify)' else \
                           _dict['%s - standard' % field]

        geo_cover = []
        for region in geographic_regions:
            field = 'geographic coverage - %s' % region
            region_str = region.capitalize().replace('ireland', 'Ireland')
            geo_cover.append('%s %s' % (region_str, _dict[field]))
        _dict['geographic coverage'] = ', '.join(geo_cover)
            
        for column in ['date released', 'date updated', 'update frequency',
                       'geographical granularity', 'geographic coverage',
                       'temporal granularity', 'file format', 'categories',
                       'national statistic', 'precision', 'taxonomy url',
                       'department', 'agency responsible']:
            if _dict[column]:
                notes += '\n\n%s: %s' % (column.capitalize(), _dict[column])

        extras_dict = {
            'co_id': _dict['co identifier'],
            'update frequency': _dict['update frequency'],
            }

        # TODO search by co_id
        existing_pkg = model.Package.by_name(name)
        if existing_pkg:
            pkg = existing_pkg
        else:
            pkg = model.Package(name=name)
        pkg.title = title
        pkg.author = author
        pkg.author_email = author_email
        pkg.maintainer = maintainer
        pkg.maintainer_email = maintainer_email
        pkg.url=url
        pkg.resources = []
        if download_url:
            pkg.add_resource(download_url)
        pkg.notes=notes
        pkg.license = model.License.by_name(u'Non-OKD Compliant::Crown Copyright')
        if not existing_pkg:
            user = model.User.by_name(self._username)

            # Setup authz
            model.setup_default_user_roles(pkg, [user]) # does commit & remove
            rev = self._new_revision()

        # Create extras
        new_extra_keys = []
        for key, value in extras_dict.items():
            extra = model.PackageExtra.query.filter_by(package=pkg, key=unicode(key)).all()
            if extra:
                extra[0].value = value
            else:
                new_extra_keys.append(key)

        for key in new_extra_keys:
            model.PackageExtra(package=pkg, key=unicode(key), value=unicode(extras_dict[key]))

        # Update tags
        taglist = self._get_tags(_dict)
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

    def _tag_munge(self, name):
        return self._munge(name).replace('_', '-').replace('--', '-')

    def _munge(self, name):
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

    def _new_revision(self):
        # Revision info
        rev = model.repo.new_revision()
        rev.author = u'auto-loader'
        rev.log_message = u'Load from cospread database'
        return rev

    def _get_tags(self, _dict):
        tags = []

        for field in ('department', 'agency responsible', 'tags', 'categories'):
            value = _dict[field]
            norm_value = self._normalise(value)
            for gvt_dept in self._gvt_depts:
                if gvt_dept in norm_value:
                    tags.append(self._tag_munge(gvt_dept))
            for abbreviation in abbreviations.keys():
                if abbreviation in value:
                    tags.append(self._tag_munge(abbreviations[abbreviation]))

        for region in geographic_regions:
            field = 'geographic coverage - %s' % region
            if 'yes' in _dict[field].lower():
                tagname = region.replace('n. ', 'northern ')
                tags.append(self._tag_munge(tagname))

        title = _dict['title'].lower()
        for keyword in title_tag_words:
            if keyword in title:
                tags.append(self._tag_munge(keyword))
        return tags

    def _normalise(self, txt):
        return txt.lower().replace(',', '')

title_tag_words = ['accident', 'road', 'traffic', 'health', 'illness', 'disease', 'population', 'school', 'accommodation', 'children', 'married', 'emissions', 'benefit', 'alcohol', 'deaths', 'mortality', 'disability', 'unemployment', 'employment', 'armed forces', 'asylum', 'cancer', 'births', 'burglary', 'child', 'tax credit', 'criminal damage', 'drug', 'earnings', 'education', 'economic', 'fire', 'fraud', 'forgery', 'fuel', 'green', 'homeless', 'hospital', 'waiting list', 'housing', 'care', 'income', 'census', 'mental health', 'disablement allowance', 'jobseekers allowance', 'national curriculum', 'older people', 'living environment', 'higher education', 'living environment', 'school absence', 'local authority', 'carbon dioxide', 'energy', 'teachers', 'fostering', 'tide', 'sunrise', 'sunset', 'gas', 'electricity', 'transport', 'veterinary', 'fishing', 'export', 'fisheries', 'pest', 'recycling', 'waste', 'crime', 'anti-social behaviour', 'police', 'refugee', 'identity card', 'immigration', 'planning', 'communities', 'lettings', 'finance', 'ethnicity', 'trading standards', 'trade', 'business', 'child protection']

gvt_depts_raw = ['Ministry of Justice', 'Department for Culture, Media and Sport', 'Home Office', 'Department of Health', 'Foreign and Commonwealth Office', 'Department for Transport', 'Department for Children, Schools and Families', 'Department for Innovation and Skills', 'Department for Business, Enterprise and Regulatory Reform', 'Department for Environment, Food and Rural Affairs', 'HM Treasury', 'Northern Ireland Office', 'Privy Council', 'Wales Office', 'Scotland Office', 'Department for Work and Pensions', 'Department for International Development', 'Ministry of Defence', 'Communities and Local Government', 'Cabinet Office', 'Office of the Leader of the House of Commons', 'Department for Energy and Climate Change']
agencies_raw = ['Health Protection Agency', 'Office for National Statistics', 'Census', 'Performance Assessment Framework', 'Annual Population Survey', 'Annual Survey of Hours and Earnings', 'Business Registers Unit', 'UK Hydrographic Office', 'Defence Analytical Services and Advice', 'Housing and Communities Agency', 'Tenants Service Authority', 'Higher Education Statistics Agency']
abbreviations = {'DCSF':'Department for Children, Schools and Families', 'VLA':'Vetinary Laboratories Agency', 'MFA':'Marine and Fisheries Agency', 'CEFAS':'Centre of Environment, Fisheries and Aquaculture Science', 'FERA':'Food and Environment Research Agency', 'DEFRA':'Department for Environment, Food and Rural Affairs', 'CRB':'Criminal Records Bureau', 'UKBA':'UK Border Agency', 'IPS':'Identity and Passport Service', 'NPIA':'National Policing Improvement Agency', 'CIB':'Company Investigation Branch', 'IPO':'Intellectual Property Office'}
geographic_regions = ['england', 'n. ireland', 'scotland', 'wales', 'overseas', 'global']
