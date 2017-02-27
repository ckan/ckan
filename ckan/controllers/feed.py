# encoding: utf-8

"""
The feed controller produces Atom feeds of datasets.

 * datasets belonging to a particular group.
 * datasets tagged with a particular tag.
 * datasets that match an arbitrary search.

TODO: document paged feeds

Other feeds are available elsewhere in the code, but these provide feeds
of the revision history, rather than a feed of datasets.

 * ``ckan/controllers/group.py`` provides an atom feed of a group's
   revision history.
 * ``ckan/controllers/package.py`` provides an atom feed of a dataset's
   revision history.
 * ``ckan/controllers/revision.py`` provides an atom feed of the repository's
   revision history.

"""
# TODO fix imports
import logging
import urlparse

import webhelpers.feedgenerator

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as plugins

from ckan.common import _, config, c, request, response, json

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
               'user': c.user, 'auth_user_obj': c.userobj}

    if 'sort' not in data_dict or not data_dict['sort']:
        data_dict['sort'] = 'metadata_modified desc'

    if 'rows' not in data_dict or not data_dict['rows']:
        data_dict['rows'] = ITEMS_LIMIT

    # package_search action modifies the data_dict, so keep our copy intact.
    query = logic.get_action('package_search')(context, data_dict.copy())

    return query['count'], query['results']


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
        that, it uses ``ckan.site_url``.  Again, this should not change over
        time.

    date_string
        A string representing a date on which the authority_name is owned by
        the publisher of the feed.

        e.g. ``"2012-03-22"``

        Again, this should not change over time.

        If date_string is None, then an attempt is made to read the config
        option ``ckan.feeds.date``.  If that's not available,
        then the date_string is not used in the generation of the atom id.

    Following the methods outlined in [1], [2] and [3], this function produces
    tagURIs like:
    ``"tag:thedatahub.org,2012:/group/933f3857-79fd-4beb-a835-c0349e31ce76"``.

    If not enough information is provide to produce a valid tagURI, then only
    the resource_path is used, e.g.: ::

        "http://thedatahub.org/group/933f3857-79fd-4beb-a835-c0349e31ce76"

    or

        "/group/933f3857-79fd-4beb-a835-c0349e31ce76"

    The latter of which is only used if no site_url is available.   And it
    should be noted will result in an invalid feed.

    [1] http://web.archive.org/web/20110514113830/http://diveintomark.org/\
    archives/2004/05/28/howto-atom-id
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


