# encoding: utf-8

import logging
import urlparse

from flask import Blueprint, make_response
from six import text_type
import webhelpers.feedgenerator
from ckan.common import _, config, g, request, response
import ckan.lib.helpers as h
import ckan.lib.base as base
import ckan.model as model
import ckan.logic as logic
import ckan.plugins as plugins
import json

log = logging.getLogger(__name__)

feeds = Blueprint(u'feeds', __name__, url_prefix=u'/feeds')

ITEMS_LIMIT = config.get(u'ckan.feeds.limit', 20)
BASE_URL = config.get(u'ckan.site_url')
SITE_TITLE = config.get(u'ckan.site_title', u'CKAN')


def _package_search(data_dict):
    """
    Helper method that wraps the package_search action.

     * unless overridden, sorts results by metadata_modified date
     * unless overridden, sets a default item limit
    """
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj
    }
    if u'sort' not in data_dict or not data_dict['sort']:
        data_dict['sort'] = u'metadata_modified desc'

    if u'rows' not in data_dict or not data_dict['rows']:
        data_dict['rows'] = ITEMS_LIMIT

    # package_search action modifies the data_dict, so keep our copy intact.
    query = logic.get_action(u'package_search')(context, data_dict.copy())

    return query['count'], query['results']


def _enclosure(pkg):
    links = []
    links.append({
        u'href': h.url(u'api.action', logic_function=u'package_show',
                       ver=3, id=pkg['id'], _external=True),
        u'rel': u'',
        u'length': text_type(len(json.dumps(pkg))),
        u'type': u'application/json'})
    return links


def _set_extras(**kw):
    extras = []
    for key, value in kw.iteritems():
        extras.append({key: value})
    return extras


def output_feed(results, feed_title, feed_description, feed_link, feed_url,
                navigation_urls, feed_guid):
    author_name = config.get(u'ckan.feeds.author_name', u'').strip() or \
        config.get(u'ckan.site_id', u'').strip()

    # TODO: language
    feed_class = None
    for plugin in plugins.PluginImplementations(plugins.IFeed):
        if hasattr(plugin, u'get_feed_class'):
            feed_class = plugin.get_feed_class()

    if not feed_class:
        feed_class = _FixedAtom1Feed

    feed = feed_class(
        feed_title,
        feed_link,
        feed_description,
        language=u'en',
        author_name=author_name,
        feed_guid=feed_guid,
        feed_url=feed_url,
        previous_page=navigation_urls[u'previous'],
        next_page=navigation_urls[u'next'],
        first_page=navigation_urls[u'first'],
        last_page=navigation_urls[u'last'], )

    for pkg in results:
        additional_fields = {}

        for plugin in plugins.PluginImplementations(plugins.IFeed):
            if hasattr(plugin, u'get_item_additional_fields'):
                additional_fields = plugin.get_item_additional_fields(pkg)

        feed.add_item(
            title=pkg.get(u'title', u''),
            link=h.url_for(
                u'api.action',
                logic_function=u'package_read',
                id=pkg['id'],
                ver=3,
                _external=True),
            description=pkg.get(u'notes', u''),
            updated=h.date_str_to_datetime(pkg.get(u'metadata_modified')),
            published=h.date_str_to_datetime(pkg.get(u'metadata_created')),
            unique_id=_create_atom_id(u'/dataset/%s' % pkg['id']),
            author_name=pkg.get(u'author', u''),
            author_email=pkg.get(u'author_email', u''),
            categories=[t['name'] for t in pkg.get(u'tags', [])],
            enclosure=webhelpers.feedgenerator.Enclosure(
                h.url_for(
                    u'api.action',
                    logic_function=u'package_show',
                    id=pkg['name'],
                    ver=3,
                    _external=True),
                text_type(len(json.dumps(pkg))), u'application/json'),
            **additional_fields)

    resp = make_response(feed.writeString(u'utf-8'), 200)
    resp.headers['Content-Type'] = u'application/atom+xml'
    return resp


def group(id):
    try:
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        group_dict = logic.get_action(u'group_show')(context, {u'id': id})
    except logic.NotFound:
        base.abort(404, _(u'Group not found'))

    return group_or_organization(group_dict, is_org=False)


def organization(id):
    try:
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        group_dict = logic.get_action(u'organization_show')(context, {
            u'id': id
        })
    except logic.NotFound:
        base.abort(404, _(u'Organization not found'))

    return group_or_organization(group_dict, is_org=True)


