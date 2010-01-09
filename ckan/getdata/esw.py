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
    license_map = {
        'under a free license':u'OKD Compliant::Other',
        'CC with attribution':u'OKD Compliant::Creative Commons Attribution',
        'Creative Commons with Attributions':u'OKD Compliant::Creative Commons Attribution',
        'Creative Commons Attribution-Noncommercial-Share Alike 3.0 License':u'OKD Compliant::Creative Commons Attribution-ShareAlike',
        '(by-nc-sa)':u'OKD Compliant::Creative Commons Attribution-ShareAlike',
        }
    tag_map = {
        'ontologies':'ontology',
        'ontology':'ontology',
        'gene':'genetics',
        'restaurants':'restaurants',
        'government':'government',
        'environmental':'environment',
        'statistics':'statistics',
        'housing':'housing',
        'population':'population',
        'medical':'medical',
        'medicine':'medical',
        'energy':'energy',
        'library':'library',
        'labor':'labour',
        'wikipedia':'wikipedia',
        'biological':'bio',
        'biotechnology':'biotech',
        'linguistic':'language',
        'clinical':'health',
        'movies':'films',
        'medline':'health',
        'geography':'geo',
        'quotations':'literature',
        'new testament':'bible',
        'semantic web':'semantic-web',
        'linked data':'linked-data',
        'economics':'economics',
        'countries':'geo',
        'dictionary':'dictionary',        
        }
    def __init__(self):
        self._from_uri_re = re.compile('from \[[^\]]+\]\s?')
        self._link_title_re = re.compile('\[\S+\s(.*)\]')
        self._link_uri_re = re.compile('\[(\S+)[^\]]*\]')
        self._link_uri_and_title_re = re.compile('\[(\S+)\s?([^\]]*)\]')

        self._groupname = u'semanticweb'
        
    def load_esw_txt_via_rest(self, txt_filepath, ckanclient):
        self._ckanclient = ckanclient
        self._existing_packages = self._ckanclient.package_register_get()
        self._existing_groups = self._ckanclient.group_register_get()
        for esw_dict, index in self._get_esw_record(txt_filepath):
            package_rec = self._make_ckan_record(esw_dict, index)
            if package_rec:
                self._load_line_via_rest(package_rec)
                if index % 100 == 0:
                    self._report(index)
        self._report(index)

    def load_esw_txt_into_db(self, txt_filepath):
        self._username = u'esw_data'
        self._basic_db_setup()
        rev = self._new_revision()
        for esw_dict, index in self._get_esw_record(txt_filepath):
            package_rec = self._make_ckan_record(esw_dict, index)
            if package_rec:
                self._load_line_into_db(package_rec)
                if index % 100 == 0:
                    self._commit_and_report(index)
        self._commit_and_report(index)

    def _get_esw_record(self, txt_filepath):
        assert os.path.exists(txt_filepath)
        f_obj = open(txt_filepath, "r")
        reader = PipedTableReader(f_obj)
        index = 0
        for row_list in reader:
            esw_dict = self._parse_line(row_list, index)
            if esw_dict:
                yield (esw_dict, index)
            index += 1

    def _report(self, index):
        print 'Loaded %s lines' % index
        
    def _commit_and_report(self, index):
        self._report(index)
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
        title = self._remove_link(esw_dict['Project']).strip()        
        title = u'%s' % (title)
        name = self._munge(title)

        # special cases
        if title.startswith('GO annotations'):
            name = self._munge('GO annotations from NCBI and EBI')
        elif title.startswith('Wikipedia'):
            title = u'Wikipedia3'
            name = self._munge(title)
        elif title == u'BBOP' and u'selected OBO ontologies' in esw_dict['Data Exposed']:
            name = u'bbop-selected'
        elif title == u'Jamendo':
            name = u'jamendo-dbtune'
        elif title == u'MusicBrainz':
            name = None #skip record
        elif title == u'DBpedia':
            name = None #skip record

        return name, title

    def _parse_line(self, row_list, line_index):
        values = row_list
        if line_index == 0:
            # titles line
            self._titles = values
            return None
        esw_dict = {}
        for i, val in enumerate(values):
            val = val.decode('ascii', 'ignore')
            esw_dict[self._titles[i].strip("'")] = unicode(val)
        return esw_dict

    def _make_ckan_record(self, edict, index):
        pdict = {} # package properties
        pdict['name'], pdict['title'] = self._create_name(edict)
        if not pdict['name']:
            # ignore record
            return None

        pdict['download_url'] = self._get_link(edict['Archive URL'])
        if pdict['download_url'] == '':
            pdict['download_url'] = self._get_link(edict['Data Exposed'])
        if pdict['download_url'] == 'URL?':
            pdict['download_url'] = ''

        pdict['url'] = self._get_link(edict['Project'])
        
        pdict['author'] = self._unwiki_link(edict['Publisher / Maintainer URI'])
        if pdict['author'] == '[URI]':
            pdict['author'] = self._unwiki_link(edict['Project'])

        pdict['notes'] = ''
        for column in ['Data Exposed', 'Size of Dump and Data Set',
                       'notes',]:
            if edict[column]:
                val = edict[column]
                val = self._link_title_re.sub(r'\1', val)
                pdict['notes'] += '\n\n%s: %s' % (column.capitalize(), val)

        pdict['extras'] = {}
        license_txt = None
        for key, license_ in self.license_map.items():
            if key in edict['notes']:
                license_txt = license_
        pdict['license'] = license_txt
        pdict['tags'] = ['linked-open-data', 'format-rdf', 'rdf', 'ckanupload.esw.200910']
        record_lower = ('%s %s %s' % (edict['Data Exposed'], edict['Project'], edict['notes'])).lower()
        for word, tag in self.tag_map.items():
            if word in record_lower:
                pdict['tags'].append(tag)
        pdict['groups'] = [self._groupname]
        print pdict
        return pdict

    def _load_line_via_rest(self, pdict):
        if pdict['license']:
            license_ = model.License.by_name(pdict['license'])
            assert license_, pdict['license']
            pdict['license_id'] = unicode(str(license_.id))
            del pdict['license']

        mode = 'create'
        while self._existing_packages and \
                  pdict['name'] in self._existing_packages:
            # package with this name exists - check if it was
            # created by this script and therefore we can edit it
            pkg = self._ckanclient.package_entity_get(pdict['name'])
            for tag in pkg['tags']:
                if tag.startswith('ckanupload.esw.'):
                    mode = 'update'
            if mode == 'update':
                break
            # not associated with this script so
            # avoid overwriting it by changing name
            pdict['name'] = pdict['name'] + '_'

        if mode == 'update':
            # update package
            for key, value in pdict.items():
                pkg[key] = value
            self._ckanclient.package_entity_put(pkg)
        elif mode == 'create':
            # create package
            self._ckanclient.package_register_post(pdict)
        assert self._ckanclient.last_status == 200, '%s: %s' % (mode, self._ckanclient.last_url_error or self._ckanclient.last_http_error or self._ckanclient.last_status)

        # Put it in the group
        for groupname in pdict['groups']:
            if not self._existing_groups or groupname not in self._existing_groups:
                # create group
                group_entity = {
                    'name': groupname,
                    }
                self._ckanclient.group_register_post(group_entity)
                self._existing_groups = self._ckanclient.group_register_get()
                assert groupname in self._existing_groups
            # ensure pkg is in group
            group = self._ckanclient.group_entity_get(groupname)
            del group[u'id']
            if pdict['name'] not in group['packages']:
                if group['packages']:
                    group['packages'].append(pdict['name'])
                else:
                    group['packages'] = [pdict['name']]
                self._ckanclient.group_entity_put(group)
    
    def _load_line_into_db(self, pdict):
        rev = self._new_revision()

        existing_pkg = model.Package.by_name(pdict['name'])
        if existing_pkg:
            pkg = existing_pkg
        else:
            pkg = model.Package(name=pdict['name'])
        for attr in ['title', 'author', 'url', 'download_url', 'notes']:
            setattr(pkg, attr, pdict[attr])
        if pdict['license']:
            license = model.License.by_name(pdict['license'])
        else:
            license = None
        pkg.license = license

        if not existing_pkg:
            user = model.User.by_name(self._username)

            # Setup authz
            model.setup_default_user_roles(pkg, [user]) # does commit & remove
            rev = self._new_revision()

        # Create extras
        new_extra_keys = []
        for key, value in pdict['extras'].items():
            extra = model.Session.query(model.PackageExtra).filter_by(package=pkg, key=unicode(key)).all()
            if extra:
                extra[0].value = value
            else:
                new_extra_keys.append(key)

        for key in new_extra_keys:
            model.PackageExtra(package=pkg, key=unicode(key), value=unicode(extras_dict[key]))

        # Update tags
        taglist = pdict['tags']
        current_tags = pkg.tags
        for name in taglist:
            if name not in current_tags:
                pkg.add_tag_by_name(unicode(name))
        for pkgtag in pkg.package_tags:
            if pkgtag.tag.name not in taglist:
                pkgtag.delete()

        # Put package in the group
        for group in pdict['groups']:
            group = model.Group.by_name(group)
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

    def _basic_db_setup(self):
        # ensure there is a user
        user = model.User.by_name(self._username)
        if not user:
            user = model.User(name=self._username)
            
        # ensure there is a group
        group = model.Group.by_name(self._groupname)
        if not group:
            group = model.Group(name=self._groupname)

