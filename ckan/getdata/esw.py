import re
import os

import ckan.model as model

class PipedTableReader:
    def __init__(self, fileobj):
        self._fileobj = fileobj
        self._num_columns = None
        
    def next(self):
        while True:
            line = self._fileobj.readline()
            if line == '':
                raise StopIteration
            if not line.startswith('||'):
                continue
            fields = line.split('||')
            if self._num_columns and len(fields) != self._num_columns:
                print 'Discarding line because %i fields instead of %i: %s' % (len(fields), self._num_columns, fields[0][:20])
                continue
            return [field.strip() for field in fields]

    def __iter__(self):
        return self

    def _set_titles(self, fields):
        self._titles = []
        for field in fields:
            self._titles.append(field.strip("'"))

class Esw(object):
    def __init__(self):
        self._from_uri_re = re.compile('from \[[^\]]+\]\s?')
        self._link_title_re = re.compile('\[\S+\s(.*)\]')
        self._link_uri_re = re.compile('\[(\S+)[^\]]*\]')
        self._link_uri_and_title_re = re.compile('\[(\S+)\s?([^\]]*)\]')
        
    def load_esw_txt_into_db(self, txt_filepath):
        self._basic_setup()
        rev = self._new_revision()
        assert os.path.exists(txt_filepath)
        f_obj = open(txt_filepath, "r")
        reader = PipedTableReader(f_obj)
        index = 0
        for row_list in reader:
            esw_dict = self._parse_line(row_list, index)
            if esw_dict:
                self._load_line_into_db(esw_dict, index)
            index += 1
            if index % 100 == 0:
                self._commit_and_report(index)
        self._commit_and_report(index)

    def _commit_and_report(self, index):
        print 'Loaded %s lines' % index
        model.repo.commit_and_remove()

    def _remove_link(self, txt):
        # Remove pure link: 'from [http:/some.link]'
        txt = self._from_uri_re.sub('', txt)
        # Extract title from link '[http:/some.link The title]' 
        return self._link_title_re.sub(r'\1', txt).strip()

    def _get_link(self, txt):
        return ', '.join(self._link_uri_re.findall(txt))

    def _unwiki_link(self, txt):
        links = self._link_uri_and_title_re.findall(txt)
        return ', '.join(['%s <%s>' % link[::-1] for link in links])
            
    def _create_name(self, esw_dict):
##        if 'John Peel' in esw_dict['Project']:
##            import pdb; pdb.set_trace()
        title = self._remove_link(esw_dict['Project']).strip()        
        title = u'%s' % (title)
        name = self._munge(title)

        # special cases
        if title.startswith('GO annotations'):
            name = self._munge('GO annotations from NCBI and EBI')
        elif title.startswith('Wikipedia'):
            title = u'Wikipedia3'
            name = self._munge(title)

        return name, title

    def _parse_line(self, row_list, line_index):
        values = row_list
        if line_index == 0:
            # titles line
            self._titles = values
            return None
        esw_dict = {}
        print values
        for i, val in enumerate(values):
            val = val.decode('ascii', 'ignore')
            esw_dict[self._titles[i].strip("'")] = unicode(val)
        return esw_dict

    def _load_line_into_db(self, _dict, line_index):
        # Create package
        rev = self._new_revision()
        name, title = self._create_name(_dict)

        download_url = self._get_link(_dict['Archive URL'])
        if download_url == '':
            download_url = self._get_link(_dict['Data Exposed'])
        if download_url == 'URL?':
            download_url = ''

        url = self._get_link(_dict['Project'])
        
        author = self._unwiki_link(_dict['Publisher / Maintainer URI'])
        if author == '[URI]':
            author = self._unwiki_link(_dict['Project'])

        notes = ''
        for column in ['Data Exposed', 'Size of Dump and Data Set',
                       'notes',]:
            if _dict[column]:
                val = _dict[column]
                val = self._link_title_re.sub(r'\1', val)
                notes += '\n\n%s: %s' % (column.capitalize(), val)

        extras_dict = {}

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
#        pkg.license = model.License.by_name(u'Non-OKD Compliant::Crown Copyright')
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

    def _new_revision(self):
        # Revision info
        rev = model.repo.new_revision()
        rev.author = u'auto-loader'
        rev.log_message = u'Load from ESW.org data'
        return rev

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
        # ensure there is a user
        self._username = u'esw_data'
        user = model.User.by_name(self._username)
        if not user:
            user = model.User(name=self._username)
            
        # ensure there is a group
        self._groupname = u'esw'
        group = model.Group.by_name(self._groupname)
        if not group:
            group = model.Group(name=self._groupname)

    def _get_tags(self, _dict):
        tags = ['linked-open-data', 'format-rdf', 'rdf', 'ckanupload.esw.200910']
        return tags
