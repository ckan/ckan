# encoding: utf-8

from datetime import datetime, timedelta

from pylons.i18n import get_lang
from six import text_type

import ckan.logic as logic
import ckan.lib.base as base
import ckan.model as model
import ckan.lib.helpers as h

from ckan.common import _, c, request


class RevisionController(base.BaseController):

    def __before__(self, action, **env):
        base.BaseController.__before__(self, action, **env)

        context = {'model': model, 'user': c.user,
                   'auth_user_obj': c.userobj}
        if c.user:
            try:
                logic.check_access('revision_change_state', context)
                c.revision_change_state_allowed = True
            except logic.NotAuthorized:
                c.revision_change_state_allowed = False
        else:
            c.revision_change_state_allowed = False
        try:
            logic.check_access('site_read', context)
        except logic.NotAuthorized:
            base.abort(403, _('Not authorized to see this page'))

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
                language=text_type(get_lang()),
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
                model.Revision.timestamp >= since_when).filter(
                    model.Revision.id != None)
            revision_query = revision_query.limit(maxresults)
            for revision in revision_query:
                package_indications = []
                revision_changes = model.repo.list_changes(revision)
                resource_revisions = revision_changes[model.Resource]
                package_extra_revisions = revision_changes[model.PackageExtra]
                for package in revision.packages:
                    if not package:
                        # package is None sometimes - I don't know why,
                        # but in the meantime while that is fixed,
                        # avoid an exception here
                        continue
                    if package.private:
                        continue
                    number = len(package.all_revisions)
                    package_revision = None
                    count = 0
                    for pr in package.all_revisions:
                        count += 1
                        if pr.revision.id == revision.id:
                            package_revision = pr
                            break
                    if package_revision and package_revision.state == \
                            model.State.DELETED:
                        transition = 'deleted'
                    elif package_revision and count == number:
                        transition = 'created'
                    else:
                        transition = 'updated'
                        for resource_revision in resource_revisions:
                            if resource_revision.package_id == package.id:
                                transition += ':resources'
                                break
                        for package_extra_revision in package_extra_revisions:
                            if package_extra_revision.package_id == \
                                    package.id:
                                if package_extra_revision.key == \
                                        'date_updated':
                                    transition += ':date_updated'
                                    break
                    indication = "%s:%s" % (package.name, transition)
                    package_indications.append(indication)
                pkgs = u'[%s]' % ' '.join(package_indications)
                item_title = u'r%s ' % (revision.id)
                item_title += pkgs
                if revision.message:
                    item_title += ': %s' % (revision.message or '')
                item_link = h.url_for(controller='revision', action='read', id=revision.id)
                item_description = _('Datasets affected: %s.\n') % pkgs
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
            query = model.Session.query(model.Revision)
            revs = query.limit(20).all()
            filtered_revs = []
            for rev in list(revs):
                private_rev = False
                for pkg in rev.packages:
                    if pkg.private:
                        private_rev = True
                        break
                if not private_rev:
                    filtered_revs.append(rev)

            c.page = h.Page(
                collection=filtered_revs,
                page=h.get_page_number(request.params),
                url=h.pager_url,
                items_per_page=20
            )
            return base.render('revision/list.html')

    def read(self, id=None):
        if id is None:
            base.abort(404)
        c.revision = model.Session.query(model.Revision).get(id)
        if c.revision is None:
            base.abort(404)

        pkgs = model.Session.query(model.PackageRevision).\
            filter_by(revision=c.revision)

        context = {'model': model, 'user': c.user}
        for pkg in c.revision.packages:
            try:
                logic.check_access('package_show', context, {'id': pkg.id})
            except logic.NotAuthorized:
                base.abort(403, _('Not authorized to see this page'))

        c.packages = [pkg.continuity for pkg in pkgs if not pkg.private]
        pkgtags = model.Session.query(model.PackageTagRevision).\
            filter_by(revision=c.revision)
        c.pkgtags = [pkgtag.continuity for pkgtag in pkgtags
                     if not pkgtag.package.private]
        grps = model.Session.query(model.GroupRevision).\
            filter_by(revision=c.revision)
        c.groups = [grp.continuity for grp in grps]
        return base.render('revision/read.html')

    def diff(self, id=None):

        if 'diff' not in request.params or 'oldid' not in request.params:
            base.abort(400)
        c.revision_from = model.Session.query(model.Revision).get(
            request.params.getone('oldid'))
        c.revision_to = model.Session.query(model.Revision).get(
            request.params.getone('diff'))

        c.diff_entity = request.params.get('diff_entity')
        if c.diff_entity == 'package':
            c.pkg = model.Package.by_name(id)

            context = {'model': model, 'user': c.user}
            try:
                logic.check_access('package_show', context, {'id': c.pkg.id})
            except logic.NotAuthorized:
                base.abort(403, _('Not authorized to see this page'))

            diff = c.pkg.diff(c.revision_to, c.revision_from)
        elif c.diff_entity == 'group':
            c.group = model.Group.by_name(id)
            diff = c.group.diff(c.revision_to, c.revision_from)
        else:
            base.abort(400)

        c.diff = diff.items()
        c.diff.sort()
        return base.render('revision/diff.html')

    def edit(self, id=None):
        if id is None:
            base.abort(404)
        revision = model.Session.query(model.Revision).get(id)
        if revision is None:
            base.abort(404)
        action = request.params.get('action', '')
        if action in ['delete', 'undelete']:
            # this should be at a lower level (e.g. logic layer)
            if not c.revision_change_state_allowed:
                base.abort(403)
            if action == 'delete':
                revision.state = model.State.DELETED
            elif action == 'undelete':
                revision.state = model.State.ACTIVE
            model.Session.commit()
            h.flash_success(_('Revision updated'))
            h.redirect_to(
                h.url_for(controller='revision', action='read', id=id))
