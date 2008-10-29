import datetime

import simplejson
from sqlalchemy import orm

import ckan.model
from ckan.model import Session

model_classes = [
    ckan.model.State,
    ckan.model.License,
    ckan.model.Revision,
    ckan.model.Package,
    ckan.model.Tag,
    ckan.model.PackageTag,
    ckan.model.PackageRevision,
    ckan.model.PackageTagRevision,
    ckan.model.ApiKey,
]

def get_table(model_class):
    table = orm.class_mapper(model_class).mapped_table
    return table

class Dumper(object):

    def dump(self, dump_path, verbose=False):
        dump_struct = { 'version' : ckan.__version__ }

        if verbose:
            print "\n\nStarting...........................\n\n\n"

        for model_class in  model_classes:
            table = get_table(model_class)
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
        simplejson.dump(dump_struct, file(dump_path, 'w'), indent=4, sort_keys=True)

    def cvt_record_to_dict(self, record, table):
        out = {}
        for key in table.c.keys():
            val  = getattr(record, key)
            if isinstance(val, datetime.date):
                val = str(val)
            out[key] = val
            # print "--- ", modelAttrName, unicode(modelAttrValue).encode('ascii', 'ignore')
        return out

    def load(self, dump_path, verbose=False):
        dump_struct = simplejson.load(open(dump_path))

        if verbose:
            print 'Building table...'
        # Protect against writing into created database.
        ckan.model.metadata.create_all()
        for model_class in model_classes:
            if model_class.query.count():
                raise Exception, "Existing '%s' records in database" % model_class

        records = {}
        for model_class in  model_classes:
            table = get_table(model_class)
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
        for model_class in model_classes:
            if model_class == ckan.model.ApiKey: # ApiKey does not have idseq
                continue
            table = get_table(model_class)
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
        pkg_table = get_table(ckan.model.Package)
        pkg_rev_table = get_table(ckan.model.PackageRevision)
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

