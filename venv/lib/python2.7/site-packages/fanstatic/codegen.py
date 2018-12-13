def _visit(resource, result, dead):
    if dead[(resource.library, resource.relpath)]:
        return
    dead[(resource.library, resource.relpath)] = True
    for depend in resource.depends:
        _visit(depend, result, dead)
    for depend in resource.supersedes:
        _visit(depend, result, dead)
    result.append(resource)


def sort_resources_topological(resources):
    """Sort resources by dependency and supersedes.
    """
    dead = {}
    result = []
    for resource in resources:
        dead[(resource.library, resource.relpath)] = False

    for resource in resources:
        _visit(resource, result, dead)
    return result


def generate_code(**kw):
    resource_to_name = {}
    resources = []
    for name, resource in kw.items():
        resource_to_name[(resource.library, resource.relpath)] = name
        resources.append(resource)

    # libraries with the same name are the same libraries
    libraries = {}
    for resource in resources:
        libraries[resource.library.name] = resource.library
        for mode_name, mode_resource in resource.modes.items():
            libraries[mode_resource.library.name] = mode_resource.library
    libraries = sorted(libraries.values(), key=lambda library: library.name)

    result = []
    # import on top
    result.append("from fanstatic import Library, Resource")
    result.append("")
    result.append("# This code is auto-generated and not PEP8 compliant")
    result.append("")
    # define libraries
    for library in libraries:
        result.append("%s = Library('%s', '%s')" %
                      (library.name, library.name, library.rootpath))
    result.append("")

    # sort resources in the order we want them to be
    resources = sort_resources_topological(resources)

    # now generate resource code
    for resource in resources:
        s = "%s = Resource(%s, '%s'" % (
            resource_to_name[(resource.library, resource.relpath)],
            resource.library.name,
            resource.relpath)
        if resource.depends:
            depends_s = ', depends=[%s]' % ', '.join(
                [resource_to_name[(d.library, d.relpath)] for d in resource.depends])
            s += depends_s
        if resource.supersedes:
            supersedes_s = ', supersedes=[%s]' % ', '.join(
                [resource_to_name[(i.library, i.relpath)] for i in resource.supersedes])
            s += supersedes_s
        if resource.modes:
            items = []
            for mode_name, mode in resource.modes.items():
                items.append((mode_name,
                              generate_inline_resource(mode, resource)))
            items = sorted(items)
            modes_s = ', %s' % ', '.join(["%s=%s" % (name, mode) for
                                          (name, mode) in items])
            s += modes_s
        s += ')'
        result.append(s)
    return '\n'.join(result)


def generate_inline_resource(resource, associated_resource):
    if resource.library.name == associated_resource.library.name:
        return "'%s'" % resource.relpath
    else:
        return "Resource(%s, '%s')" % (resource.library.name,
                                       resource.relpath)
