import sqlobject

import vdm.base

# American spelling ...
class License(sqlobject.SQLObject):

    class sqlmeta:
        _defaultOrder = 'name'

    name = sqlobject.UnicodeCol(alternateID=True)

    packages = sqlobject.RelatedJoin('Package',
            createRelatedTable=False,
            intermediateTable='package_license'
            )


class PackageRevision(vdm.base.ObjectRevisionSQLObject):

    base = sqlobject.ForeignKey('Package', cascade=True)
    title = sqlobject.UnicodeCol(default=None)
    url = sqlobject.UnicodeCol(default=None)
    download_url = sqlobject.UnicodeCol(default=None)
    license = sqlobject.ForeignKey('License', default=None)
    notes = sqlobject.UnicodeCol(default=None)


class TagRevision(vdm.base.ObjectRevisionSQLObject):

    base = sqlobject.ForeignKey('Tag', cascade=True)


class PackageTagRevision(vdm.base.ObjectRevisionSQLObject):

    base = sqlobject.ForeignKey('PackageTag', cascade=True)


class Package(vdm.base.VersionedDomainObject):

    sqlobj_version_class = PackageRevision
    versioned_attributes = vdm.base.get_attribute_names(sqlobj_version_class)
    
    name = sqlobject.UnicodeCol(alternateID=True)

    # should be attribute_name, module_name, module_object
    m2m = [ ('tags', 'ckan.models.package', 'Tag', 'PackageTag') ]

    def add_tag_by_name(self, tagname):
        try:
            tag = self.revision.model.tags.get(tagname)
        except: # TODO: make this specific
            tag = self.transaction.model.tags.create(name=tagname)
        self.tags.create(tag=tag)


class Tag(vdm.base.VersionedDomainObject):

    sqlobj_version_class = TagRevision

    name = sqlobject.UnicodeCol(alternateID=True)
    versioned_attributes = vdm.base.get_attribute_names(sqlobj_version_class)

    m2m = [ ('packages', 'ckan.models.package', 'Package', 'PackageTag') ]

    @classmethod
    def search_by_name(self, search_string):
        # sqlobject specific
        term = '%' + search_string + '%'
        query = '''UPPER(tag.name) LIKE UPPER('%s')''' % term
        return self.select(query)


class PackageTag(vdm.base.VersionedDomainObject):

    sqlobj_version_class = PackageTagRevision
    versioned_attributes = vdm.base.get_attribute_names(sqlobj_version_class)
    m2m = []

    package = sqlobject.ForeignKey('Package', cascade=True)
    tag = sqlobject.ForeignKey('Tag', cascade=True)

    package_tag_index = sqlobject.DatabaseIndex('package', 'tag',
            unique=True)

