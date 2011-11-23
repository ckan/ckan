from pylons.i18n import _, ungettext, N_, gettext

from ckan import model
import package

__all__ = ['get_package_dict', 'edit_package_dict', 'add_to_package_dict', 'strip_ids_from_package_dict', 'PackageDictFormatError']

class PackageDictFormatError(Exception):
    pass

def get_package_dict(pkg=None, blank=False, fs=None, user_editable_groups=None):
    '''
    Creates a package dictionary suitable for use with edit_package_dict and
    deserialization.
    @param pkg  Package this dict relates to. id is extracted to go into the
                key prefixes and the package data is used. If None, the dict
                is for a new package.
    @param blank  Whether or not you supply a package, this ensures that the
                  values of the resulting dict are blank.
    @param fs  Fieldset to use - sets the fields.
    Resulting dict has keys with a formalchemy prefix, and it should work
    binding it to a fs and syncing. But whereas formalchemy forms produce a
    param dicts with "package--extras-0-key":extra-key etc, this method creates
    a param dict with iterators in the values, so you get something like:
    "package--extras":{extra-key:extra-value} instead.
    '''
    indict = {}
    if fs is None:
        fs = package.get_standard_fieldset(
            is_admin=False, user_editable_groups=user_editable_groups)
    if pkg:
        fs = fs.bind(pkg)

    exclude = ('-id', '-package_tags', '-all_revisions', '-_extras', '-roles', '-ratings')

    for field in fs._fields.values():
        if not filter(lambda x: field.renderer.name.endswith(x), exclude):
            if blank:
                indict[field.renderer.name] = u''
            else:
                if field.renderer.value:
                    indict[field.renderer.name] = field.renderer.value
                else:
                    indict[field.renderer.name] = u''

                # some fields don't bind in this way, so do it manually
                if field.renderer.name.endswith('-extras'):
                    indict[field.renderer.name] = dict(pkg.extras) if pkg else {}
                if field.renderer.name.endswith('-tags'):
                    indict[field.renderer.name] = ','.join([tag.name for tag in pkg.tags]) if pkg else ''
                if field.renderer.name.endswith('-resources'):
                    indict[field.renderer.name] = [dict([(key, getattr(res, key)) for key in model.Resource.get_columns()]) for res in pkg.resources] if pkg else []
        
    return indict

# Todo: Rename to indicate prefixing normal attribute names for fieldset.
def edit_package_dict(dict_, changed_items, id=''):
    '''
    Edits package dictionary obtained by "get_package_dict" ready for
    deserializing.
    
    @param dict_ Package dict to be edited
    @param changed_items Package dict with the changes to be made
           (keys do not need the "Package-<id>-" prefix)
    @return Edited dict
    '''
    prefix = 'Package-%s-' % id
    extras_key = prefix + 'extras'
    tags_key = prefix + 'tags'
    resources_key = prefix + 'resources'
    download_url_key = prefix + 'download_url'
    license_key = prefix + 'license'
    license_id_key = prefix + 'license_id'
    for key, value in changed_items.items():
        if key:
            if not key.startswith(prefix):
                key = prefix + key
            if dict_.has_key(key):
                if key == extras_key and isinstance(value, dict):
                    extras = dict_[extras_key]
                    for e_key, e_value in value.items():
                        if e_value == None:
                            if extras.has_key(e_key):
                                del extras[e_key]
                            #else:
                            #    print 'Ignoring deletion - incorrect key'
                        else:
                            extras[e_key] = e_value
                elif key == resources_key and isinstance(value, list):
                    # REST edit
                    resources = []
                    for res_dict in value:
                        res_dict_str = {}
                        if not isinstance(res_dict, dict):
                            raise PackageDictFormatError(_('Resource should be a dictionary: %r') % res_dict)
                        for key, value in res_dict.items():
                            res_dict_str[str(key)] = value
                        resources.append(res_dict_str)
                    dict_[resources_key] = resources
                elif key == tags_key and isinstance(value, list):
                    dict_[key] = ','.join(value)
                else:
                    dict_[key] = value
            elif key == download_url_key:
                dict_[resources_key].insert(0, {'url':value})
                # blank format, description and hash
            elif key == license_id_key:
                dict_[license_id_key] = unicode(value)
            elif key == license_key:
                dict_[license_id_key] = unicode(value)
            else:
                raise PackageDictFormatError(_('Key unknown: %s') % key)
        else:
            raise PackageDictFormatError(_('Key blank'))
    return dict_

def add_to_package_dict(dict_, changed_items, id=''):
    '''
    Takes a package dictionary (usually with all fields, but blank content)
    and adds the changed_items dictionary.
    '''
    prefix = 'Package-%s-' % id
    for key, value in changed_items.items():
        if key:
            if not key.startswith(prefix):
                key = prefix + key
            dict_[key] = value
    return dict_

def strip_ids_from_package_dict(dict_, id):
    '''
    Takes a package dictionary with field prefix Package-<id>-
    and makes it Package--
    '''
    new_dict = {}
    prefix = 'Package-%s-' % id
    for key, value in dict_.items():
        new_key = key.replace(prefix, 'Package--')
        new_dict[new_key] = value
    return new_dict
