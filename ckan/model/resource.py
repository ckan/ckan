from sqlalchemy.util import OrderedDict
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy import orm
from pylons import config
import vdm.sqlalchemy

from meta import *
from types import make_uuid, JsonDictType
from core import *
from package import *
from ckan.model import extension
from ckan.model.activity import ActivityDetail

__all__ = ['Resource', 'resource_table', 
           'ResourceGroup', 'resource_group_table',
           'ResourceRevision', 'resource_revision_table',
           'ResourceGroupRevision', 'resource_group_revision_table',
           ]

CORE_RESOURCE_COLUMNS = ['url', 'format', 'description', 'hash', 'name',
                         'resource_type', 'mimetype', 'mimetype_inner',
                         'size', 'last_modified', 'cache_url', 'cache_last_updated',
                         'webstore_url', 'webstore_last_updated']



##formally package_resource
resource_table = Table(
    'resource', metadata,
    Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
    Column('resource_group_id', types.UnicodeText, ForeignKey('resource_group.id')),
    Column('url', types.UnicodeText, nullable=False),
    Column('format', types.UnicodeText),
    Column('description', types.UnicodeText),
    Column('hash', types.UnicodeText),
    Column('position', types.Integer),

    Column('name', types.UnicodeText),
    Column('resource_type', types.UnicodeText),
    Column('mimetype', types.UnicodeText),
    Column('mimetype_inner', types.UnicodeText),
    Column('size', types.BigInteger),
    Column('last_modified', types.DateTime),
    Column('cache_url', types.UnicodeText),
    Column('cache_last_updated', types.DateTime),
    Column('webstore_url', types.UnicodeText),
    Column('webstore_last_updated', types.DateTime),
    
    Column('extras', JsonDictType),
    )

resource_group_table = Table(
    'resource_group', metadata,
    Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
    Column('package_id', types.UnicodeText, ForeignKey('package.id')),
    Column('label', types.UnicodeText),
    Column('sort_order', types.UnicodeText),
    Column('extras', JsonDictType),
    )

vdm.sqlalchemy.make_table_stateful(resource_table)
resource_revision_table = make_revisioned_table(resource_table)

vdm.sqlalchemy.make_table_stateful(resource_group_table)
resource_group_revision_table = make_revisioned_table(resource_group_table)

class Resource(vdm.sqlalchemy.RevisionedObjectMixin,
               vdm.sqlalchemy.StatefulObjectMixin,
               DomainObject):
    extra_columns = None
    def __init__(self, resource_group_id=None, url=u'', 
                 format=u'', description=u'', hash=u'',
                 extras=None,
                 **kwargs):
        self.id = make_uuid()
        if resource_group_id:
            self.resource_group_id = resource_group_id
        self.url = url
        self.format = format
        self.description = description
        self.hash = hash
        # The base columns historically defaulted to empty strings
        # not None (Null). This is why they are seperate here.
        base_columns = ['url', 'format', 'description', 'hash']
        for key in set(CORE_RESOURCE_COLUMNS) - set(base_columns):
            setattr(self, key, kwargs.pop(key, None))
        self.extras = extras or {}
        extra_columns = self.get_extra_columns()
        for field in extra_columns:
            value = kwargs.pop(field, None)
            if value is not None:
                setattr(self, field, value)
        if kwargs:
            raise TypeError('unexpected keywords %s' % kwargs)

    def as_dict(self, core_columns_only=False):
        _dict = OrderedDict()
        cols = self.get_columns()
        if not core_columns_only:
            cols = ['id', 'resource_group_id'] + cols + ['position']
        for col in cols:
            value = getattr(self, col)
            if isinstance(value, datetime.datetime):
                value = value.isoformat()
            _dict[col] = value
        for k, v in self.extras.items() if self.extras else []:
            _dict[k] = v
        if self.resource_group and not core_columns_only:
            _dict["package_id"] = self.resource_group.package_id
        return _dict

    @classmethod
    def get(cls, reference):
        '''Returns a resource object referenced by its name or id.'''
        query = Session.query(ResourceRevision).filter(ResourceRevision.id==reference)
        query = query.filter(and_(
            ResourceRevision.state == u'active', ResourceRevision.current == True
        ))
        resource = query.first()
        if resource == None:
            resource = cls.by_name(reference)            
        return resource
        
    @classmethod
    def get_columns(cls, extra_columns=True):
        '''Returns the core editable columns of the resource.'''
        if extra_columns:
            return CORE_RESOURCE_COLUMNS + cls.get_extra_columns()
        else:
            return CORE_RESOURCE_COLUMNS

    @classmethod
    def get_extra_columns(cls):
        if cls.extra_columns is None:
            cls.extra_columns = config.get('ckan.extra_resource_fields', '').split()
            for field in cls.extra_columns:
                setattr(cls, field, DictProxy(field, 'extras'))
        return cls.extra_columns

    def related_packages(self):
        return [self.resource_group.package]

    def activity_stream_detail(self, activity_id, activity_type):
        import ckan.model as model
        import ckan.lib.dictization

        # Handle 'deleted' resources.
        # When the user marks a resource as deleted this comes through here as
        # a 'changed' resource activity. We detect this and change it to a
        # 'deleted' activity.
        if activity_type == 'changed' and self.state == u'deleted':
            activity_type = 'deleted'

        res_dict = ckan.lib.dictization.table_dictize(self,
                context={'model':model})
        return ActivityDetail(activity_id, self.id, u"Resource", activity_type,
                {'resource': res_dict})

