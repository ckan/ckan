import logging
from sqlobject import SQLObjectNotFound
import ckan.model as model

# Todo: Use ckan.forms here?

class RegisterPresenter(list):

    modelClass = None
    keyName = 'id'
    log = logging.getLogger(__name__)

    def __init__(self, entities):
        super(RegisterPresenter, self).__init__()
        self.entities = None
        entities_type = type(entities)
        if issubclass(entities_type, list):
            self.init_from_list(entities)
        else:
            msg = "Can't init presenter with '%s': %s" % (
                entities_type, entity)
            raise Exception, msg

    def init_from_list(self, entities):
        self.entities = entities
        for e in entities:
            if issubclass(type(e), self.modelClass):
                self.append(self.get_entity_key(e))
            else:
                msg = "Entity %s is not a %s." % (
                    e, self.modelClass)
                raise Exception, msg

    def get_entity_key(self, entity):
        return getattr(entity, self.keyName)


class EntityPresenter(dict):

    modelClass = None
    keyName = 'id'

    def __init__(self, entity, register=None, uncreated=False):
        self.register = register
        self.uncreated = uncreated
        entity_type = type(entity)
        self.entity = None
        if issubclass(entity_type, self.modelClass):
            self.init_from_model(entity)
        elif issubclass(entity_type, dict):
            self.init_from_request_data(entity)
        else:
            msg = "Can't init presenter with '%s': %s" % (
                entity_type, entity)
            raise Exception, msg

    def init_from_model(self, entity):
        self.entity = entity

    def init_from_request_data(self, kwds):
        pass

    def as_constructor_kwds(self):
        kwds = {}
        return kwds

    def as_entity(self):
        if self.entity != None:
            pass
        elif self.is_update():
            self.update_entity()
        else:
            self.construct_entity()
        return self.entity

    def is_update(self):
        return not self.uncreated

    def construct_entity(self):
        kwds = self.as_constructor_kwds()
        try:
            self.entity = self.register(**kwds)
            self.post_entity_create()
        except TypeError, inst:
            msg = "Couldn't create with kwds %s: %s" % (
                kwds, inst
            )
            raise TypeError(msg)

    def post_entity_create(self):
        pass

    def update_entity(self):
        entity_key = self[self.keyName]
        kwds = {self.keyName: entity_key}
        if self.register != None:
            self.entity = self.register.get(entity_key)
        else:
            self.entity = self.modelClass.selectBy(**kwds)


class PackageRegisterPresenter(RegisterPresenter):

    modelClass = model.Package
    keyName = 'name'


class TagRegisterPresenter(RegisterPresenter):

    modelClass = model.Tag
    keyName = 'name'


class PackagePresenter(EntityPresenter):

    modelClass = model.Package
    keyName = 'name'

    def init_from_model(self, entity):
        super(PackagePresenter, self).init_from_model(entity)
        self['name'] = self.entity.name
        self['title'] = self.entity.title
        self['url'] = self.entity.url
        self['download_url'] = self.entity.download_url
        self['notes'] = self.entity.notes
        self['tags'] = self.get_tag_names()

    def get_tag_names(self):
        tag_names = []
        for tag in self.entity.tags:
            if hasattr(tag, 'tag'):
                tag = tag.tag  # Sometimes we get a list of associations.
            tag_names.append(tag.name)
        return tag_names

    def init_from_request_data(self, kwds):
        super(PackagePresenter, self).init_from_request_data(kwds)
        if 'name' in kwds:
            self['name'] = kwds['name']
        if 'title' in kwds:
            self['title'] = kwds['title']
        if 'url' in kwds:
            self['url'] = kwds['url']
        if 'download_url' in kwds:
            self['download_url'] = kwds['download_url']
        if 'notes' in kwds:
            self['notes'] = kwds['notes']
        if 'tags' in kwds:
            self['tags'] = kwds['tags'][:]  # Copy tag names.
    
    def as_constructor_kwds(self):
        kwds = super(PackagePresenter, self).as_constructor_kwds()
        if 'name' in self:
            kwds['name'] = self['name']
        if 'title' in self:
            kwds['title'] = self['title']
        #if 'url' in self:
        #    kwds['url'] = self['url']
        #if 'download_url' in self:
        #    kwds['download_url'] = self['download_url']
        #if 'notes' in self:
        #    kwds['notes'] = self['notes']
        return kwds
    
    def post_entity_create(self):
        self.update_entity_tags()
        if 'name' in self:
            self.entity.name = self['name']
        if 'title' in self:
            self.entity.title = self['title']
        if 'url' in self:
            self.entity.url = self['url']
        if 'download_url' in self:
            self.entity.download_url = self['download_url']
        if 'notes' in self:
            self.entity.notes = self['notes']

    def update_entity_tags(self):
        # Todo: Remove old tag associations.

        if 'tags' in self:
            new_tags = self['tags']
            old_tags = self.get_tag_names()
            for tag_name in new_tags:
                if tag_name not in old_tags:
                    self.entity.add_tag_by_name(tag_name)
            for tag_name in old_tags:
                if tag_name not in new_tags:
                    self.entity.drop_tag_by_name(tag_name)


    def assert_schema_tag_name(self, tag_name):
        # Todo: Check tag_name with proper tag schema.
        pass

    def update_entity(self):
        super(PackagePresenter, self).update_entity()
        if self.entity:
            if 'name' in self:
                self.entity.name = self['name']
            if 'title' in self:
                self.entity.title = self['title']
            if 'url' in self:
                self.entity.url = self['url']
            if 'download_url' in self:
                self.entity.download_url = self['download_url']
            if 'notes' in self:
                self.entity.notes = self['notes']
            self.update_entity_tags()


class TagPresenter(EntityPresenter):

    modelClass = model.Tag
    keyName = 'name'

    def init_from_model(self, entity):
        super(TagPresenter, self).init_from_model(entity)
        self['name'] = entity.name

    def init_from_request_data(self, kwds):
        super(TagPresenter, self).init_from_request_data(kwds)
        self['name'] = kwds['name']

    def as_constructor_kwds(self):
        kwds = super(TagPresenter, self).as_constructor_kwds()
        kwds['name'] = self['name']
        return kwds

    def update_entity(self):
        super(TagPresenter, self).update_entity()
        if self.entity:
            self.entity.name = self['name']


