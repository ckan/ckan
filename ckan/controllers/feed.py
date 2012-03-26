"""
The feed controller produces Atom feeds of datasets.

 * datasets belonging to a particular group.
 * datasets tagged with a particular tag.
 * datasets that match an arbitrary search.

Other feeds are available elsewhere in the code, but these provide feeds
of the revision history, rather than a feed of datasets.

 * ``ckan/controllers/group.py`` provides an atom feed of a group's
   revision history.
 * ``ckan/controllers/package.py`` provides an atom feed of a dataset's
   revision history.
 * ``ckan/controllers/revision.py`` provides an atom feed of the repository's
   revision history.

"""

import logging
import urlparse

import webhelpers.feedgenerator
from pylons import config
from urllib import urlencode

from ckan import model
from ckan.lib.base import BaseController, c, request, response, json, abort, g
from ckan.lib.helpers import date_str_to_datetime, url_for
from ckan.logic import get_action, NotFound

# TODO make the item list configurable
ITEMS_LIMIT = 20

log = logging.getLogger(__name__)

def _package_search(data_dict):
    """
    Helper method that wraps the package_search action.

     * unless overridden, sorts results by metadata_modified date
     * unless overridden, sets a default item limit
    """
    context = {'model': model, 'session': model.Session,
               'user': c.user or c.author}

    if not 'sort' in data_dict:
        data_dict['sort'] = 'metadata_modified desc'

    if not 'rows' in data_dict:
        data_dict['rows'] = ITEMS_LIMIT


    query = get_action('package_search')(context,data_dict)

    return query['results']

def _create_atom_id(resource_path, authority_name=None, date_string=None):
    """
    Helper method that creates an atom id for a feed or entry.

    An id must be unique, and must not change over time.  ie - once published,
    it represents an atom feed or entry uniquely, and forever.  See [4]:

        When an Atom Document is relocated, migrated, syndicated,
        republished, exported, or imported, the content of its atom:id
        element MUST NOT change.  Put another way, an atom:id element
        pertains to all instantiations of a particular Atom entry or feed;
        revisions retain the same content in their atom:id elements.  It is
        suggested that the atom:id element be stored along with the
        associated resource.

    resource_path
        The resource path that uniquely identifies the feed or element.  This
        mustn't be something that changes over time for a given entry or feed.
        And does not necessarily need to be resolvable.

        e.g. ``"/group/933f3857-79fd-4beb-a835-c0349e31ce76"`` could represent
        the feed of datasets belonging to the identified group.

    authority_name
        The domain name or email address of the publisher of the feed.  See [3]
        for more details.  If ``None`` then the domain name is taken from the
        config file.  First trying ``ckan.feeds.authority_name``, and failing
        that, it uses ``ckan.site_url``.  Again, this should not change over time.

    date_string
        A string representing a date on which the authority_name is owned by the
        publisher of the feed.

        e.g. ``"2012-03-22"``

        Again, this should not change over time.

        If date_string is None, then an attempt is made to read the config
        option ``ckan.feeds.date``.  If that's not available,
        then the date_string is not used in the generation of the atom id.

    Following the methods outlined in [1], [2] and [3], this function produces
    tagURIs like: ``"tag:thedatahub.org,2012:/group/933f3857-79fd-4beb-a835-c0349e31ce76"``.

    If not enough information is provide to produce a valid tagURI, then only
    the resource_path is used, e.g.: ::

        "http://thedatahub.org/group/933f3857-79fd-4beb-a835-c0349e31ce76"

    or

        "/group/933f3857-79fd-4beb-a835-c0349e31ce76"

    The latter of which is only used if no site_url is available.   And it should
    be noted will result in an invalid feed.

    [1] http://web.archive.org/web/20110514113830/http://diveintomark.org/archives/2004/05/28/howto-atom-id
    [2] http://www.taguri.org/
    [3] http://tools.ietf.org/html/rfc4151#section-2.1
    [4] http://www.ietf.org/rfc/rfc4287
    """
    if authority_name is None:
        authority_name = config.get('ckan.feeds.authority_name', '').strip()
        if not authority_name:
            site_url = config.get('ckan.site_url', '').strip()
            authority_name = urlparse.urlparse(site_url).netloc

    if not authority_name:
        log.warning('No authority_name available for feed generation.  '
                    'Generated feed will be invalid.')

    if date_string is None:
        date_string = config.get('ckan.feeds.date', '')
    
    if not date_string:
        log.warning('No date_string available for feed generation.  '
                    'Please set the "ckan.feeds.date" config value.')

        # Don't generate a tagURI without a date as it wouldn't be valid.
        # This is best we can do, and if the site_url is not set, then
        # this still results in an invalid feed.
        site_url = config.get('ckan.site_url', '')
        return '/'.join([site_url, resource_path])

    tagging_entity = ','.join([authority_name, date_string])
    return ':'.join(['tag', tagging_entity, resource_path])

