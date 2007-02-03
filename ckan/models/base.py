class BaseRegistry(object):

    # domain object to which this registry relates
    registry_object = None
    # ditto but for the revison of the object 
    registry_object_revision = None

    def create(self, revision, **kwargs):
        base = self.registry_object(**kwargs)
        kwargs['base'] = base 
        kwargs['revision'] = revision
        rev = self.registry_object_revision(**kwargs)
        return rev



