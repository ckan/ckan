# encoding: utf-8
from __future__ import annotations

import logging
import json
import unicodedata
from typing import Optional, cast, Any


from urllib.parse import urlparse
from flask import Blueprint, make_response

from dateutil.tz import tzutc
from feedgen.feed import FeedGenerator
from ckan.common import _, config, request, current_user
from ckan.lib.helpers import helper_functions as h
from ckan.lib.helpers import _url_with_params
import ckan.lib.base as base
import ckan.model as model
import ckan.logic as logic
import ckan.plugins as plugins
from ckan.types import Context, DataDict, PFeedFactory, Response

log = logging.getLogger(__name__)

feeds = Blueprint(u'feeds', __name__, url_prefix=u'/feeds')


def _package_search(data_dict: DataDict) -> tuple[int, list[dict[str, Any]]]:
    """
    Helper method that wraps the package_search action.

     * unless overridden, sorts results by metadata_modified date
     * unless overridden, sets a default item limit
    """
    context = cast(Context, {
        u'model': model,
        u'session': model.Session,
        u'user': current_user.name,
        u'auth_user_obj': current_user
    })
    if u'sort' not in data_dict or not data_dict['sort']:
        data_dict['sort'] = u'metadata_modified desc'

    if u'rows' not in data_dict or not data_dict['rows']:
        data_dict['rows'] = config.get('ckan.feeds.limit')

    # package_search action modifies the data_dict, so keep our copy intact.
    query = logic.get_action(u'package_search')(context, data_dict.copy())

    return query['count'], query['results']


def _enclosure(pkg: dict[str, Any]) -> 'Enclosure':
    url = h.url_for(
        u'api.action',
        logic_function=u'package_show',
        id=pkg['name'],
        ver=3,
        _external=True
    )
    enc = Enclosure(url)
    enc.mime_type = u'application/json'
    enc.length = str(len(json.dumps(pkg)))
    return enc


class Enclosure(str):
    def __init__(self, url: str):
        self.url = url
        self.length = u'0'
        self.mime_type = u'application/json'


class CKANFeed(FeedGenerator):
    def __init__(
        self,
        feed_title: str,
        feed_link: str,
        feed_description: str,
        language: Optional[str],
        author_name: Optional[str],
        feed_guid: Optional[str],
        feed_url: Optional[str],
        previous_page: Optional[str],
        next_page: Optional[str],
        first_page: Optional[str],
        last_page: Optional[str],
    ) -> None:
        super(CKANFeed, self).__init__()

        self.title(feed_title)
        self.link(href=feed_link, rel=u"alternate")
        self.description(feed_description)
        self.language(language)
        self.author({u"name": author_name})
        self.id(feed_guid)
        self.link(href=feed_url, rel=u"self")
        links = (
            (u"prev", previous_page),
            (u"next", next_page),
            (u"first", first_page),
            (u"last", last_page),
        )
        for rel, href in links:
            if not href:
                continue
            self.link(href=href, rel=rel)

    def writeString(self, encoding: str) -> str:  # noqa
        return cast(str, self.atom_str(encoding=encoding))

    def add_item(self, **kwargs: Any) -> None:
        entry = self.add_entry()
        for key, value in kwargs.items():
            if key in {u"published", u"updated"} and not value.tzinfo:
                value = value.replace(tzinfo=tzutc())
            elif key == u'unique_id':
                key = u'id'
            elif key == u'categories':
                key = u'category'
                value = [{u'term': t} for t in value]
            elif key == u'link':
                value = {u'href': value}
            elif key == u'author_name':
                key = u'author'
                value = {u'name': value}
            elif key == u'author_email':
                key = u'author'
                value = {u'email': value}

            key = key.replace(u"field_", u"")
            getattr(entry, key)(value)


