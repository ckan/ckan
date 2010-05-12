import xml.sax
import re
import os
import glob
import logging

import ckan.model as model
from ckan.lib import schema_gov
from ckan.lib import field_types

guid_prefix = 'http://www.statistics.gov.uk/'

class Data(object):
    def load_xml_into_db(self, xml_filepaths, log=False):
        self._basic_setup()
        self._logging = log
#        rev = self._new_revision()
        if isinstance(xml_filepaths, (str, unicode)):
            if '?' in xml_filepaths or '*' in xml_filepaths:
                xml_filepaths = glob.glob(xml_filepaths)
            else:
                assert os.path.exists(xml_filepaths), xml_filepaths
                xml_filepaths = [xml_filepaths]
        else:
            xml_filepaths = xml_filepaths
        handler = OnsXmlHandler(self.load_item)
        self._log(logging.info, 'Loading %i ONS files' % len(xml_filepaths))
        for xml_filepath in xml_filepaths:
            self._log(logging.info, 'Loading ONS file: %s' % xml_filepath)
            self._current_filename = os.path.basename(xml_filepath)
            parser = xml.sax.parse(xml_filepath, handler)
            self._commit_and_report()

    def load_item(self, item):
        assert isinstance(item, dict)
        self._item_count += 1
        if self._item_count % 100 == 0:
            self._commit_and_report()

        # process item
        title, release = self._split_title(item['title'])
        munged_title = schema_gov.name_munge(title)
        pkg = model.Package.by_name(munged_title)
        department = self._source_to_department(item['hub:source-agency'])
        if pkg and pkg.extras.get('department') != department:
            munged_title = schema_gov.name_munge('%s - %s' % (title, department))
            pkg = model.Package.by_name(munged_title)
        while pkg and not pkg.extras.get('import_source', u'').startswith('ONS'):
            print 'Avoiding clash with non-ONS (%s) item of similar name: %s' % (pkg.extras.get('import_source'), munged_title)
            munged_title += '_'
            pkg = model.Package.by_name(munged_title)


        # Resources
        guid = item['guid'] or None
        if guid:
            assert guid.startswith(guid_prefix)
            guid = guid[len(guid_prefix):]
            assert 'http' not in guid, guid
        existing_resource = None
        if guid and pkg:
            for res in pkg.resources:
                if res.description:
                    for desc_bit in res.description.split('|'):
                        if desc_bit.strip() == guid:
                            existing_resource = res
                            break
        url = item.get('link', None)
        descriptors = []
        if release:
            descriptors.append(release)
        if guid:
            descriptors.append(guid)
        description = ' | '.join(descriptors)

        notes_list = []
        if item['description']:
            notes_list.append(item['description'])
        for column, name in [('hub:source-agency', 'Source agency'),
                             ('hub:designation', 'Designation'),
                             ('hub:language', 'Language'),
                             ('hub:altTitle', 'Alternative title'),
                       ]:
            if item[column]:
                notes_list.append('%s: %s' % (name, item[column]))
        notes = '\n\n'.join(notes_list)
#        rev = self._new_revision()

        extras = {'geographic_coverage':u'', 'external_reference':u'', 'temporal_granularity':u'', 'date_updated':u'', 'agency':u'', 'precision':u'', 'geographical_granularity':u'', 'temporal_coverage_from':u'', 'temporal_coverage_to':u'', 'national_statistic':u'', 'department':u'', 'update_frequency':u'', 'date_released':u'', 'categories':u''}
        date_released = u''
        if item['pubDate']:
            try:
                date_released = field_types.DateType.iso_to_db(item['pubDate'], '%a, %d %b %Y %H:%M:%S %Z')
            except TypeError, e:
                self._log(logging.warning, 'Warning: Could not read format of publication (release) date: %r' % e.args)
        extras['date_released'] = date_released
        extras['department'] = self._source_to_department(item['hub:source-agency'])
        extras['agency'] = item['hub:source-agency'] if not extras['department'] else u''
        extras['categories'] = item['hub:theme']
        geo_coverage_type = schema_gov.GeoCoverageType.get_instance()
        extras['geographic_coverage'] = geo_coverage_type.str_to_db(item['hub:coverage'])
        extras['national_statistic'] = 'yes' if item['hub:designation'] == 'National Statistics' or item['hub:designation'] == 'National Statistics' else 'no'
        extras['geographical_granularity'] = item['hub:geographic-breakdown']
        extras['external_reference'] = u'ONSHUB'
        for update_frequency_suggestion in schema_gov.update_frequency_suggestions:
            item_info = ('%s %s' % (item['title'], item['description'])).lower()
            if update_frequency_suggestion in item_info:
                extras['update_frequency'] = update_frequency_suggestion
            elif update_frequency_suggestion.endswith('ly'):
                if update_frequency_suggestion.rstrip('ly') in item_info:
                    extras['update_frequency'] = update_frequency_suggestion
        extras['import_source'] = 'ONS-%s' % self._current_filename 

        tags = set()
        pkg_dict = {'name':munged_title, 'title':title, 'notes':notes,
                    'categories':extras['categories'],
                    'agency':extras['agency']}
        suggested_tags = schema_gov.TagSuggester.suggest_tags(pkg_dict)
        for keyword in item['hub:ipsv'].split(';') + \
                item['hub:keywords'].split(';') + \
                item['hub:nscl'].split(';') + \
                list(suggested_tags):
            tags.add(schema_gov.tag_munge(keyword))


        # update package
        if not pkg:
            pkg = model.Package(name=munged_title)
            model.Session.add(pkg)
            self._new_package_count += 1
            is_new_package = True
            rev = self._new_revision('New package %s' % munged_title)