class FeedController(base.BaseController):
    base_url = config.get('ckan.site_url')

    def _alternate_url(self, params, **kwargs):
        search_params = params.copy()
        search_params.update(kwargs)

        # Can't count on the page sizes being the same on the search results
        # view.  So provide an alternate link to the first page, regardless
        # of the page we're looking at in the feed.
        search_params.pop('page', None)
        return self._feed_url(search_params,
                              controller='package',
                              action='search')

    def _group_or_organization(self, obj_dict, is_org):

        data_dict, params = self._parse_url_params()
        if is_org:
            key = 'owner_org'
            value = obj_dict['id']
            group_type = 'organization'
        else:
            key = 'groups'
            value = obj_dict['name']
            group_type = 'group'

        data_dict['fq'] = '{0}:"{1}"'.format(key, value)

        item_count, results = _package_search(data_dict)

        navigation_urls = self._navigation_urls(params,
                                                item_count=item_count,
                                                limit=data_dict['rows'],
                                                controller='feed',
                                                action=group_type,
                                                id=obj_dict['name'])
        feed_url = self._feed_url(params,
                                  controller='feed',
                                  action=group_type,
                                  id=obj_dict['name'])

        site_title = config.get('ckan.site_title', 'CKAN')
        if is_org:
            guid = _create_atom_id(u'/feeds/organization/%s.atom' %
                                   obj_dict['name'])
            alternate_url = self._alternate_url(params,
                                                organization=obj_dict['name'])
            desc = u'Recently created or updated datasets on %s '\
                'by organization: "%s"' % (site_title, obj_dict['title'])
            title = u'%s - Organization: "%s"' % (site_title,
                                                  obj_dict['title'])

        else:  # is group
            guid = _create_atom_id(u'/feeds/group/%s.atom' %
                                   obj_dict['name'])
            alternate_url = self._alternate_url(params,
                                                groups=obj_dict['name'])
            desc = u'Recently created or updated datasets on %s '\
                'by group: "%s"' % (site_title, obj_dict['title'])
            title = u'%s - Group: "%s"' %\
                (site_title, obj_dict['title'])

        return self.output_feed(results,
                                feed_title=title,
                                feed_description=desc,
                                feed_link=alternate_url,
                                feed_guid=guid,
                                feed_url=feed_url,
                                navigation_urls=navigation_urls)

    def group(self, id):
        try:
            context = {'model': model, 'session': model.Session,
                       'user': c.user, 'auth_user_obj': c.userobj}
            group_dict = logic.get_action('group_show')(context, {'id': id})
        except logic.NotFound:
            base.abort(404, _('Group not found'))

        return self._group_or_organization(group_dict, is_org=False)

    def organization(self, id):
        try:
            context = {'model': model, 'session': model.Session,
                       'user': c.user, 'auth_user_obj': c.userobj}
            group_dict = logic.get_action('organization_show')(context,
                                                               {'id': id})
        except logic.NotFound:
            base.abort(404, _('Organization not found'))

        return self._group_or_organization(group_dict, is_org=True)

    def tag(self, id):
        data_dict, params = self._parse_url_params()
        data_dict['fq'] = 'tags:"%s"' % id

        item_count, results = _package_search(data_dict)

        navigation_urls = self._navigation_urls(params,
                                                item_count=item_count,
                                                limit=data_dict['rows'],
                                                controller='feed',
                                                action='tag',
                                                id=id)

        feed_url = self._feed_url(params,
                                  controller='feed',
                                  action='tag',
                                  id=id)

        alternate_url = self._alternate_url(params, tags=id)

        site_title = config.get('ckan.site_title', 'CKAN')

        return self.output_feed(results,
                                feed_title=u'%s - Tag: "%s"' %
                                (site_title, id),
                                feed_description=u'Recently created or '
                                'updated datasets on %s by tag: "%s"' %
                                (site_title, id),
                                feed_link=alternate_url,
                                feed_guid=_create_atom_id
                                (u'/feeds/tag/%s.atom' % id),
                                feed_url=feed_url,
                                navigation_urls=navigation_urls)

    def general(self):
        data_dict, params = self._parse_url_params()
        data_dict['q'] = '*:*'

        item_count, results = _package_search(data_dict)

        navigation_urls = self._navigation_urls(params,
                                                item_count=item_count,
                                                limit=data_dict['rows'],
                                                controller='feed',
                                                action='general')

        feed_url = self._feed_url(params,
                                  controller='feed',
                                  action='general')

        alternate_url = self._alternate_url(params)

        site_title = config.get('ckan.site_title', 'CKAN')

        return self.output_feed(results,
                                feed_title=site_title,
                                feed_description=u'Recently created or '
                                'updated datasets on %s' % site_title,
                                feed_link=alternate_url,
                                feed_guid=_create_atom_id
                                (u'/feeds/dataset.atom'),
                                feed_url=feed_url,
                                navigation_urls=navigation_urls)

    # TODO check search params
    def custom(self):
        q = request.params.get('q', u'')
        fq = ''
        search_params = {}
        for (param, value) in request.params.items():
            if param not in ['q', 'page', 'sort'] \
                    and len(value) and not param.startswith('_'):
                search_params[param] = value
                fq += ' %s:"%s"' % (param, value)

        page = h.get_page_number(request.params)

        limit = ITEMS_LIMIT
        data_dict = {
            'q': q,
            'fq': fq,
            'start': (page - 1) * limit,
            'rows': limit,
            'sort': request.params.get('sort', None),
        }

        item_count, results = _package_search(data_dict)

        navigation_urls = self._navigation_urls(request.params,
                                                item_count=item_count,
                                                limit=data_dict['rows'],
                                                controller='feed',
                                                action='custom')

        feed_url = self._feed_url(request.params,
                                  controller='feed',
                                  action='custom')

        atom_url = h._url_with_params('/feeds/custom.atom',
                                      search_params.items())

        alternate_url = self._alternate_url(request.params)

        site_title = config.get('ckan.site_title', 'CKAN')

        return self.output_feed(results,
                                feed_title=u'%s - Custom query' % site_title,
                                feed_description=u'Recently created or updated'
                                ' datasets on %s. Custom query: \'%s\'' %
                                (site_title, q),
                                feed_link=alternate_url,
                                feed_guid=_create_atom_id(atom_url),
                                feed_url=feed_url,
                                navigation_urls=navigation_urls)

    def output_feed(self, results, feed_title, feed_description,
                    feed_link, feed_url, navigation_urls, feed_guid):
        author_name = config.get('ckan.feeds.author_name', '').strip() or \
            config.get('ckan.site_id', '').strip()
        author_link = config.get('ckan.feeds.author_link', '').strip() or \
            config.get('ckan.site_url', '').strip()

        # TODO language
        feed_class = None
        for plugin in plugins.PluginImplementations(plugins.IFeed):
            if hasattr(plugin, 'get_feed_class'):
                feed_class = plugin.get_feed_class()

        if not feed_class:
            feed_class = _FixedAtom1Feed

        feed = feed_class(
            feed_title,
            feed_link,
            feed_description,
            language=u'en',
            author_name=author_name,
            author_link=author_link,
            feed_guid=feed_guid,
            feed_url=feed_url,
            previous_page=navigation_urls['previous'],
            next_page=navigation_urls['next'],
            first_page=navigation_urls['first'],
            last_page=navigation_urls['last'],
        )

        for pkg in results:
            additional_fields = {}

            for plugin in plugins.PluginImplementations(plugins.IFeed):
                if hasattr(plugin, 'get_item_additional_fields'):
                    additional_fields = plugin.get_item_additional_fields(pkg)

            feed.add_item(
                title=pkg.get('title', ''),
                link=self.base_url + h.url_for(controller='package',
                                               action='read',
                                               id=pkg['id']),
                description=pkg.get('notes', ''),
                updated=h.date_str_to_datetime(pkg.get('metadata_modified')),
                published=h.date_str_to_datetime(pkg.get('metadata_created')),
                unique_id=_create_atom_id(u'/dataset/%s' % pkg['id']),
                author_name=pkg.get('author', ''),
                author_email=pkg.get('author_email', ''),
                categories=[t['name'] for t in pkg.get('tags', [])],
                enclosure=webhelpers.feedgenerator.Enclosure(
                    self.base_url + h.url_for(controller='api',
                                              register='package',
                                              action='show',
                                              id=pkg['name'],
                                              ver='2'),
                    unicode(len(json.dumps(pkg))),   # TODO fix this
                    u'application/json'),
                **additional_fields
            )
        response.content_type = feed.mime_type
        return feed.writeString('utf-8')

    # CLASS PRIVATE METHODS #

    def _feed_url(self, query, controller, action, **kwargs):
        """
        Constructs the url for the given action.  Encoding the query
        parameters.
        """
        path = h.url_for(controller=controller, action=action, **kwargs)
        return h._url_with_params(self.base_url + path, query.items())

    def _navigation_urls(self, query, controller, action,
                         item_count, limit, **kwargs):
        """
        Constructs and returns first, last, prev and next links for paging
        """
        urls = dict((rel, None) for rel in 'previous next first last'.split())

        page = int(query.get('page', 1))

        # first: remove any page parameter
        first_query = query.copy()
        first_query.pop('page', None)
        urls['first'] = self._feed_url(first_query, controller,
                                       action, **kwargs)

        # last: add last page parameter
        last_page = (item_count / limit) + min(1, item_count % limit)
        last_query = query.copy()
        last_query['page'] = last_page
        urls['last'] = self._feed_url(last_query, controller,
                                      action, **kwargs)

        # previous
        if page > 1:
            previous_query = query.copy()
            previous_query['page'] = page - 1
            urls['previous'] = self._feed_url(previous_query, controller,
                                              action, **kwargs)
        else:
            urls['previous'] = None

        # next
        if page < last_page:
            next_query = query.copy()
            next_query['page'] = page + 1
            urls['next'] = self._feed_url(next_query, controller,
                                          action, **kwargs)
        else:
            urls['next'] = None

        return urls

    def _parse_url_params(self):
        """
        Constructs a search-query dict from the URL query parameters.

        Returns the constructed search-query dict, and the valid URL
        query parameters.
        """
        page = h.get_page_number(request.params)

        limit = ITEMS_LIMIT
        data_dict = {
            'start': (page - 1) * limit,
            'rows': limit
        }

        # Filter ignored query parameters
        valid_params = ['page']
        params = dict((p, request.params.get(p)) for p in valid_params
                      if p in request.params)
        return data_dict, params


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

       [1] https://bitbucket.org/bbangert/webhelpers/src/f5867a319abf/\
       webhelpers/feedgenerator.py#cl-373
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
        updates = [item['updated'] for item in self.items
                   if item['updated'] is not None]
        if not len(updates):  # delegate to parent for default behaviour
            return super(_FixedAtom1Feed, self).latest_post_date()
        return max(updates)

    def add_item_elements(self, handler, item):
        """
        Add the <updated> and <published> fields to each entry that's written
        to the handler.
        """
        super(_FixedAtom1Feed, self).add_item_elements(handler, item)

        dfunc = webhelpers.feedgenerator.rfc3339_date

        if(item['updated']):
            handler.addQuickElement(u'updated',
                                    dfunc(item['updated']).decode('utf-8'))

        if(item['published']):
            handler.addQuickElement(u'published',
                                    dfunc(item['published']).decode('utf-8'))

    def add_root_elements(self, handler):
        """
        Add additional feed fields.

         * Add the <subtitle> field from the feed description
         * Add links other pages of the logical feed.
        """
        super(_FixedAtom1Feed, self).add_root_elements(handler)

        handler.addQuickElement(u'subtitle', self.feed['description'])

        for page in ['previous', 'next', 'first', 'last']:
            if self.feed.get(page + '_page', None):
                handler.addQuickElement(u'link', u'',
                                        {'rel': page,
                                         'href':
                                            self.feed.get(page + '_page')})
