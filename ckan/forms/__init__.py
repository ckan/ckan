import formencode.sqlschema

import ckan.models

class PackageSchema(formencode.sqlschema.SQLSchema):
    wrap = ckan.models.Package
    allow_extra_fields = True
    # setting filter_extra_fields seems to mean from_python no longer works
    # filter_extra_fields = True

    def _convert_tags(self, obj):
        tagnames = [ tag.name for tag in obj.tags ]
        return ' '.join(tagnames)


    def get_current(self, obj, state):
        # single super is a mess, see:
        # http://groups.google.co.uk/group/comp.lang.python/browse_thread/thread/6d94ebc1016b7ddb/34684c138cf9f3%2334684c138cf9f3 
        # not sure why it is in the example code ...
        # value = super(PackageSchema).get_current(obj, state)
        value = formencode.sqlschema.SQLSchema.get_current(self, obj, state)
        tags_as_string = self._convert_tags(obj)
        value['tags'] = tags_as_string
        return value

    def update_object(self, columns, extra, state):
        tags = extra.pop('tags')
        outobj = super(PackageSchema, self).update_object(
            columns, extra, state)
        taglist = tags.split(' ')
        for tag in taglist:
            outobj.add_tag_by_name(tag)
        return outobj