def tag(id):
    data_dict, params = _parse_url_params()
    data_dict['fq'] = u'tags: "%s"' % id

    item_count, results = _package_search(data_dict)

    navigation_urls = _navigation_urls(
        params,
        item_count=item_count,
        limit=data_dict['rows'],
        controller=u'feeds',
        action=u'tag',
        id=id)

    feed_url = _feed_url(params, controller=u'feeds', action=u'tag', id=id)

    alternate_url = _alternate_url(params, tags=id)

    title = u'%s - Tag: "%s"' % (SITE_TITLE, id)
    desc = u'Recently created or updated datasets on %s by tag: "%s"' % \
           (SITE_TITLE, id)
    guid = _create_atom_id(u'/feeds/tag/%s.atom' % id)

    return output_feed(
        results,
        feed_title=title,
        feed_description=desc,
        feed_link=alternate_url,
        feed_guid=guid,
        feed_url=feed_url,
        navigation_urls=navigation_urls)


def group_or_organization(obj_dict, is_org):
    data_dict, params = _parse_url_params()
    if is_org:
        key = u'owner_org'
        value = obj_dict['id']
        group_type = u'organization'
    else:
        key = u'groups'
        value = obj_dict['name']
        group_type = u'group'

    data_dict['fq'] = u'{0}: "{1}"'.format(key, value)
    item_count, results = _package_search(data_dict)

    navigation_urls = _navigation_urls(
        params,
        item_count=item_count,
        limit=data_dict['rows'],
        controller=u'feed',
        action=group_type,
        id=obj_dict['name'])
    feed_url = _feed_url(
        params, controller=u'feed', action=group_type, id=obj_dict['name'])
    # site_title = SITE_TITLE
    if is_org:
        guid = _create_atom_id(
            u'feeds/organization/%s.atom' % obj_dict['name'])
        alternate_url = _alternate_url(params, organization=obj_dict['name'])
        desc = u'Recently created or updated datasets on %s '\
               'by organization: "%s"' % (SITE_TITLE, obj_dict['title'])
        title = u'%s - Organization: "%s"' % (SITE_TITLE, obj_dict['title'])

    else:
        guid = _create_atom_id(u'feeds/group/%s.atom' % obj_dict['name'])
        alternate_url = _alternate_url(params, groups=obj_dict['name'])
        desc = u'Recently created or updated datasets on %s '\
               'by group: "%s"' % (SITE_TITLE, obj_dict['title'])
        title = u'%s - Group: "%s"' % (SITE_TITLE, obj_dict['title'])

    return output_feed(
        results,
        feed_title=title,
        feed_description=desc,
        feed_link=alternate_url,
        feed_guid=guid,
        feed_url=feed_url,
        navigation_urls=navigation_urls)


def _parse_url_params():
    """
    Constructs a search-query dict from the URL query parameters.

    Returns the constructed search-query dict, and the valid URL
    query parameters.
    """
    page = h.get_page_number(request.params)

    limit = ITEMS_LIMIT
    data_dict = {u'start': (page - 1) * limit, u'rows': limit}

    # Filter ignored query parameters
    valid_params = ['page']
    params = dict((p, request.params.get(p)) for p in valid_params
                  if p in request.params)
    return data_dict, params


def general():
    data_dict, params = _parse_url_params()
    data_dict['q'] = u'*:*'

    item_count, results = _package_search(data_dict)

    navigation_urls = _navigation_urls(
        params,
        item_count=item_count,
        limit=data_dict['rows'],
        controller=u'feeds',
        action=u'general')

    feed_url = _feed_url(params, controller=u'feeds', action=u'general')

    alternate_url = _alternate_url(params)

    guid = _create_atom_id(u'/feeds/dataset.atom')

    desc = u'Recently created or updated datasets on %s' % SITE_TITLE

    return output_feed(
        results,
        feed_title=SITE_TITLE,
        feed_description=desc,
        feed_link=alternate_url,
        feed_guid=guid,
        feed_url=feed_url,
        navigation_urls=navigation_urls)


def custom():
    """
    Custom atom feed

    """
    q = request.params.get(u'q', u'')
    fq = u''
    search_params = {}
    for (param, value) in request.params.items():
        if param not in [u'q', u'page', u'sort'] \
                and len(value) and not param.startswith(u'_'):
            search_params[param] = value
            fq += u'%s:"%s"' % (param, value)

    page = h.get_page_number(request.params)

    limit = ITEMS_LIMIT
    data_dict = {
        u'q': q,
        u'fq': fq,
        u'start': (page - 1) * limit,
        u'rows': limit,
        u'sort': request.params.get(u'sort', None)
    }

    item_count, results = _package_search(data_dict)

    navigation_urls = _navigation_urls(
        request.params,
        item_count=item_count,
        limit=data_dict['rows'],
        controller=u'feeds',
        action=u'custom')

    feed_url = _feed_url(request.params, controller=u'feeds', action=u'custom')

    atom_url = h._url_with_params(u'/feeds/custom.atom', search_params.items())

    alternate_url = _alternate_url(request.params)

    return output_feed(
        results,
        feed_title=u'%s - Custom query' % SITE_TITLE,
        feed_description=u'Recently created or updated'
        ' datasets on %s. Custom query: \'%s\'' % (SITE_TITLE, q),
        feed_link=alternate_url,
        feed_guid=_create_atom_id(atom_url),
        feed_url=feed_url,
        navigation_urls=navigation_urls)


