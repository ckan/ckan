import re
import os.path
import csv

import ckan.model as model

class Data4Nr(object):
    comment = 'Load from data4nr database'    
    
    def load_csv_into_db(self, csv_filepath):
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

    def _commit_and_report(self, index):
        #print 'Loaded %s lines' % index
        rev = model.repo.new_revision()
        rev.comment = self.comment
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
        pkg.download_url=download_url
        pkg.notes=notes
        
        rev = model.repo.new_revision()
        rev.comment = self.comment

        if not existing_pkg:
            model.Session.commit()
            model.setup_default_user_roles(pkg)
            pkg = model.Package.by_name(name)

        new_extra_keys = []
        for key, value in extras_dict.items():
            extra = model.PackageExtra.query.filter_by(package=pkg, key=unicode(key)).all()
            if extra:
                extra[0].value = value
            else:
                new_extra_keys.append(key)

        for key in new_extra_keys:
            model.PackageExtra(package=pkg, key=unicode(key), value=unicode(extras_dict[key]))
        
        rev = model.repo.new_revision()
        rev.comment = self.comment
        model.Session.commit()


    def _create_name(self, data4nr_dict):
        name = u'%s-%s' % (data4nr_dict['title'], data4nr_dict['time coverage'])
        # convert spaces to underscores
        name = re.sub(' ', '_', name).lower()        
        # convert symbols to dashes
        name = re.sub('[:/,]', '-', name).lower()        
        # take out not allowed characters
        name = re.sub('[^a-zA-Z0-9-_]', '', name).lower()
        return name[:100]
            
