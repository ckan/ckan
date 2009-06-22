from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController

import ckan.authz
from datetime import datetime

class RevisionController(CkanBaseController):

    def index(self):
        return self.list()

    def list(self, id=0):
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
                item_title = 'r%s' % (revision.id)
                if revision.message:
                    item_title += ': %s' % (revision.message or '')

                item_link = h.url_for(action='read', id=revision.id)
                # Todo: More interesting description (actual pkg/tag changes?).
                item_description = '%s' % (revision.author or 'no author')
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
            return self._paginate_list('revision', id, 'revision/list')

    def read(self, id=None):
        if id is None:
            h.redirect_to(controller='revision', action='list')
        id = int(id)
        c.revision = model.Revision.query.get(id)
        if c.revision is None:
            abort(404)
        pkgs = model.PackageRevision.query.filter_by(revision=c.revision)
        c.packages = [ pkg.continuity for pkg in pkgs ]
        pkgtags = model.PackageTagRevision.query.filter_by(revision=c.revision)
        c.pkgtags = [ pkgtag.continuity for pkgtag in pkgtags ]
        return render('revision/read')

    def _has_purge_permissions(self):
        authorizer = ckan.authz.Authorizer()
        action = ckan.authz.actions['revision-purge']
        return ( c.user and authorizer.is_authorized(c.user, action) )

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

