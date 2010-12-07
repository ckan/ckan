import genshi
from sqlalchemy import orm
import ckan.lib.helpers as h
from ckan.lib.base import *
import ckan.rating
from pylons import g

# Todo: Factor out unused original_name argument.

class ValidationException(Exception):
    pass

class PackageSaver(object):
    '''Use this to validate, preview and save packages to the db.
    @param log_message: optional - only supply this if you want it validated
    @param author: optional - only supply this if you want it validated
    '''
    @classmethod
    def render_preview(cls, fs, original_name, record_id,
                       log_message=None,
                       author=None, client=None):
        '''Renders a package on the basis of a fieldset - perfect for
        preview of form data.
        Note that the actual calling of render('package/read') is left
        to the caller.'''
        pkg = cls._preview_pkg(fs, original_name, record_id,
                               log_message, author, client=client)
        cls.render_package(pkg)

    # TODO: rename to something more correct like prepare_for_render
    @classmethod
    def render_package(cls, pkg):
        '''Prepares for rendering a package. Takes a Package object and
        formats it for the various context variables required to call
        render. 
        Note that the actual calling of render('package/read') is left
        to the caller.'''
        c.pkg = pkg
        notes_formatted = ckan.misc.MarkdownFormat().to_html(pkg.notes)
        c.pkg_extras = sorted([(k, v) for k, v in pkg.extras.items() \
                               if k not in g.package_hide_extras])
        c.pkg_notes_formatted = genshi.HTML(notes_formatted)
        c.current_rating, c.num_ratings = ckan.rating.get_rating(pkg)
        c.pkg_url_link = h.link_to(c.pkg.url, c.pkg.url, target='_blank') if c.pkg.url else "No web page given"
        c.pkg_author_link = cls._person_email_link(c.pkg.author, c.pkg.author_email, "Author")
        c.pkg_maintainer_link = cls._person_email_link(c.pkg.maintainer, c.pkg.maintainer_email, "Maintainer")
        c.package_relationships = pkg.get_relationships_printable()

    @classmethod
    def _preview_pkg(cls, fs, original_name, pkg_id,
                     log_message=None, author=None, client=None):
        '''Previews the POST data (associated with a package edit)
        @input c.error
        @input fs      FieldSet with the param data bound to it
        @input original_name Name of the package before this edit
        @input pkg_id Package id
        @param log_message: only supply this if you want it validated
        @param author: only supply this if you want it validated
        @return package object
        '''
        try:
            out = cls._update(fs, original_name, pkg_id, log_message,
                              author, commit=False, client=client)
            # While pkg is still in the session, touch the relations so they
            # lazy load, for use later.
            fs.model.license
            fs.model.groups
            fs.model.ratings
        except ValidationException, e:
            # remove everything from session so nothing can get saved accidentally
            model.Session.clear()
            raise ValidationException(*e)
        # remove everything from session so nothing can get saved accidentally
        model.Session.clear()
        return out

    @classmethod
    def commit_pkg(cls, fs, original_name, pkg_id, log_message, author, client=None):
        '''Writes the POST data (associated with a package edit) to the
        database
        @input c.error
        @input fs      FieldSet with the param data bound to it
        @input original_name Name of the package before this edit
        @input pkg_id Package id
        '''
        cls._update(fs, original_name, pkg_id, log_message, author, commit=True, client=client)

    @classmethod
    def _update(cls, fs, original_name, pkg_id, log_message, author, commit=True, client=None):
        # Todo: Remove original_name and pkg_id, since they aren't used.
        # Todo: Consolidate log message field (and validation).
        # Todo: Separate out the preview line of execution, it's confusing.
        rev = None
        # validation
        errors = cls._revision_validation(log_message)
        if client:
            client.errors = errors
        fs.validate()
        validates = not (errors or fs.errors)

        # sync
        try:
            if commit:
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
            elif not validates:
                raise ValidationException(fs)
            else:
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
        PackageSaver().commit_pkg(self.fieldset, None, None, self.log_message, self.author, self.client)

