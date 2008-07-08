import logging

import ckan.model as model
import ckan.presentation as presentation
from ckan.forms import PackageSchema
from sqlobject import SQLObjectNotFound
from formencode import Invalid
from ckan.lib.base import c

# Todo: Fold formencode objects into validator (below, naive).

logger = logging.getLogger(__name__)

class PresentationMode(object):

    repo = model.repo

    moved_permanently = {}
    entity_presenter_classes = {
        'package': presentation.PackagePresenter,
        'tag': presentation.TagPresenter,
    }
    register_presenter_classes = {
        'package': presentation.PackageRegisterPresenter,
        'tag': presentation.TagRegisterPresenter,
    }
    presentation_schemas = {
        'package': PackageSchema,
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
    
    def create_entity(self, txn_author='', txn_log_message=''):
        kwds = self.request_data
        kwds = self.convert_unicode_kwds(kwds)
        txn = self.repo.begin_transaction()
        register = self.get_register(txn.model)
        Presenter = self.get_entity_presenter_class()
        keyName = self.get_entity_presenter_class().keyName
        kwds_create = {keyName: kwds[keyName]}
        entity = register.create(**kwds_create)
        if entity:
            presenter = Presenter(self.request_data, register=register)
            entity = presenter.as_entity()
            txn.author = txn_author
            txn.log_message = txn_log_message
            txn.commit()
        return entity

    def get_entity(self, amodel=None):
        register = self.get_register(amodel)
        id = self.get_entity_id()
        try:
            entity = register.get(id)
            if entity.state.name != 'active':
                return None 
            else:
                return entity
        except SQLObjectNotFound:
            return None
    
    def update_entity(self, txn_author='', txn_log_message=''):
        txn = self.repo.begin_transaction()
        #entity = self.get_entity(txn.model)
        #if entity:
        #    register = self.get_register(txn.model)
        #    Presenter = self.get_entity_presenter_class()
        #    presenter = Presenter(self.request_data, register=register)
        #    entity = presenter.as_entity()
        #    txn.commit()
        #return entity
        try:
            request_data = dict(self.request_data)
            schema = self.get_presentation_schema()
            pkg = schema.to_python(request_data, state=txn)
        except Invalid, inst:
            return False
        else:
            txn.author = txn_author
            txn.log_message = txn_log_message
            txn.commit()
            return True

    def delete_entity(self, txn_author='', txn_log_message=''):
        txn = self.repo.begin_transaction()
        try:
            entity = self.get_entity(txn.model)
            entity.delete()
            #entity.purge()
        except:
            pass  # Again, not good. --jb
        else:
            txn.author = txn_author
            txn.log_message = txn_log_message
            txn.commit()

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
    
    def convert_unicode_kwds(self, data):
        # Need string keywords, not the unicode from the JSON parser.
        copy = {}
        [copy.__setitem__(str(n),v) for (n,v) in data.items()]
        return copy
    
    def get_register(self, amodel=None):
        if amodel == None:
            amodel = model.repo.youngest_revision().model
        register_name = self.get_register_name()
        register = None
        if 'package' in register_name:
            register = amodel.packages
        elif 'tag' in register_name:
            register = amodel.tags
        return register

    def get_entity_presenter_class(self):
        return self.entity_presenter_classes[self.get_register_name()]

    def get_register_presenter_class(self):
        return self.register_presenter_classes[self.get_register_name()]

    def get_presentation_schema(self):
        return self.presentation_schemas[self.get_register_name()]

    def get_register_name(self):
        return self.registry_path.split('/')[1]

    def get_entity_id(self):
        return self.registry_path.split('/')[2]

    def is_moved_permanently(self):
        if self.moved_permanently.get(self.registry_path, False):
            return True
        return False

    def register_not_found(self):
        if not self.get_register():
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
        if self.register_not_found():
            self.response_code = 404
            self.response_data = None
        elif self.is_moved_permanently():
            self.response_code = 301
            self.response_data = None
        else:
            self.entities = self.get_entities()
            self.response_code = 200
            self.response_data = self.get_register_presenter()
        return self


class RegisterPost(PresentationMode):

    def execute(self):
        if self.register_not_found():
            self.response_code = 404
            self.response_data = None
        elif self.is_unauthorized():
            self.response_code = 401
            self.response_data = None
        elif self.is_bad_request():
            self.response_code = 400
            self.response_data = None
        else:
            try:
                author = c.rest_api_user
                log_message = "REST API: POST %s" % self.registry_path
                self.entity = self.create_entity(author, log_message)
            # NB: Catching DB errors is problematic. We can't just do:
            #     except IntegrityError:
            #     ...
            # http://osdir.com/ml/python.sqlobject/2005-08/msg00199.html
            except Exception, inst:
                if inst.__class__.__name__ == 'IntegrityError':
                    self.response_code = 409
                    self.response_data = None
                else:
                    raise
            else:
                self.response_code = 200
                self.response_data = self.get_entity_presenter()
        return self


class RegisterSearch(PresentationMode):

    def execute(self):
        if self.register_not_found():
            self.response_code = 404
            self.response_data = None
        elif self.is_moved_permanently():
            self.response_code = 301
            self.response_data = None
        else:
            self.entities = self.search_entities()
            self.response_code = 200
            self.response_data = self.get_register_presenter()
        return self


class EntityGet(PresentationMode):

    def execute(self):
        if self.register_not_found():
            self.response_code = 404
            self.response_data = None
        elif self.is_bad_request():
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
        if self.register_not_found():
            self.response_code = 404
            self.response_data = None
        elif self.is_moved_permanently():
            self.response_code = 301
            self.response_data = None
        elif self.is_bad_request():
            self.response_code = 400
            self.response_data = None
        elif not self.get_entity():
            self.response_code = 404
            self.response_data = None
        else:
            author = c.rest_api_user
            log_message = "REST API: PUT %s" % self.registry_path
            if self.update_entity(author, log_message):
                self.response_code = 200
                self.response_data = None
            else:
                self.response_code = 400
                self.response_data = None
        return self

    def is_bad_request(self):
        if 'name' in self.request_data:
            if self.get_entity_id() != self.request_data['name']:
                return True
        return False

class EntityDelete(PresentationMode):

    def execute(self):
        if self.register_not_found():
            self.response_code = 404
            self.response_data = None
        elif not self.get_entity():
            self.response_code = 404
            self.response_data = None
        else:
            author = c.rest_api_user
            log_message = "REST API: DELETE %s" % self.registry_path
            self.delete_entity(author, log_message)
            self.response_code = 200
            self.response_data = None
        return self


class Validator(object):

    def validate(self, data):
        return True


class PackagePostValidator(object):

    def validate(self, data):
        return data.has_key('title')

