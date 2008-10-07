import ckan.model
import simplejson
from ckan.model import Session
from sqlalchemy import orm

model_classes = [
    ckan.model.State,
    ckan.model.License,
    ckan.model.Revision,
    ckan.model.Package,
    ckan.model.Tag,
    ckan.model.PackageTag,
    ckan.model.PackageRevision,
    ckan.model.PackageTagRevision
]

def get_table(model_class):
    table = orm.class_mapper(model_class).mapped_table
    return table

def load_from_dump(dump_path):
    dumpStruct = simplejson.load(open(dump_path))

    print 'Building table...'
    # Protect against writing into created database.
    ckan.model.metadata.create_all()
    for model_class in model_classes:
        if model_class.query.count():
            raise Exception, "Existing '%s' records in database" % model_class

    records = {}
    for model_class in  model_classes:
        table = get_table(model_class)
        collectionObjects = {}
        model_className = model_class.__name__
        records[model_className] = collectionObjects
        print model_className, '--------------------------------'
        collectionStruct = dumpStruct[model_className]
        print collectionStruct.keys()
        recordIds = collectionStruct.keys()
        recordIds.sort()
        for recordId in recordIds:
            recordStruct = collectionStruct[recordId]
            recordStruct = switch_names(recordStruct)
            print recordStruct
            q = table.insert(values=recordStruct)
            result = q.execute()
    fix_up_continuity()
    fix_sequences()
    print 'OK'

def switch_names(record_struct):
    out = {}
    for k,v in record_struct.items():
        k = k.replace('ID', '_id')
        if k == 'base_id':
            k = 'continuity_id'
        if k == 'log_message':
            k = 'message'
        if v == 'None':
            v = None
        if '_id' in k and v is not None:
            v = int(v)
        out[k] = v
    return out

def fix_sequences():
    for model_class in model_classes:
        table = get_table(model_class)
        seqname = '%s_id_seq' % table.name 
        q = table.select()
        maxid = q.order_by(table.c.id.desc()).execute().fetchone().id
        print seqname, maxid+1
        sql = "SELECT setval('%s', %s);" % (seqname, maxid+1)
        engine = ckan.model.metadata.bind
        engine.execute(sql)


def fix_up_continuity():
    pkg_table = get_table(ckan.model.Package)
    pkg_rev_table = get_table(ckan.model.PackageRevision)
    for record in pkg_table.select().execute():
        print 'Current:', record
        q = pkg_rev_table.select()
        q = q.where(pkg_rev_table.c.continuity_id==record.id)
        q = q.order_by(pkg_rev_table.c.revision_id.desc()).limit(1)
        pkg_rev_record = q.execute().fetchall()[0]
        print 'Object Revision:', pkg_rev_record
        newrecord = {}
        for k in [ 'download_url', 'license_id', 'notes', 'revision_id',
                'state_id', 'title', 'url' ]:
            if k != 'id': 
                newrecord[k] = getattr(pkg_rev_record, k)
        print 'New:', newrecord
        update = pkg_table.update(pkg_table.c.id==record.id, values=newrecord)
        update.execute()

