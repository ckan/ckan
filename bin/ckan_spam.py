# purge revisions associated with a specific package name and after a certain
# revision number

# path to config file
cfg_path = 'INSERT YOUR PATH'
# name of pkg to examine
pkg_name = 'mis-uiowa'
# revision id to start at
# all revisions above this associated with pkg will be purged
start_at_id = 472

# holder for author blacklist
authors = {}

import os

import sqlobject

import loadconfig
path = os.path.abspath(cfg_path)
loadconfig.load_config(path)

import ckan.models as model

import ckan.commands.revision
def purge(revision):
    author = revision.author
    authors[author] = authors.get(author, 0) + 1
    cmd = ckan.commands.revision.PurgeRevision(
            revision=revision,
            leave_record=False)
    print 'Purging revision: %s' % revision.id
    cmd.execute()

def purge_packages_by_name():
    pkg = model.Package.byName(pkg_name)
    # for efficiency reasons best to have revisions in descending order
    sel = model.PackageRevision.select(
            sqlobject.AND(model.PackageRevision.q.baseID==pkg.id,
                model.PackageRevision.q.revisionID>=start_at_id),
            orderBy=-model.PackageRevision.q.revisionID,
            )
    print 'Total number of spam revisions:', sel.count()
    for item in sel:
        # testing
        # if item.revisionID > 700 and item.revisionID < 720:
        #     print item.revisionID
        # if item.revisionID < 1000:
        #    break
        purge(item.revision)

def purge_revisions_by_id(id_list):
    for id in id_list:
        rev = model.Revision.get(id)
        purge(rev)

# purge_revisions_by_id([514, 515, 516, 462, 469, 1867, 1866, 1833, 795])

print 'Blacklisted IPs:', authors.keys()
print 'Distribution of Spam by IP:', authors
