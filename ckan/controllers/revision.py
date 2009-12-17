from ckan.lib.base import *

import ckan.authz
from datetime import datetime

class RevisionController(BaseController):

    def index(self):
        return self.list()

    def list(self):
        format = request.params.get('format', '')
        if format == 'atom':
            # Generate and return Atom 1.0 document.
            from webhelpers.feedgenerator import Atom1Feed
            feed = Atom1Feed(
                title=u'CKAN Package Revision History',
                link=h.url_for(controller='revision', action='list', id=''),
                description=u'Recent changes to the CKAN repository.',
                language=u'en',
            )
            select_results = model.repo.history().all()
            for revision in select_results:
                if not revision.id and revision.number:
                    continue
                try:
                    dayHorizon = int(request.params.get('days'))
                except:
                    dayHorizon = 30
                try:
                    dayAge = (datetime.now() - revision.timestamp).days
                except:
                    dayAge = 0
                if dayAge >= dayHorizon:
                    break
                pkgs = u'[%s]' % ' '.join([ p.name for p in revision.packages ])
                item_title = u'r%s ' % (revision.id)
                item_title += pkgs
                if revision.message:
                    item_title += ': %s' % (revision.message or '')
                item_link = h.url_for(action='read', id=revision.id)
                item_description = 'Packages affected: %s.\n' % pkgs
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
                        
            from ckan.lib.helpers import Page

            c.page = Page(
                collection=model.Revision.query(),
                page=request.params.get('page', 1),
                items_per_page=50
            )
            
            return render('revision/list')

    def read(self, id=None):
        if id is None:
            h.redirect_to(controller='revision', action='list')
        c.revision = model.Revision.query.get(id)
        if c.revision is None:
            abort(404)
        pkgs = model.PackageRevision.query.filter_by(revision=c.revision)
        c.packages = [ pkg.continuity for pkg in pkgs ]
        pkgtags = model.PackageTagRevision.query.filter_by(revision=c.revision)
        c.pkgtags = [ pkgtag.continuity for pkgtag in pkgtags ]
        return render('revision/read')

    def diff(self, id=None):
        if 'diff' not in request.params or 'oldid' not in request.params:
            abort(400)
        pkg = model.Package.by_name(id)
        c.revision_from = model.Revision.query.get(
            request.params.getone('oldid'))
        c.revision_to = model.Revision.query.get(
            request.params.getone('diff'))
        c.diff = pkg.diff(c.revision_to, c.revision_from)
        c.pkg = pkg
        return render('revision/diff')

    def _has_purge_permissions(self):
        authorizer = ckan.authz.Authorizer()
        action = model.Action.PURGE
        return ( c.user and authorizer.is_authorized(c.user, action,
            model.Revision) )

    def purge(self, id=None):
        if id is None:
            c.error = 'No revision id specified'
            return render('revision/purge')
        if not self._has_purge_permissions():
            c.error = 'You are not authorized to perform this action'
            return render('revision/purge')
        else:
            revision = model.Revision.query.get(id)
            try:
                model.repo.purge_revision(revision, leave_record=True)
            except Exception, inst:
                # is this a security risk?
                # probably not because only admins get to here
                c.error = 'Purge of revision failed: %s' % inst
            return render('revision/purge')

