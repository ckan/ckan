import csv
import datetime
from sqlalchemy import orm

import ckan.model as model
import ckan.model
from ckan.common import json, OrderedDict

class SimpleDumper(object):
    '''Dumps just package data but including tags, groups, license text etc'''
    def dump(self, dump_file_obj, format='json', query=None):
        if query is None:
            query = model.Session.query(model.Package)
            active = model.State.ACTIVE
            query = query.filter_by(state=active)
        if format == 'csv':
            self.dump_csv(dump_file_obj, query)
        elif format == 'json':
            self.dump_json(dump_file_obj, query)
        else:
            raise Exception('Unknown format: %s' % format)

    def dump_csv(self, dump_file_obj, query):
        row_dicts = []
        for pkg in query:
            pkg_dict = pkg.as_dict()
            # flatten dict
            for name, value in pkg_dict.items()[:]:
                if isinstance(value, (list, tuple)):
                    if value and isinstance(value[0], dict) and name == 'resources':
                        for i, res in enumerate(value):
                            prefix = 'resource-%i' % i
                            pkg_dict[prefix + '-url'] = res['url']
                            pkg_dict[prefix + '-format'] = res['format']
                            pkg_dict[prefix + '-description'] = res['description']
                    else:
                        pkg_dict[name] = ' '.join(value)
                if isinstance(value, dict):
                    for name_, value_ in value.items():
                        pkg_dict[name_] = value_
                    del pkg_dict[name]
            row_dicts.append(pkg_dict)
        writer = CsvWriter(row_dicts)
        writer.save(dump_file_obj)

    def dump_json(self, dump_file_obj, query):
        pkgs = []
        for pkg in query:
            pkg_dict = pkg.as_dict()
            pkgs.append(pkg_dict)
        json.dump(pkgs, dump_file_obj, indent=4)

class Dumper(object):
    '''Dumps the database in same structure as it appears in the database'''
    model_classes = [
#        ckan.model.State,
        ckan.model.Revision,
        ckan.model.Package,
        ckan.model.Tag,
        ckan.model.PackageTag,
        ckan.model.PackageRevision,
        ckan.model.PackageTagRevision,
        ckan.model.Group,
        ckan.model.Member,
        ckan.model.PackageExtra,
        ]
    # TODO Bring this list of classes up to date. In the meantime,
    # disabling this functionality in cli.
    
    def get_table(self, model_class):
        table = orm.class_mapper(model_class).mapped_table
        return table

    def dump_json(self, dump_path, verbose=False, ):
        dump_struct = { 'version' : ckan.__version__ }

        if verbose:
            print "\n\nStarting...........................\n\n\n"

        for model_class in self.model_classes:
            table = self.get_table(model_class)
            model_class_name = model_class.__name__
            dump_struct[model_class_name] = {}
            if verbose:
                print model_class_name, '--------------------------------'
            q = table.select()
            for record in q.execute():
                if verbose:
                    print '--- ', 'id', record.id
                recorddict = self.cvt_record_to_dict(record, table)
                dump_struct[model_class_name][record.id] = recorddict
        if verbose:
            print '---------------------------------'
            print 'Dumping to %s' % dump_path
        json.dump(dump_struct, file(dump_path, 'w'), indent=4, sort_keys=True)

    def cvt_record_to_dict(self, record, table):
        out = {}
        for key in table.c.keys():
            val  = getattr(record, key)
            if isinstance(val, datetime.date):
                val = str(val)
            out[key] = val
            # print "--- ", modelAttrName, unicode(modelAttrValue).encode('ascii', 'ignore')
        return out

    def load_json(self, dump_path, verbose=False):
        dump_struct = json.load(open(dump_path))

        if verbose:
            print 'Building table...'
        # Protect against writing into created database.
        ckan.model.metadata.create_all()
        for model_class in self.model_classes:
            if model.Session.query(model_class).count():
                raise Exception, "Existing '%s' records in database" % model_class

        records = {}
        for model_class in self.model_classes:
            table = self.get_table(model_class)
            collection_objects = {}
            model_class_name = model_class.__name__
            records[model_class_name] = collection_objects
            if verbose:
                print model_class_name, '--------------------------------'
            collectionStruct = dump_struct[model_class_name]
            if verbose:
                print collectionStruct.keys()
            recordIds = collectionStruct.keys()
            recordIds.sort()
            for recordId in recordIds:
                record_struct = collectionStruct[recordId]
                record_struct = self.switch_names(record_struct)
                if verbose:
                    print record_struct
                q = table.insert(values=record_struct)
                result = q.execute()
        self.fix_sequences()
        if verbose:
            print 'OK'

    def switch_names(self, record_struct):
        '''Alter SQLObject and v0.6 names.

        Can be run safely on data post 0.6.
        '''
        out = {}
        for k,v in record_struct.items():
            # convert from v0.6 to v0.7
            k = k.replace('ID', '_id')
            if k == 'base_id':
                k = 'continuity_id'
            if k == 'log_message':
                k = 'message'
            # generic
            if v == 'None':
                v = None
            if '_id' in k and v is not None:
                v = int(v)
            out[k] = v
        return out

    def fix_sequences(self):
        for model_class in self.model_classes:
            if model_class == ckan.model.User: # ApiKey does not have idseq
                continue
            table = self.get_table(model_class)
            seqname = '%s_id_seq' % table.name 
            q = table.select()
            print model_class
            maxid = q.order_by(table.c.id.desc()).execute().fetchone().id
            print seqname, maxid+1
            sql = "SELECT setval('%s', %s);" % (seqname, maxid+1)
            engine = ckan.model.metadata.bind
            engine.execute(sql)

    def migrate_06_to_07(self):
        '''Fix up continuity objects and put names in revision objects.'''
        print 'Migrating 0.6 data to 0.7'
        pkg_table = self.get_table(ckan.model.Package)
        pkg_rev_table = self.get_table(ckan.model.PackageRevision)
        for record in pkg_table.select().execute():
            print 'Current:', record
            q = pkg_rev_table.select()
            q = q.where(pkg_rev_table.c.continuity_id==record.id)
            mostrecent = q.order_by(pkg_rev_table.c.revision_id.desc()).limit(1)
            pkg_rev_record = mostrecent.execute().fetchall()[0]
            print 'Object Revision:', pkg_rev_record
            newrecord = {}
            for k in [ 'download_url', 'license_id', 'notes', 'revision_id',
                    'state_id', 'title', 'url' ]:
                if k != 'id': 
                    newrecord[k] = getattr(pkg_rev_record, k)
            print 'New:', newrecord
            update = pkg_table.update(pkg_table.c.id==record.id, values=newrecord)
            update.execute()

            # now put names in package_revisions
            for rev in q.execute():
                update = pkg_rev_table.update(pkg_rev_table.c.id==rev.id,
                        values={'name': record.name})
                update.execute()

