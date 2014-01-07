import ckan.lib.helpers as h
import ckan.lib.base as base
import ckan.model as model
import ckan.rating

from ckan.common import g, c, _

# Todo: Factor out unused original_name argument.

class PackageSaver(object):
    '''Use this to validate and save packages to the db.
    @param log_message: optional - only supply this if you want it validated
    @param author: optional - only supply this if you want it validated
    '''

    # TODO: rename to something more correct like prepare_for_render
    @classmethod
    def render_package(cls, pkg, context):
        '''Prepares for rendering a package. Takes a Package object and
        formats it for the various context variables required to call
        render. 
        Note that the actual calling of render('package/read') is left
        to the caller.'''
        c.pkg_notes_formatted = h.render_markdown(pkg.get('notes'))

        c.current_rating, c.num_ratings = ckan.rating.get_rating(context['package'])
        url = pkg.get('url', '')
        c.pkg_url_link = h.link_to(url, url, rel='foaf:homepage', target='_blank') \
                if url else _("No web page given")

        c.pkg_author_link = cls._person_email_link(
                name=pkg.get('author'), email=pkg.get('author_email'),
                fallback=_("Author not given"))
        c.pkg_maintainer_link = cls._person_email_link(
                name=pkg.get('maintainer'), email=pkg.get('maintainer_email'),
                fallback=_("Maintainer not given"))

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
    def commit_pkg(cls, fs, log_message, author, client=None):
        '''Writes the POST data (associated with a package edit) to the
        database
        @input c.error
        @input fs      FieldSet with the param data bound to it
        '''
        cls._update(fs, log_message, author, client=client)

    @classmethod
    def _update(cls, fs, log_message, author, client=None):
        # Todo: Consolidate log message field (and validation).
        rev = None
        # validation
        errors = cls._revision_validation(log_message)
        if client:
            client.errors = errors
        fs.validate()
        validates = not (errors or fs.errors)
        if not validates:
            raise base.ValidationException(fs)
        # sync
        try:
            rev = model.repo.new_revision()
            rev.author = author
            rev.message = log_message
            fs.sync()
        except Exception:
            model.Session.rollback()
            raise
        else:
            # only commit if it validates ok
            if validates:
                model.Session.commit()

    @classmethod
    def _revision_validation(cls, log_message):
        errors = []
        if log_message and 'http:' in log_message:
            errors.append(_('No links are allowed in the log_message.'))
        return errors

    @classmethod
    def _person_email_link(cls, name, email, fallback):
        if email:
            return h.mail_to(email_address=email, name=name or email,
                    encode='hex')
        else:
            return name or fallback

class WritePackageFromBoundFieldset(object):

    def __init__(self, fieldset, log_message='', author='', client=None):
        self.fieldset = fieldset
        self.log_message = log_message
        self.author = author
        self.client = None
        self.write_package()

    def write_package(self):
        PackageSaver().commit_pkg(self.fieldset, self.log_message, self.author, self.client)