def _alternate_url(params, **kwargs):
    search_params = params.copy()
    search_params.update(kwargs)

    # Can't count on the page sizes being the same on the search results
    # view.  So provide an alternate link to the first page, regardless
    # of the page we're looking at in the feed.
    search_params.pop(u'page', None)
    return _feed_url(search_params, controller=u'package', action=u'search')


def _feed_url(query, controller, action, **kwargs):
    """
    Constructs the url for the given action.  Encoding the query
    parameters.
    """
    for item in query.iteritems():
        kwargs['query'] = item
    return h.url_for(controller=controller, action=action, **kwargs)


def _navigation_urls(query, controller, action, item_count, limit, **kwargs):
    """
    Constructs and returns first, last, prev and next links for paging
    """

    urls = dict((rel, None) for rel in u'previous next first last'.split())

    page = int(query.get(u'page', 1))

    # first: remove any page parameter
    first_query = query.copy()
    first_query.pop(u'page', None)
    urls['first'] = _feed_url(first_query, controller,
                              action, **kwargs)

    # last: add last page parameter
    last_page = (item_count / limit) + min(1, item_count % limit)
    last_query = query.copy()
    last_query['page'] = last_page
    urls['last'] = _feed_url(last_query, controller,
                             action, **kwargs)

    # previous
    if page > 1:
        previous_query = query.copy()
        previous_query['page'] = page - 1
        urls['previous'] = _feed_url(previous_query, controller,
                                     action, **kwargs)
    else:
        urls['previous'] = None

    # next
    if page < last_page:
        next_query = query.copy()
        next_query['page'] = page + 1
        urls['next'] = _feed_url(next_query, controller,
                                 action, **kwargs)
    else:
        urls['next'] = None

    return urls


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
        authority_name = config.get(u'ckan.feeds.authority_name', u'').strip()
        if not authority_name:
            site_url = config.get(u'ckan.site_url', u'').strip()
            authority_name = urlparse.urlparse(site_url).netloc

    if not authority_name:
        log.warning(u'No authority_name available for feed generation.  '
                    'Generated feed will be invalid.')

    if date_string is None:
        date_string = config.get(u'ckan.feeds.date', u'')

    if not date_string:
        log.warning(u'No date_string available for feed generation.  '
                    'Please set the "ckan.feeds.date" config value.')

        # Don't generate a tagURI without a date as it wouldn't be valid.
        # This is best we can do, and if the site_url is not set, then
        # this still results in an invalid feed.
        site_url = config.get(u'ckan.site_url', u'')
        return u''.join([site_url, resource_path])

    tagging_entity = u','.join([authority_name, date_string])
    return u':'.join(['tag', tagging_entity, resource_path])


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
        if u'pubdate' in kwargs:
            kwargs.pop(u'pubdate')
        defaults = {u'updated': None, u'published': None}
        defaults.update(kwargs)
        super(_FixedAtom1Feed, self).add_item(*args, **defaults)

    def latest_post_date(self):
        """
        Calculates the latest post date from the 'updated' fields,
        rather than the 'pubdate' fields.
        """
        updates = [
            item['updated'] for item in self.items
            if item['updated'] is not None
        ]
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

        if (item['updated']):
            handler.addQuickElement(u'updated',
                                    dfunc(item['updated']).decode(u'utf-8'))

        if (item['published']):
            handler.addQuickElement(u'published',
                                    dfunc(item['published']).decode(u'utf-8'))

    def add_root_elements(self, handler):
        """
        Add additional feed fields.
         * Add the <subtitle> field from the feed description
         * Add links other pages of the logical feed.
        """
        super(_FixedAtom1Feed, self).add_root_elements(handler)

        handler.addQuickElement(u'subtitle', self.feed['description'])

        for page in [u'previous', u'next', u'first', u'last']:
            if self.feed.get(page + u'_page', None):
                handler.addQuickElement(u'link', u'', {
                    u'rel': page,
                    u'href': self.feed.get(page + u'_page')
                })


# Routing
feeds.add_url_rule(u'/dataset.atom', methods=[u'GET'], view_func=general)
feeds.add_url_rule(u'/custom.atom', methods=[u'GET'], view_func=custom)
feeds.add_url_rule(u'/tag/<string:id>.atom', methods=[u'GET'], view_func=tag)
feeds.add_url_rule(
    u'/group/<string:id>.atom', methods=[u'GET'], view_func=group)
feeds.add_url_rule(
    u'/organization/<string:id>.atom',
    methods=[u'GET'],
    view_func=organization)
