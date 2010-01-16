# Various fixes to CKAN DB
# Directions for use:
# Start a paster shell and then import and use

import ckan.model as model

# 2010-01-16: Corrections to broken package_tags in ckan.net (from long ago it
# seems)
# also package resource (revision id not set during migration!)
def fix_package_tags():
    # all package_tag_revision objects have a revision
    # 5 package_tag objects have either no package_id or no tag_id (and also absent
    # in package_tag_revisoin)

    # copy over revision_id from package_tag_revision into package
    # delete package_tag where pkgid/tagid is absent
    count = 0
    for pkgtag in model.Session.query(model.PackageTag).filter_by(revision_id=None):
        comparer = lambda x,y: x.revision.timestamp > y.revision.timestamp
        revs = sorted(pkgtag.all_revisions, cmp=comparer)
        mostrecent = revs[0]
        pkgtag.revision_id = mostrecent.revision_id
        count += 1
    print('Updated %s PackageTags' % count)
    model.Session.commit()
    
    count = 0
    # every one w/o a tag_id is also w/o package_id
    for pkgtagrev in model.Session.query(model.PackageTagRevision).filter_by(package_id=None):
        pkgtagrev.package_id = pkgtagrev.continuity.package_id
        pkgtagrev.tag_id = pkgtagrev.continuity.tag_id
        count += 1
    print('Updated %s PackageTagRevisions' % count)
    model.Session.commit()

    count = 0
    for pkgtag in model.Session.query(model.PackageTag).filter_by(package_id=None):
        pkgtag.purge()
        count += 1
    print('Deleted %s PackageTags' % count)
    model.Session.commit()