class FeedController(BaseController):

    base_url = config.get('ckan.site_url')

    def group(self,id):

        try:
            context = {'model': model, 'session': model.Session,
               'user': c.user or c.author}
            group_dict = get_action('group_show')(context,{'id':id})
        except NotFound:
            abort(404,'Group not found')

        data_dict = {'q': 'groups: %s' % id }
        results= _package_search(data_dict)

        # TODO feed_link can be generated?
        return self.output_feed(results,
                    feed_title = u'%s - Group: "%s"' % (g.site_title, group_dict['title']),
                    feed_description = u'Recently created or updated datasets on %s by group: "%s"' % \
                        (g.site_title,group_dict['title']),
                    feed_link = u'%s/dataset?groups=%s' % (self.base_url,id),
                    feed_guid = _create_atom_id(u'/feeds/groups/%s.atom' % id),
                )

    def tag(self,id):

        data_dict = {'q': 'tags: %s' % id }
        results= _package_search(data_dict)

        # TODO feed_link can be generated?
        return self.output_feed(results,
                    feed_title = u'%s - Tag: "%s"' % (g.site_title, id),
                    feed_description = u'Recently created or updated datasets on %s by tag: "%s"' % \
                        (g.site_title, id),
                    feed_link = u'%s/dataset?tags=%s' % (self.base_url,id),
                    feed_guid = _create_atom_id(u'/feeds/tags/%s.atom' % id),
                )

    def general(self):
        data_dict = {'q': '*:*' }
        results= _package_search(data_dict)

        # TODO feed_link can be generated?
        return self.output_feed(results,
                    feed_title = g.site_title,
                    feed_description = u'Recently created or updated datasets on %s' % g.site_title,
                    feed_link = u'%s/dataset' % self.base_url,
                    feed_guid = _create_atom_id(u'/feeds/dataset.atom'),
                )

    # TODO check search params
    def custom(self):
        q = request.params.get('q', u'')
        search_params = {}
        for (param, value) in request.params.items():
            if not param in ['q', 'page'] \
                    and len(value) and not param.startswith('_'):
                search_params[param] = value
                q += ' %s: "%s"' % (param, value)

        search_url_params = urlencode(search_params)

        data_dict = { 'q':q }
        results= _package_search(data_dict)

        # TODO feed_link can be generated?
        return self.output_feed(results,
                    feed_title = u'%s - Custom query' % g.site_title,
                    feed_description = u'Recently created or updated datasets on %s. Custom query: \'%s\'' % (g.site_title, q),
                    feed_link = u'%s/dataset?%s' % (self.base_url, search_url_params),
                    feed_guid = _create_atom_id(u'/feeds/custom.atom?%s' % search_url_params),
                )

    def output_feed(self, results,
                          feed_title,
                          feed_description,
                          feed_link,
                          feed_guid):

        author_name = config.get('ckan.feeds.author_name', '').strip() or \
                      config.get('ckan.site_id', '').strip()
        author_link = config.get('ckan.feeds.author_link', '').strip() or \
                      config.get('ckan.site_url', '').strip()

        # TODO language
        feed = _FixedAtom1Feed(
            title=feed_title,
            link=feed_link,
            description=feed_description,
            language=u'en',
            author_name=author_name,
            author_link=author_link,
            feed_guid=feed_guid
            )

        for pkg in results:
            feed.add_item(
                    title = pkg.get('title', ''),
                    link = self.base_url + url_for(controller='package', action='read', id=pkg['id']),
                    description = pkg.get('notes', ''),
                    updated = date_str_to_datetime(pkg.get('metadata_modified')),
                    published = date_str_to_datetime(pkg.get('metadata_created')),
                    unique_id = _create_atom_id(u'/feeds/dataset/%s.atom' % pkg['id']),
                    author_name = pkg.get('author', ''),
                    author_email = pkg.get('author_email', ''),
                    categories = [t['name'] for t in pkg.get('tags', [])],
                    enclosure=webhelpers.feedgenerator.Enclosure(
                        self.base_url + url_for(controller='api', register='package', action='show', id=pkg['name'], ver='2'),
                        unicode(len(json.dumps(pkg))),
                        u'application/json'
                        )
                    )
        response.content_type = feed.mime_type
        return feed.writeString('utf-8')

# TODO paginated feed
class _FixedAtom1Feed(webhelpers.feedgenerator.Atom1Feed):
    """
    The Atom1Feed defined in webhelpers doesn't provide all the fields we
    might want to publish.

     * In Atom1Feed, each <entry> is created with identical <updated> and
       <published> fields.  See [1] (webhelpers 1.2) for details.

       So, this class fixes that by allow an item to set both an <updated> and
       <published> field.

     * In Atom1Feed, the feed description is not used.  So this class uses the
       <subtitle> field to publish that.

    [1] https://bitbucket.org/bbangert/webhelpers/src/f5867a319abf/webhelpers/feedgenerator.py#cl-373
    """

    def add_item(self, *args, **kwargs):
        """
        Drop the pubdate field from the new item.
        """
        if 'pubdate' in kwargs:
            kwargs.pop('pubdate')
        defaults = {'updated': None, 'published': None}
        defaults.update(kwargs)
        super(_FixedAtom1Feed, self).add_item(*args, **defaults)

    def latest_post_date(self):
        """
        Calculates the latest post date from the 'updated' fields,
        rather than the 'pubdate' fields.
        """
        updates = [ item['updated'] for item in self.items if item['updated'] is not None ]
        if not len(updates): # delegate to parent for default behaviour
            return super(_FixedAtom1Feed, self).latest_post_date()
        return max(updates)

    def add_item_elements(self, handler, item):
        """
        Add the <updated> and <published> fields to each entry that's written to the handler.
        """
        super(_FixedAtom1Feed, self).add_item_elements(handler, item)
        
        if(item['updated']):
            handler.addQuickElement(u'updated', webhelpers.feedgenerator.rfc3339_date(item['updated']).decode('utf-8'))

        if(item['published']):
            handler.addQuickElement(u'published', webhelpers.feedgenerator.rfc3339_date(item['published']).decode('utf-8'))

    def add_root_elements(self, handler):
        """
        Add the <subtitle> field from the feed description
        """
        super(_FixedAtom1Feed, self).add_root_elements(handler)

        handler.addQuickElement(u'subtitle', self.feed['description'])