##            rev = self._new_revision()
##            model.Session.flush()

        else:
            rev = self._new_revision('Edit package %s' % munged_title)
            is_new_package = False
            

        pkg.title = title
        pkg.notes = notes
        pkg.license_id = self._crown_license_id
        pkg.extras = extras
        if extras['department']:
            pkg.author = extras['department']

        if existing_resource:
            res = existing_resource
            res.download_url = url
            res.description = description
        else:
            pkg.add_resource(url, description=description)
        
        existing_tags = pkg.tags
        for pkgtag in pkg.package_tags:
            if pkgtag.tag.name not in tags:
                pkgtag.delete()
            elif pkgtag.tag.name in existing_tags:
                tags.remove(pkgtag.tag.name)
##        if tags:
##            rev = self._new_revision()
        for tag in tags:
            pkg.add_tag_by_name(unicode(tag), autoflush=False)

        group = model.Session.query(model.Group).get(self._group_id)
        if pkg not in group.packages:
            group.packages.append(pkg)

        if is_new_package:
            # Setup authz
            user = model.Session.query(model.User).get(self._user_id)
            pkg = model.Package.by_name(munged_title)
            model.setup_default_user_roles(pkg, [user]) # does commit & remove

        model.repo.commit_and_remove()
#        model.Session.flush()

    def _source_to_department(self, source):
        dept_given = schema_gov.expand_abbreviations(source)
        department = None
        if '(Northern Ireland)' in dept_given:
            department = u'Northern Ireland Executive'
        for dept in schema_gov.government_depts:
            if dept_given in dept or dept_given.replace('Service', 'Services') in dept or dept_given.replace('Dept', 'Department') in dept:
                department = unicode(dept)
                
        if department:
            assert department in schema_gov.government_depts, department
            return department
        else:
            if dept_given and dept_given not in ['Office for National Statistics', 'Health Protection Agency', 'Information Centre for Health and Social Care', 'General Register Office for Scotland', 'Northern Ireland Statistics and Research Agency', 'National Health Service in Scotland', 'National Treatment Agency', 'Police Service of Northern Ireland (PSNI)', 'Child Maintenance and Enforcement Commission', 'Health and Safety Executive', 'ISD Scotland (part of NHS National Services Scotland)']:
                self._log(logging.warning, 'Warning: Double check this is not a gvt department source: %s' % dept_given)
            return None
        


    def _split_title(self, xml_title):
        if not hasattr(self, 'title_re'):
            self.title_re = re.compile(r'([^-]+)\s-\s(.*)')
        match = self.title_re.match(xml_title)
        if not match:
            'Warning: Could not split title: %s' % xml_title
            return (xml_title, None)
        return match.groups()

    def _commit_and_report(self):
        self._log(logging.info, 'Loaded %i lines with %i new packages' % (self._item_count, self._new_package_count))
        model.repo.commit_and_remove()
    
    def _basic_setup(self):
        self._item_count = 0
        self._new_package_count = 0
        self._crown_license_id = u'ukcrown-withrights'


        # ensure there is a user hmg
        username = u'hmg'
        user = model.User.by_name(username)
        if not user:
            self._new_revision('Adding user')
            user = model.User(name=username)
            model.Session.add(user)
            
        # ensure there is a group ukgov
        groupname = u'ukgov'
        group = model.Group.by_name(groupname)
        if not group:
            self._new_revision('Adding group')
            group = model.Group(name=groupname)
            model.Session.add(group)
            user = model.User.by_name(username)
            model.setup_default_user_roles(group, [user])

        if model.Session.new:
            model.repo.commit_and_remove()
        self._user_id = model.User.by_name(username).id
        self._group_id = model.Group.by_name(groupname).id

    def _new_revision(self, msg=None):
        # Revision info
        rev = model.repo.new_revision()
        rev.author = u'auto-loader'
        rev.message = u'Load from ONS feed'
        if msg:
            rev.message += u' - %s' % msg
        return rev

    def _log(self, log_func, msg):
        if self._logging:
            log_func(msg)
        else:
            print '%s: %s' % (log_func.func_name, msg)

class OnsXmlHandler(xml.sax.handler.ContentHandler):
    def __init__(self, load_item_func):
        xml.sax.handler.ContentHandler.__init__(self)
        self._load_item_func = load_item_func
    
    def startDocument(self):
        self._level = 0
        self._item_dict = {}        
        
    def startElement(self, name, attrs):
        self._level += 1
        if self._level == 1:
            if name == 'rss':
                pass
            else:
                print 'Warning: Not expecting element %s at level %i' % (name, self._level)
        elif self._level == 2:
            if name == 'channel':
                pass
            else:
                print 'Warning: Not expecting element %s at level %i' % (name, self._level)
        elif self._level == 3:
            if name == 'item':
                assert not self._item_dict
            elif name in ('title', 'link', 'description', 'language', 'pubDate', 'atom:link'):
                pass
        elif self._level == 4:
            assert name in ('title', 'link', 'description', 'pubDate', 'guid',
                            'hub:source-agency', 'hub:theme', 'hub:coverage',
                            'hub:designation', 'hub:geographic-breakdown',
                            'hub:ipsv', 'hub:keywords', 'hub:altTitle',
                            'hub:language',
                            'hub:nscl'), name
            self._item_element = name
            self._item_data = u''

    def characters(self, chrs):
        if self._level == 4:
            self._item_data += chrs

    def endElement(self, name):
        if self._level == 3:
            if self._item_dict:
                self._load_item_func(self._item_dict)
            self._item_dict = {}
        elif self._level == 4:
            self._item_dict[self._item_element] = self._item_data
            self._item_element = self._item_data = None
        self._level -= 1
