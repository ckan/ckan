import genshi
from sqlalchemy import orm
import ckan.lib.helpers as h
from ckan.lib.base import *
import ckan.rating
from pylons import g
from ckan.lib.dictization import table_dictize

# Todo: Factor out unused original_name argument.

class PackageSaver(object):
    '''Use this to validate, preview and save packages to the db.
    @param log_message: optional - only supply this if you want it validated
    @param author: optional - only supply this if you want it validated
    '''
    @classmethod
    def render_preview(cls, fs, log_message=None, author=None, client=None):
        '''Renders a package on the basis of a fieldset - perfect for
        preview of form data.
        Note that the actual calling of render('package/read') is left
        to the caller.'''
        pkg = cls._preview_pkg(fs, log_message, author, client=client)

        pkg_dict = table_dictize(pkg, {'model': model})
        pkg_dict['extras'] = []
        c.pkg = pkg
        for key, value in pkg.extras.iteritems():
            pkg_dict['extras'].append(dict(key=key, value=value))

        cls.render_package(pkg_dict, {'package': pkg})

    # TODO: rename to something more correct like prepare_for_render
    @classmethod
    def render_package(cls, pkg, context):
        '''Prepares for rendering a package. Takes a Package object and
        formats it for the various context variables required to call
        render. 
        Note that the actual calling of render('package/read') is left
        to the caller.'''
        try:
            notes_formatted = ckan.misc.MarkdownFormat().to_html(pkg.get('notes',''))
            c.pkg_notes_formatted = genshi.HTML(notes_formatted)
        except Exception, e:
            error_msg = "<span class='inline-warning'>%s</span>" % _("Cannot render package description")
            c.pkg_notes_formatted = genshi.HTML(error_msg)
        c.current_rating, c.num_ratings = ckan.rating.get_rating(context['package'])
        url = pkg.get('url', '')
        c.pkg_url_link = h.link_to(url, url, rel='foaf:homepage', target='_blank') \
                if url else _("No web page given")
        c.pkg_author_link = cls._person_email_link(pkg.get('author', ''), pkg.get('author_email', ''), "Author")
        maintainer = pkg.get('maintainer', '')
        maintainer_email = pkg.get('maintainer_email', '')
        c.pkg_maintainer_link = cls._person_email_link(maintainer, maintainer_email, "Maintainer")
        c.package_relationships = context['package'].get_relationships_printable()
        c.pkg_extras = []
        for extra in sorted(pkg.get('extras',[]), key=lambda x:x['key']):
            if extra.get('state') == 'deleted':
                continue
            k, v = extra['key'], extra['value']
            if k in g.package_hide_extras:
                continue
            if isinstance(v, (list, tuple)):
                v = ", ".join(map(unicode, v))
            c.pkg_extras.append((k, v))
        if context.get('revision_id') or context.get('revision_date'):
            # request was for a specific revision id or date
            c.pkg_revision_id = c.pkg_dict[u'revision_id']
            c.pkg_revision_timestamp = c.pkg_dict[u'revision_timestamp']
            c.pkg_revision_not_latest = c.pkg_dict[u'revision_id'] != c.pkg.revision.id

    @classmethod
    def _preview_pkg(cls, fs, log_message=None, author=None, client=None):
        '''Previews the POST data (associated with a package edit)
        @input c.error
        @input fs      FieldSet with the param data bound to it
        @param log_message: only supply this if you want it validated
        @param author: only supply this if you want it validated
        @return package object
        '''
        try:
            out = cls._update(fs, log_message,
                              author, commit=False, client=client)
        except ValidationException, e:
            raise ValidationException(*e)
        finally:
            # While the package is still in the session, touch the relations
            # so that they load (they are set to lazy load) because we will
            # need to use their values later when we render the package
            # object (i.e. preview it).
            fs.model.license
            fs.model.groups
            fs.model.ratings
            fs.model.extras
            fs.model.resources
            # remove everything from session so nothing can get saved
            # accidentally
            model.Session.remove()
        return out

    @classmethod
    def commit_pkg(cls, fs, log_message, author, client=None):
        '''Writes the POST data (associated with a package edit) to the
        database
        @input c.error
        @input fs      FieldSet with the param data bound to it
        '''
        cls._update(fs, log_message, author, commit=True, client=client)

    @classmethod
    def _update(cls, fs, log_message, author, commit=True, client=None):
        # Todo: Consolidate log message field (and validation).
        # Todo: Separate out the preview line of execution, it's confusing.
        rev = None
        # validation
        errors = cls._revision_validation(log_message)
        if client:
            client.errors = errors
        fs.validate()
        validates = not (errors or fs.errors)
        if not validates:
            raise ValidationException(fs)
        # sync
        try:
            rev = model.repo.new_revision()
            rev.author = author
            rev.message = log_message
            fs.sync()
        except Exception, inst:
            model.Session.rollback()
            raise
        else:
            # only commit if desired and it validates ok
            if commit and validates:
                model.Session.commit()
            elif validates:
                # i.e. preview
                pkg = fs.model
                return pkg
        if rev and 'true' == config.get('changeset.auto_commit', '').strip():
            try:
                from ckan.model.changeset import ChangesetRegister
                changeset_ids = ChangesetRegister().commit()
                for id in changeset_ids:
                    msg = "PackageSaver auto-committed changeset '%s'." % id
                    logging.info(msg)
            except Exception, inst:
                msg = "PackageSaver failed to auto-commit revision '%s': %s" % (
                    rev.id, inst
                )
                logging.error(msg)

    @classmethod
    def _revision_validation(cls, log_message):
        errors = []
        if log_message and 'http:' in log_message:
            errors.append(_('No links are allowed in the log_message.'))
        return errors

    @classmethod
    def _person_email_link(cls, name, email, reference):
        if email:
            return h.mail_to(email_address=email, name=name or email, encode='hex')
        else:
            return name or reference + " not given"


class WritePackageFromBoundFieldset(object):

    def __init__(self, fieldset, log_message='', author='', client=None):
        self.fieldset = fieldset
        self.log_message = log_message
        self.author = author
        self.client = None
        self.write_package()

    def write_package(self):
        PackageSaver().commit_pkg(self.fieldset, self.log_message, self.author, self.client)

