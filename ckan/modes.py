import logging

import ckan.model as model
import ckan.presentation as presentation

# This module implements the following presentation modes:
#
# Resource     Method      Format      Status Codes
# Register     GET     Register Format     200, 301
# Register     POST    Entity Format  200, 400, 401
# Entity     GET     Entity Format  200, 301, 400, 404
# Entity     PUT     Entity Format  200, 301, 400, 404
# Entity     DELETE  N/A     200, 204
#

# Todo: Fold formencode objects into validator (below, naive).
# Todo: Resolve fact that only Register POST mode can be unauthorized!

logger = logging.getLogger(__name__)

class PresentationMode(object):

    moved_permanently = {}
    # Todo: Generalise static 'register' lookup table.
    registers = {
        'package': model.repo.youngest_revision().model.packages,
        'tag': model.repo.youngest_revision().model.tags,
    }
    entity_presenter_classes = {
        'package': presentation.PackagePresenter,
        'tag': presentation.TagPresenter,
    }
    register_presenter_classes = {
        'package': presentation.PackageRegisterPresenter,
        'tag': presentation.TagRegisterPresenter,
    }

    def __init__(self, registry_path, request_data=None,
            validator=None, moved_permanently=None):
        self.registry_path = registry_path
        self.request_data = request_data
        self.validator = validator
        if moved_permanently != None:
            self.moved_permanently = moved_permanently

    def execute(self):
        raise Exception, "No execute method for mode %s." % type(self)

    def get_entities(self):
        register = self.get_register()
        entities = register.list()
        return entities
    
    def search_entities(self):
        '''Search for entities matching specified criteria.

        Supports a JSON-oriented dictionary based message format:

        {
            key : value,
            ...
        }

        Conditions are ANDed together. Use '%' for like support. For example
        the following query will select items which have BOTH a title LIKE %2
        AND a description like %abc.
        
        { "title" : "%2", description : "%abc" }

        Selecting by collection membership is supported. E.g. to get all
        packages which contain tag 1 do:

        {
            'tags' : [1],
        }

        To do a general text search:

        {
            'text-search' : 'term'
        }
        
        TODO: other query options such as limit (limiting number of
        results), 'OR's etc.
        '''
        register = self.get_register()
        kwds = self.request_data
        if kwds is None or len(kwds) == 0:
            return []
        kwds = self.convert_unicode_kwds(kwds)
        query = register.query
        for k, v in kwds.items():
            if k == 'text-search':
                query = register.text_search(query, v)
            elif isinstance(v, list): # an association test
                # depending on how it was set up join made be on e.g.
                # tags or package_tags
                singular = k[:-1]
                target_object = getattr(model, singular.capitalize())
                try:
                    query = query.join(k)
                except:
                    # its package_tags
                    attr_name = self.get_register_name() + '_' + k
                    query = query.join(attr_name)
                # at present cannot do more than 1 item
                # want to do:
                # select package where package_2_tag contains
                # package, tag1 and package, tag2 and ...
                # however with simple join do
                # select package.id from package join package_2_tag where
                # tag.id = id1 and tag.id = id2
                # this obviously always give zero results
                if len(v) > 1:
                    msg = 'Filtering by more than 2 items is not supported'
                    raise NotImplementedError(msg)
                for entity_id in v:
                    query = query.filter(target_object.id == entity_id)
            else:
                model_attr = getattr(register, k)
                query = query.filter(model_attr.like(v))
        logger.debug(query)
        return query.all()
    
    def create_entity(self):
        register = self.get_register()
        kwds = self.request_data
        kwds = self.convert_unicode_kwds(kwds)
        entity = register(**kwds)
        model.Session.flush()
        return entity

    def get_entity(self):
        register = self.get_register()
        id = self.get_entity_id()
        entity = register.get(id)
        return entity
    
    def update_entity(self):
        self.request_data['id'] = self.get_entity_id()
        Presenter = self.get_entity_presenter_class()
        presenter = Presenter(self.request_data)
        return presenter.as_entity()

    def delete_entity(self):
        entity = self.get_entity()
        if entity:
            model.Session.delete(entity)
            model.Session.flush()
            return True
        return False

    def convert_unicode_kwds(self, data):
        # Need string keywords, not the unicode from the JSON parser.
        copy = {}
        [copy.__setitem__(str(n),v) for (n,v) in data.items()]
        return copy
    
    def get_register(self):
        return self.registers[self.get_register_name()]

    def get_entity_presenter_class(self):
        return self.entity_presenter_classes[self.get_register_name()]

    def get_register_presenter_class(self):
        return self.register_presenter_classes[self.get_register_name()]

    def get_register_name(self):
        return self.registry_path.split('/')[1]

    def get_entity_id(self):
        return self.registry_path.split('/')[2]

    def is_moved_permanently(self):
        if self.moved_permanently.get(self.registry_path, False):
            return True
        return False

    def is_unauthorized(self):
        if self.moved_permanently.get(self.registry_path, False):
            return True
        return False

    def is_bad_request(self):
        if not self.validator:
            return False
        return not self.validator.validate(self.request_data)

    def get_entity_presenter(self):
        Presenter = self.get_entity_presenter_class()
        presenter = Presenter(self.entity)
        return presenter

    def get_register_presenter(self):
        Presenter = self.get_register_presenter_class()
        presenter = Presenter(self.entities)
        return presenter


class RegisterGet(PresentationMode):

    def execute(self):
        if self.is_moved_permanently():
            self.response_code = 301
            self.response_data = None
        else:
            self.entities = self.get_entities()
            self.response_code = 200
            self.response_data = self.get_register_presenter()
        return self


class RegisterPost(PresentationMode):

    def execute(self):
        if self.is_unauthorized():
            self.response_code = 401
            self.response_data = None
        elif self.is_bad_request():
            self.response_code = 400
            self.response_data = None
        else:
            self.entity = self.create_entity()
            self.response_code = 200
            self.response_data = self.get_entity_presenter()
        return self


class RegisterSearch(PresentationMode):

    def execute(self):
        if self.is_moved_permanently():
            self.response_code = 301
            self.response_data = None
        else:
            self.entities = self.search_entities()
            self.response_code = 200
            self.response_data = self.get_register_presenter()
        return self


class EntityGet(PresentationMode):

    def execute(self):
        if self.is_bad_request():
            self.response_code = 400
            self.response_data = None
        elif self.is_moved_permanently():
            self.response_code = 301
            self.response_data = None
        else:
            self.entity = self.get_entity()
            if self.entity:
                self.response_code = 200
                self.response_data = self.get_entity_presenter()
            else:
                self.response_code = 404
                self.response_data = None
        return self

    def is_bad_request(self):
        return False


class EntityPut(PresentationMode):

    def execute(self):
        if self.is_bad_request():
            self.response_code = 400
            self.response_data = None
        elif self.is_moved_permanently():
            self.response_code = 301
            self.response_data = None
        else:
            self.entity = self.update_entity()
            if self.entity:
                self.response_code = 200
                self.response_data = self.get_entity_presenter()
            else:
                self.response_code = 404
                self.response_data = None
        return self

    def is_bad_request(self):
        return False


class EntityDelete(PresentationMode):

    def execute(self):
        if self.delete_entity():
            self.response_code = 200
            self.response_data = None
        else:
            self.response_code = 204
            self.response_data = None
        return self


class Validator(object):

    def validate(self, data):
        return True


class PackagePostValidator(object):

    def validate(self, data):
        return data.has_key('title')