def output_feed(
        results: list[dict[str, Any]], feed_title: str, feed_description: str,
        feed_link: str, feed_url: str, navigation_urls: dict[str, str],
        feed_guid: str) -> Response:
    author_name = config.get(u'ckan.feeds.author_name').strip() or \
        config.get(u'ckan.site_id').strip()

    def remove_control_characters(s: str):
        if not s:
            return ""

        return "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")

    # TODO: language
    feed_class: PFeedFactory = CKANFeed
    for plugin in plugins.PluginImplementations(plugins.IFeed):
        if hasattr(plugin, u'get_feed_class'):
            feed_class = plugin.get_feed_class()

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
        additional_fields: dict[str, Any] = {}

        for plugin in plugins.PluginImplementations(plugins.IFeed):
            if hasattr(plugin, u'get_item_additional_fields'):
                additional_fields = plugin.get_item_additional_fields(pkg)

        feed.add_item(
            title=pkg.get(u'title', u''),
            link=h.url_for(
                u'api.action',
                logic_function=u'package_show',
                id=pkg['id'],
                ver=3,
                _external=True),
            description=remove_control_characters(pkg.get(u'notes', u'')),
            updated=h.date_str_to_datetime(pkg.get(u'metadata_modified', '')),
            published=h.date_str_to_datetime(pkg.get(u'metadata_created', '')),
            unique_id=_create_atom_id(u'/dataset/%s' % pkg['id']),
            author_name=pkg.get(u'author', u''),
            author_email=pkg.get(u'author_email', u''),
            categories=[t[u'name'] for t in pkg.get(u'tags', [])],
            enclosure=_enclosure(pkg),
            **additional_fields)

    resp = make_response(feed.writeString(u'utf-8'), 200)
    resp.headers['Content-Type'] = u'application/atom+xml'
    return resp


def group(id: str) -> Response:
    try:
        context = cast(Context, {
            u'model': model,
            u'session': model.Session,
            u'user': current_user.name,
            u'auth_user_obj': current_user
        })
        group_dict = logic.get_action(u'group_show')(context, {u'id': id})
    except logic.NotFound:
        base.abort(404, _(u'Group not found'))
    except logic.NotAuthorized:
        base.abort(403, _('Not authorized to see this page'))

    return group_or_organization(group_dict, is_org=False)


def organization(id: str) -> Response:
    try:
        context = cast(Context, {
            u'model': model,
            u'session': model.Session,
            u'user': current_user.name,
            u'auth_user_obj': current_user
        })
        group_dict = logic.get_action(u'organization_show')(context, {
            u'id': id
        })
    except logic.NotFound:
        base.abort(404, _(u'Organization not found'))
    except logic.NotAuthorized:
        base.abort(403, _('Not authorized to see this page'))

    return group_or_organization(group_dict, is_org=True)


def tag(id: str) -> Response:
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

    site_title = config.get(u'ckan.site_title')
    title = u'%s - Tag: "%s"' % (site_title, id)
    desc = u'Recently created or updated datasets on %s by tag: "%s"' % \
           (site_title, id)
    guid = _create_atom_id(u'/feeds/tag/%s.atom' % id)

    return output_feed(
        results,
        feed_title=title,
        feed_description=desc,
        feed_link=alternate_url,
        feed_guid=guid,
        feed_url=feed_url,
        navigation_urls=navigation_urls)


def group_or_organization(obj_dict: dict[str, Any], is_org: bool) -> Response:
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
    site_title = config.get(u'ckan.site_title')

    navigation_urls = _navigation_urls(
        params,
        item_count=item_count,
        limit=data_dict['rows'],
        controller=u'feeds',
        action=group_type,
        id=obj_dict['name'])
    feed_url = _feed_url(
        params, controller=u'feeds', action=group_type, id=obj_dict['name'])
    # site_title = SITE_TITLE
    if is_org:
        guid = _create_atom_id(
            u'feeds/organization/%s.atom' % obj_dict['name'])
        alternate_url = _alternate_url(params, organization=obj_dict['name'])
        desc = u'Recently created or updated datasets on %s '\
               'by organization: "%s"' % (site_title, obj_dict['title'])
        title = u'%s - Organization: "%s"' % (site_title, obj_dict['title'])

    else:
        guid = _create_atom_id(u'feeds/group/%s.atom' % obj_dict['name'])
        alternate_url = _alternate_url(params, groups=obj_dict['name'])
        desc = u'Recently created or updated datasets on %s '\
               'by group: "%s"' % (site_title, obj_dict['title'])
        title = u'%s - Group: "%s"' % (site_title, obj_dict['title'])

    return output_feed(
        results,
        feed_title=title,
        feed_description=desc,
        feed_link=alternate_url,
        feed_guid=guid,
        feed_url=feed_url,
        navigation_urls=navigation_urls)


