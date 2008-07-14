import sqlobject

try:
    # vdm >= 0.2
    import vdm.sqlobject.base as vdmbase
    from vdm.sqlobject.base import State
except:
    # vdm == 0.1
    import vdm.base as vdmbase
    from vdm.base import State

# American spelling ...
class License(sqlobject.SQLObject):

    class sqlmeta:
        _defaultOrder = 'name'

    name = sqlobject.UnicodeCol(alternateID=True)
    packages = sqlobject.MultipleJoin('Package')


class PackageRevision(vdmbase.ObjectRevisionSQLObject):

    base = sqlobject.ForeignKey('Package', cascade=True)
    title = sqlobject.UnicodeCol(default=None)
    url = sqlobject.UnicodeCol(default=None)
    download_url = sqlobject.UnicodeCol(default=None)
    license = sqlobject.ForeignKey('License', default=None)
    notes = sqlobject.UnicodeCol(default=None)


class TagRevision(vdmbase.ObjectRevisionSQLObject):

    base = sqlobject.ForeignKey('Tag', cascade=True)


class PackageTagRevision(vdmbase.ObjectRevisionSQLObject):

    base = sqlobject.ForeignKey('PackageTag', cascade=True)


class Package(vdmbase.VersionedDomainObject):

    sqlobj_version_class = PackageRevision
    versioned_attributes = vdmbase.get_attribute_names(sqlobj_version_class)
    
    name = sqlobject.UnicodeCol(alternateID=True)

    # should be attribute_name, module_name, module_object
    m2m = [ ('tags', 'ckan.models.package', 'Tag', 'PackageTag') ]

    def add_tag_by_name(self, tagname):
        if not tagname:
            return
        try:
            tag = self.revision.model.tags.get(tagname)
        except sqlobject.SQLObjectNotFound:
            tag = self.transaction.model.tags.create(name=tagname)
        self.tags.create(tag=tag)

    def drop_tag_by_name(self, tagname):
        tag = self.revision.model.tags.get(tagname)
        self.tags.delete(tag=tag)


class Tag(vdmbase.VersionedDomainObject):

    sqlobj_version_class = TagRevision

    class sqlmeta:
        defaultOrder = 'name'

    name = sqlobject.UnicodeCol(alternateID=True)
    versioned_attributes = vdmbase.get_attribute_names(sqlobj_version_class)


    m2m = [ ('packages', 'ckan.models.package', 'Package', 'PackageTag') ]

    @classmethod
    def search_by_name(self, text_query):
        text_query = str(text_query) # SQLObject chokes on unicode.
        return self.select(self.q.name.contains(text_query.lower()))


class PackageTag(vdmbase.VersionedDomainObject):

    sqlobj_version_class = PackageTagRevision
    versioned_attributes = vdmbase.get_attribute_names(sqlobj_version_class)
    m2m = []

    package = sqlobject.ForeignKey('Package', cascade=True)
    tag = sqlobject.ForeignKey('Tag', cascade=True)

    package_tag_index = sqlobject.DatabaseIndex('package', 'tag',
            unique=True)

