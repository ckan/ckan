from pylons.i18n import get_lang

from ckan.lib.base import *
from ckan.lib.helpers import Page
import ckan.authz
from datetime import datetime, timedelta

class RevisionController(BaseController):

    def index(self):
        return self.list()

    def list(self):
        format = request.params.get('format', '')
        if format == 'atom':
            # Generate and return Atom 1.0 document.
            from webhelpers.feedgenerator import Atom1Feed
            feed = Atom1Feed(
                title=_(u'CKAN Repository Revision History'),
                link=h.url_for(controller='revision', action='list', id=''),
                description=_(u'Recent changes to the CKAN repository.'),
                language=unicode(get_lang()),
            )
            # TODO: make this configurable?
            # we do not want the system to fall over!
            maxresults = 200
            try:
                dayHorizon = int(request.params.get('days', 5))
            except:
                dayHorizon = 5
            ourtimedelta = timedelta(days=-dayHorizon)
            since_when = datetime.now() + ourtimedelta
            revision_query = model.repo.history()
            revision_query = revision_query.filter(
                    model.Revision.timestamp>=since_when).filter(
                    model.Revision.id!=None)
            revision_query = revision_query.limit(maxresults)
            for revision in revision_query:
                package_indications = []
                revision_changes = model.repo.list_changes(revision)
                package_resource_revisions = revision_changes[model.PackageResource]
                package_extra_revisions = revision_changes[model.PackageExtra]
                for package in revision.packages:
                    number = len(package.all_revisions)
                    package_revision = None
                    count = 0
                    for pr in package.all_revisions:
                        count += 1
                        if pr.revision.id == revision.id:
                            package_revision = pr
                            break
                    if package_revision and package_revision.state == model.State.DELETED:
                        transition = 'deleted'
                    elif package_revision and count == number:
                        transition = 'created'
                    else:
                        transition = 'updated'
                        for package_resource_revision in package_resource_revisions:
                            if package_resource_revision.package_id == package.id:
                                transition += ':resources'
                                break
                        for package_extra_revision in package_extra_revisions:
                            if package_extra_revision.package_id == package.id:
                                if package_extra_revision.key == 'date_updated':
                                    transition += ':date_updated'
                                    break
                    indication = "%s:%s" % (package.name, transition)
                    package_indications.append(indication)
                pkgs = u'[%s]' % ' '.join(package_indications)
                item_title = u'r%s ' % (revision.id)
                item_title += pkgs
                if revision.message:
                    item_title += ': %s' % (revision.message or '')
                item_link = h.url_for(action='read', id=revision.id)
                item_description = _('Packages affected: %s.\n') % pkgs
                item_description += '%s' % (revision.message or '')
                item_author_name = revision.author
                item_pubdate = revision.timestamp
                feed.add_item(
                    title=item_title,
                    link=item_link,
                    description=item_description,
                    author_name=item_author_name,
                    pubdate=item_pubdate,
                )
            feed.content_type = 'application/atom+xml'
            return feed.writeString('utf-8')
        else:
            c.show_purge_links = self._has_purge_permissions()
            query = model.Session.query(model.Revision)
            c.page = Page(
                collection=query,
                page=request.params.get('page', 1),
                items_per_page=20
            )
            return render('revision/list.html')

    def read(self, id=None):
        if id is None:
            h.redirect_to(controller='revision', action='list')
        
        cache_key = str(hash(id))
        etag_cache(cache_key)    
        
        c.revision = model.Session.query(model.Revision).get(id)
        if c.revision is None:
            abort(404)
        pkgs = model.Session.query(model.PackageRevision).filter_by(revision=c.revision)
        c.packages = [ pkg.continuity for pkg in pkgs ]
        pkgtags = model.Session.query(model.PackageTagRevision).filter_by(revision=c.revision)
        c.pkgtags = [ pkgtag.continuity for pkgtag in pkgtags ]
        return render('revision/read.html', cache_key=cache_key)

    def diff(self, id=None):
        if 'diff' not in request.params or 'oldid' not in request.params:
            abort(400)
        pkg = model.Package.by_name(id)
        c.revision_from = model.Session.query(model.Revision).get(
            request.params.getone('oldid'))
        c.revision_to = model.Session.query(model.Revision).get(
            request.params.getone('diff'))
        diff = pkg.diff(c.revision_to, c.revision_from)
        c.diff = diff.items()
        c.diff.sort()
        c.pkg = pkg
        return render('revision/diff.html')

    def _has_purge_permissions(self):
        authorizer = ckan.authz.Authorizer()
        action = model.Action.PURGE
        return ( c.user and authorizer.is_authorized(c.user, action,
            model.Revision) )

    def purge(self, id=None):
        if id is None:
            c.error = _('No revision id specified')
            return render('revision/purge.html')
        if not self._has_purge_permissions():
            c.error = _('You are not authorized to perform this action')
            return render('revision/purge.html')
        else:
            revision = model.Session.query(model.Revision).get(id)
            try:
                model.repo.purge_revision(revision, leave_record=True)
            except Exception, inst:
                # is this a security risk?
                # probably not because only admins get to here
                c.error = _('Purge of revision failed: %s') % inst
            return render('revision/purge.html')