def _parse_url_params() -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Constructs a search-query dict from the URL query parameters.

    Returns the constructed search-query dict, and the valid URL
    query parameters.
    """
    page = h.get_page_number(request.args)

    limit = config.get('ckan.feeds.limit')
    data_dict = {u'start': (page - 1) * limit, u'rows': limit}

    # Filter ignored query parameters
    valid_params = ['page']
    params = dict((p, request.args.get(p)) for p in valid_params
                  if p in request.args)
    return data_dict, params


def general() -> Response:
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

    site_title = config.get(u'ckan.site_title')
    desc = u'Recently created or updated datasets on %s' % site_title

    return output_feed(
        results,
        feed_title=site_title,
        feed_description=desc,
        feed_link=alternate_url,
        feed_guid=guid,
        feed_url=feed_url,
        navigation_urls=navigation_urls)


def custom() -> Response:
    """
    Custom atom feed

    """
    q = request.args.get(u'q', u'')
    fq = u''
    search_params = {}
    for (param, value) in request.args.items():
        if param not in [u'q', u'page', u'sort'] \
                and len(value) and not param.startswith(u'_'):
            search_params[param] = value
            fq += u'%s:"%s"' % (param, value)

    page = h.get_page_number(request.args)

    limit = config.get('ckan.feeds.limit')
    data_dict: dict[str, Any] = {
        u'q': q,
        u'fq': fq,
        u'start': (page - 1) * limit,
        u'rows': limit,
        u'sort': request.args.get(u'sort', None)
    }

    item_count, results = _package_search(data_dict)

    navigation_urls = _navigation_urls(
        request.args,
        item_count=item_count,
        limit=data_dict['rows'],
        controller=u'feeds',
        action=u'custom')

    feed_url = _feed_url(request.args, controller=u'feeds', action=u'custom')

    atom_url = _url_with_params(u'/feeds/custom.atom', search_params.items())

    alternate_url = _alternate_url(request.args)
    site_title = config.get(u'ckan.site_title')
    return output_feed(
        results,
        feed_title=u'%s - Custom query' % site_title,
        feed_description=u'Recently created or updated'
        ' datasets on %s. Custom query: \'%s\'' % (site_title, q),
        feed_link=alternate_url,
        feed_guid=_create_atom_id(atom_url),
        feed_url=feed_url,
        navigation_urls=navigation_urls)


def _alternate_url(params: dict[str, Any], **kwargs: Any) -> str:
    search_params = params.copy()
    search_params.update(kwargs)

    # Can't count on the page sizes being the same on the search results
    # view.  So provide an alternate link to the first page, regardless
    # of the page we're looking at in the feed.
    search_params.pop(u'page', None)
    return _feed_url(search_params, controller=u'dataset', action=u'search')


def _feed_url(query: dict[str, Any], controller: str, action: str,
              **kwargs: Any) -> str:
    """
    Constructs the url for the given action.  Encoding the query
    parameters.
    """
    for item in query.items():
        kwargs['query'] = item
    endpoint = controller + '.' + action
    return h.url_for(endpoint, **kwargs)


def _navigation_urls(
        query: dict[str, Any], controller: str, action: str,
        item_count: int, limit: int, **kwargs: Any) -> dict[str, Any]:
    """
    Constructs and returns first, last, prev and next links for paging
    """

    urls: dict[str, Optional[str]] = dict(
        (rel, None) for rel in u'previous next first last'.split()
    )

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


def _create_atom_id(resource_path: str,
                    authority_name: Optional[str] = None,
                    date_string: Optional[str] = None) -> str:
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
        authority_name = config.get(u'ckan.feeds.authority_name')
        if not authority_name:
            site_url = config.get(u'ckan.site_url')
            authority_name = urlparse(site_url).netloc

    if not authority_name:
        log.warning(u'No authority_name available for feed generation.  '
                    'Generated feed will be invalid.')
        authority_name = ''
    if date_string is None:
        date_string = config.get(u'ckan.feeds.date')

    if not date_string:
        log.warning(u'No date_string available for feed generation.  '
                    'Please set the "ckan.feeds.date" config value.')

        # Don't generate a tagURI without a date as it wouldn't be valid.
        # This is best we can do, and if the site_url is not set, then
        # this still results in an invalid feed.
        site_url = config.get(u'ckan.site_url')
        return u''.join([site_url, resource_path])

    tagging_entity = u','.join([authority_name, date_string])
    return u':'.join(['tag', tagging_entity, resource_path])


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