class CsvWriter:
    def __init__(self, package_dict_list=None):
        self._rows = []
        self._col_titles = []
        titles_set = set()
        for row_dict in package_dict_list:
            for key in row_dict.keys():
                if key not in self._col_titles:
                    self._col_titles.append(key)
        for row_dict in package_dict_list:
            self._add_row_dict(row_dict)
        
    def _add_row_dict(self, row_dict):
        row = []
        for title in self._col_titles:
            if row_dict.has_key(title):
                if isinstance(row_dict[title], int):
                    row.append(row_dict[title])
                elif isinstance(row_dict[title], unicode):
                    row.append(row_dict[title].encode('utf8'))
                else:
                    row.append(row_dict[title])
            else:
                row.append(None)
        self._rows.append(row)

    def save(self, file_obj):        
        writer = csv.writer(file_obj, quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(self._col_titles)
        for row in self._rows:
            writer.writerow(row)

class PackagesXlWriter:
    def __init__(self, package_dict_list=None):
        import xlwt
        self._workbook = xlwt.Workbook(encoding='utf8')
        self._sheet = self._workbook.add_sheet('test')
        self._col_titles = {} # title:col_index
        self._row = 1
        self.add_col_titles(['name', 'title'])
        if package_dict_list:
            for row_dict in package_dict_list:
                self.add_row_dict(row_dict)
                self._row += 1

    def add_row_dict(self, row_dict):
        for key, value in row_dict.items():
            if value is not None:
                if key not in self._col_titles.keys():
                    self._add_col_title(key)
                col_index = self._col_titles[key]
                self._sheet.write(self._row, col_index, value)

    def get_serialized(self):
        strm = StringIO.StringIO()
        self._workbook.save(strm)
        workbook_serialized = strm.getvalue()
        strm.close()
        return workbook_serialized

    def save(self, filepath):
        self._workbook.save(filepath)

    def add_col_titles(self, titles):
        # use initially to specify the order of column titles
        for title in titles:
            self._add_col_title(title)
                    
    def _add_col_title(self, title):
        if self._col_titles.has_key(title):
            return
        col_index = len(self._col_titles)
        self._sheet.write(0, col_index, title)
        self._col_titles[title] = col_index

    @staticmethod
    def pkg_to_xl_dict(pkg):
        '''Convert a Package object to a dictionary suitable for XL format'''
        dict_ = pkg.as_dict()

        for key, value in dict_.items():
            # Not interested in dumping IDs - for internal use only really
            if (key.endswith('_id') or key == 'id'
                or key.startswith('rating')):
                del dict_[key]
            if key=='resources':
                for i, res in enumerate(value):
                    prefix = 'resource-%i' % i
                    keys = model.Resource.get_columns()
                    keys += [key_ for key_ in pkg.resources[i].extras.keys() if key_ not in keys]
                    for field in keys:
                        dict_['%s-%s' % (prefix, field)] = res[field]
                del dict_[key]
            elif isinstance(value, (list, tuple)):
                dict_[key] = ' '.join(value)
            elif key=='extras':
                for key_, value_ in value.items():
                    dict_[key_] = value_
                del dict_[key]
        return dict_

class UserDumper(object):
    def dump(self, dump_file_obj):
        query = model.Session.query(model.User)
        query = query.order_by(model.User.created.asc())

        columns = (('id', 'name', 'openid', 'fullname', 'email', 'created', 'about'))
        row_dicts = []
        for user in query:
            row = OrderedDict()
            for col in columns:
                value = getattr(user, col)
                if not value:
                    value = ''
                if col == 'created':
                    value = str(value) # or maybe dd/mm/yyyy?
                row[col] = value
            row_dicts.append(row)

        writer = CsvWriter(row_dicts)
        writer.save(dump_file_obj)
        dump_file_obj.close()