class ResourceGroup(vdm.sqlalchemy.RevisionedObjectMixin,
               vdm.sqlalchemy.StatefulObjectMixin,
               DomainObject):
    extra_columns = None
    def __init__(self, package_id=None, sort_order=u'', label=u'',
                 extras=None, **kwargs):
        if package_id:
            self.package_id = package_id
        self.sort_order = sort_order
        self.label = label
        self.extras = extras or {}

        extra_columns = self.get_extra_columns()
        for field in extra_columns:
            value = kwargs.pop(field, u'')
            setattr(self, field, value)
        if kwargs:
            raise TypeError('unexpected keywords %s' % kwargs)

    def as_dict(self, core_columns_only=False):
        _dict = OrderedDict()
        cols = self.get_columns()
        if not core_columns_only:
            cols = ['package_id', 'label', 'sort_order'] + cols
        for col in cols:
            _dict[col] = getattr(self, col)
        for k, v in self.extras.items() if self.extras else []:
            _dict[k] = v
        return _dict
        
    @classmethod
    def get_columns(cls, extra_columns=True):
        '''Returns the core editable columns of the resource.'''
        if extra_columns:
            return ['label', 'sort_order'] + cls.get_extra_columns()
        else:
            return ['label', 'sort_order']

    @classmethod
    def get_extra_columns(cls):
        if cls.extra_columns is None:
            cls.extra_columns = config.get('ckan.extra_resource_group_fields', '').split()
            for field in cls.extra_columns:
                setattr(cls, field, DictProxy(field, 'extras'))
        return cls.extra_columns
    

## Mappers

mapper(Resource, resource_table, properties={
    'resource_group':orm.relation(ResourceGroup,
        # all resources including deleted
        # formally package_resources_all
        backref=orm.backref('resources_all',
                            collection_class=ordering_list('position'),
                            cascade='all, delete',
                            order_by=resource_table.c.position,
                            ),
                       )
    },
    order_by=[resource_table.c.resource_group_id],
    extension=[vdm.sqlalchemy.Revisioner(resource_revision_table),
               extension.PluginMapperExtension(),
               ],
)


mapper(ResourceGroup, resource_group_table, properties={
    'package':orm.relation(Package,
        # all resources including deleted
        backref=orm.backref('resource_groups_all',
                            cascade='all, delete, delete-orphan',
                            order_by=resource_group_table.c.sort_order,
                            ),
                       )
    },
    order_by=[resource_group_table.c.package_id],
    extension=[vdm.sqlalchemy.Revisioner(resource_group_revision_table),
               extension.PluginMapperExtension(),
               ],
)

## VDM

vdm.sqlalchemy.modify_base_object_mapper(Resource, Revision, State)
ResourceRevision = vdm.sqlalchemy.create_object_version(
    mapper, Resource, resource_revision_table)
    
vdm.sqlalchemy.modify_base_object_mapper(ResourceGroup, Revision, State)
ResourceGroupRevision = vdm.sqlalchemy.create_object_version(
    mapper, ResourceGroup, resource_group_revision_table)

ResourceGroupRevision.related_packages = lambda self: [self.continuity.package]
ResourceRevision.related_packages = lambda self: [self.continuity.resouce_group.package]

import vdm.sqlalchemy.stateful
# TODO: move this into vdm
def add_stateful_m21(object_to_alter, m21_property_name,
        underlying_m21_attrname, identifier, **kwargs):
    from sqlalchemy.orm import object_session
    def _f(obj_to_delete):
        sess = object_session(obj_to_delete)
        if sess: # for tests at least must support obj not being sqlalchemy
            sess.expunge(obj_to_delete)

    active_list = vdm.sqlalchemy.stateful.DeferredProperty(
            underlying_m21_attrname,
            vdm.sqlalchemy.stateful.StatefulList,
            # these args are passed to StatefulList
            # identifier if url (could use id but have issue with None)
            identifier=identifier,
            unneeded_deleter=_f,
            base_modifier=lambda x: x.get_as_of()
            )
    setattr(object_to_alter, m21_property_name, active_list)

def resource_identifier(obj):
    return obj.id


add_stateful_m21(Package, 'resource_groups', 'resource_groups_all',
                 resource_identifier)
add_stateful_m21(ResourceGroup, 'resources', 'resources_all',
                 resource_identifier)



class DictProxy(object):

    def __init__(self, target_key, target_dict, data_type=unicode):
        self.target_key = target_key
        self.target_dict = target_dict
        self.data_type = data_type

    def __get__(self, obj, type):

        if not obj:
            return self

        proxied_dict = getattr(obj, self.target_dict)
        if proxied_dict:
            return proxied_dict.get(self.target_key)

    def __set__(self, obj, value):

        proxied_dict = getattr(obj, self.target_dict)
        if proxied_dict is None:
            proxied_dict = {}
            setattr(obj, self.target_dict, proxied_dict)

        proxied_dict[self.target_key] = self.data_type(value)

    def __delete__(self, obj):

        proxied_dict = getattr(obj, self.target_dict)
        proxied_dict.pop(self.target_key)


