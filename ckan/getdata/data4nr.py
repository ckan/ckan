import re
import os.path
import csv

import ckan.model as model

class Data4Nr(object):
    def __init__(self):
        self._gvt_depts = []
        for raw_dept in gvt_depts_raw + publishers_raw:
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
            data4nr_dict = self._parse_line(row_list, index)
            if data4nr_dict:
                self._load_line_into_db(data4nr_dict, index)
            index += 1
            if index % 100 == 0:
                self._commit_and_report(index)
        self._commit_and_report(index)
#        model.Session.remove()

    def _commit_and_report(self, index):
        print 'Loaded %s lines' % index
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
        name = self._create_name(_dict)
        title = _dict['title']
        url = _dict['data4nr link']
        download_url = _dict['url 1']
        notes = _dict['description']
        author = _dict['publisher']
        for column in ['source', 'geographies',
                       'geographic coverage', 'time coverage',
                       'time coverage (most recent)', 'update frequency',
                       'type of data', 'reliability', 'notes', 'guidelines']:
            if _dict[column]:
                notes += '\n\n%s: %s' % (column.capitalize(), _dict[column])

        extras_dict = {
            'source': _dict['source'],
            'update frequency': _dict['update frequency'],
            }

        existing_pkg = model.Package.by_name(name)
        if existing_pkg:
            pkg = existing_pkg
        else:
            pkg = model.Package(name=name)
        pkg.title = title
        pkg.author = author
        pkg.url=url
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

    def _create_name(self, data4nr_dict):
        name = u'%s_%s' % (data4nr_dict['title'], data4nr_dict['time coverage'])
        return self._munge(name)

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
            
        # ensure there is a group ukgov
        self._groupname = u'ukgov'
        group = model.Group.by_name(self._groupname)
        if not group:
            group = model.Group(name=self._groupname)

    def _new_revision(self):
        # Revision info
        rev = model.repo.new_revision()
        rev.author = u'auto-loader'
        rev.log_message = u'Load from data4nr database'
        return rev

    def _get_tags(self, _dict):
        tags = []

        source = self._normalise(_dict['source'])
        publisher = self._normalise(_dict['publisher'])
        source_tags = []
        publisher_tags = []
        for gvt_dept in self._gvt_depts:
            if gvt_dept in source:
                source_tags.append(self._munge(gvt_dept))
            if gvt_dept in publisher:
                publisher_tags.append(self._munge(gvt_dept))
        if source_tags:
            tags.extend(source_tags)
##        else:
##            tags.append(self._munge(_dict['source']))
        if publisher_tags:
            tags.extend(publisher_tags)
##        else:
##            tags.append(self._munge(_dict['publisher']))
            
        geo = _dict['geographic coverage']
        geo_tags = geo.split(', ')
        for geo_tag in geo_tags:
            tags.append(self._munge(geo_tag))

        title = _dict['title'].lower()
        for keyword in title_tag_words:
            if keyword in title:
                tags.append(self._munge(keyword))
        return tags

    def _normalise(self, txt):
        return txt.lower().replace(',', '')

title_tag_words = ['accident', 'road', 'traffic', 'health', 'illness', 'disease', 'population', 'school', 'accommodation', 'children', 'married', 'emissions', 'benefit', 'alcohol', 'deaths', 'mortality', 'disability', 'unemployment', 'employment', 'armed forces', 'asylum', 'cancer', 'births', 'burglary', 'child', 'tax credit', 'criminal damage', 'drug', 'earnings', 'education', 'economic', 'fire', 'fraud', 'forgery', 'fuel', 'green', 'homeless', 'hospital', 'waiting list', 'housing', 'care', 'income', 'census', 'mental health', 'disablement allowance', 'jobseekers allowance', 'national curriculum', 'older people', 'living environment', 'higher education', 'living environment', 'school absence', '']

gvt_depts_raw = ['Ministry of Justice', 'Department for Culture, Media and Sport', 'Home Office', 'Department of Health', 'Foreign and Commonwealth Office', 'Department for Transport', 'Department for Children, Schools and Families', 'Department for Innovation, Universities and Skills', 'Department for Business, Enterprise and Regulatory Reform', 'Department for Environment, Food and Rural Affairs', 'HM Treasury', 'Northern Ireland Office', 'Privy Council', 'Wales Office', 'Scotland Office', 'Department for Work and Pensions', 'Department for International Development', 'Ministry of Defence', 'Communities and Local Government', 'Cabinet Office', 'Office of the Leader of the House of Commons']
publishers_raw = ['Health Protection Agency', 'Office for National Statistics', 'Census', 'Performance Assessment Framework', 'Annual Population Survey', 'Annual Survey of Hours and Earnings', 'Business Registers Unit', '']
        

    
##        sources = ['Department for Environment Food and Rural Affairs',
##                   'Department of Health',
##                   'Communities and Local Government',
##                   'Office for National Statistics',
##                   'Annual Population Survey',
##                   'Annual Survey of Hours and Earnings',
##                   'Communities and Local Government',
##                   'Census',
##                   'Office of the Deputy Prime Minister',
##                   'Child Maintenance and Enforcement Commission',
##                   'Communities and Local Government'
##                   ]
