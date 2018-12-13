# Copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
#     1. Redistributions of source code must retain the above copyright notice, 
#        this list of conditions and the following disclaimer.
#     
#     2. Redistributions in binary form must reproduce the above copyright 
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
# 
#     3. Neither the name of Django nor the names of its contributors may be used
#        to endorse or promote products derived from this software without
#        specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Last synched with Django source 2009-12-18 (Django revision 11910):
# http://code.djangoproject.com/browser/django/trunk/django/utils/feedgenerator.py
# http://code.djangoproject.com/browser/django/trunk/django/contrib/gis/feeds.py

# WebHelpers changes from original:
# ---------------------------------
# - Combine ``django.utils.feedgenerator`` and ``django.contrib.gis.feeds``.
# - Change imports: 
#     * ``SimpleXMLGenerator`` and ``iri_to_uri`` are in ``webhelpers.util``.
#     * Add local copy of ``force_unicode``.
# - Delete parts that depend on Django's ORM system: ``Feed`` class, 
#   ``BaseFeed`` and ``FeedDoesNotExist`` imports.
# - Delete ``to_unicode`` lambdas and ``force_unicode`` import; these seem
#   unnecessary.
# - Change docstring imports.
# - Apply ``rfc3339_date`` bugfix (02044132a2ef) to both that function and
#   and ``rfc2822_date``.  (``.tzinfo`` attribute may not exist in datetime
#   objects.)
# - Apply 'published' property patch (1f234b039b58).
# - Note: 'generator' and 'source' properties were lost from a previous
#   revision of webhelpers.feedgenerator. The implementation had a bug and
#   can't be used as is.
# - Extend latitude-longitude behavior so that data can be input in either
#   lat-lon or lon-lat format. Output is always written in lat-lon per the
#   GeoRSS spec. Django's feedgenerator expects lon-lat input for GeoDjango
#   compatibility.  WebHelpers defaults to lat-lon but can be switched to
#   lon-lat by setting the ``GeoFeedMixin.is_input_latitude_first`` flag to
#   false. (The flag can be set in a subclass or instance anytime before the
#   output is written.) The swapping is done in
#   ``GeoFeedMixin.georss_coords()`` and ``.add_georss_point()``.
# - "if geom is not None" syntax fix in ``GeoFeedMixin.get_georss_element()``.
# - Add a ``Geometry`` class for passing geometries to the Geo classes.
# - ``GeoFeedMixin`` docstring.
# - Add a dummy version attribute to ``RssFeed`` base class. 
#   ``RssFeed._version = # "?"`` This avoids AttributeError when instantiating
#   ``RssFeed`` directly, although it's obviously invalid RSS.


"""
Syndication feed generation library -- used for generating RSS, etc.

Sample usage:

>>> import webhelpers.feedgenerator as feedgenerator
>>> feed = feedgenerator.Rss201rev2Feed(
...     title=u"Poynter E-Media Tidbits",
...     link=u"http://www.poynter.org/column.asp?id=31",
...     description=u"A group weblog by the sharpest minds in online media/journalism/publishing.",
...     language=u"en",
... )
>>> feed.add_item(title="Hello", link=u"http://www.holovaty.com/test/", description="Testing.")
>>> fp = open('test.rss', 'w')
>>> feed.write(fp, 'utf-8')
>>> fp.close()

For definitions of the different versions of RSS, see:
http://diveintomark.org/archives/2004/02/04/incompatible-rss
"""

import re
import datetime
from webhelpers.util import SimplerXMLGenerator, iri_to_uri

#### The following code comes from ``django.utils.feedgenerator`` ####

def rfc2822_date(date):
    # We do this ourselves to be timezone aware, email.Utils is not tz aware.
    if getattr(date, "tzinfo", False):
        time_str = date.strftime('%a, %d %b %Y %H:%M:%S ')
        offset = date.tzinfo.utcoffset(date)
        timezone = (offset.days * 24 * 60) + (offset.seconds / 60)
        hour, minute = divmod(timezone, 60)
        return time_str + "%+03d%02d" % (hour, minute)
    else:
        return date.strftime('%a, %d %b %Y %H:%M:%S -0000')

def rfc3339_date(date):
    if getattr(date, "tzinfo", False):
        time_str = date.strftime('%Y-%m-%dT%H:%M:%S')
        offset = date.tzinfo.utcoffset(date)
        timezone = (offset.days * 24 * 60) + (offset.seconds / 60)
        hour, minute = divmod(timezone, 60)
        return time_str + "%+03d:%02d" % (hour, minute)
    else:
        return date.strftime('%Y-%m-%dT%H:%M:%SZ')

def get_tag_uri(url, date):
    "Creates a TagURI. See http://diveintomark.org/archives/2004/05/28/howto-atom-id"
    tag = re.sub('^http://', '', url)
    if date is not None:
        tag = re.sub('/', ',%s:/' % date.strftime('%Y-%m-%d'), tag, 1)
    tag = re.sub('#', '/', tag)
    return u'tag:' + tag

class SyndicationFeed(object):
    "Base class for all syndication feeds. Subclasses should provide write()"
    def __init__(self, title, link, description, language=None, author_email=None,
            author_name=None, author_link=None, subtitle=None, categories=None,
            feed_url=None, feed_copyright=None, feed_guid=None, ttl=None, **kwargs):
        if categories:
            categories = [force_unicode(c) for c in categories]
        self.feed = {
            'title': title,
            'link': iri_to_uri(link),
            'description': description,
            'language': language,
            'author_email': author_email,
            'author_name': author_name,
            'author_link': iri_to_uri(author_link),
            'subtitle': subtitle,
            'categories': categories or (),
            'feed_url': iri_to_uri(feed_url),
            'feed_copyright': feed_copyright,
            'id': feed_guid or link,
            'ttl': ttl,
        }
        self.feed.update(kwargs)
        self.items = []

    def add_item(self, title, link, description, author_email=None,
        author_name=None, author_link=None, pubdate=None, comments=None,
        unique_id=None, enclosure=None, categories=(), item_copyright=None,
        ttl=None, **kwargs):
        """
        Adds an item to the feed. All args are expected to be Python Unicode
        objects except pubdate, which is a datetime.datetime object, and
        enclosure, which is an instance of the Enclosure class.
        """
        item = {
            'title': title,
            'link': iri_to_uri(link),
            'description': description,
            'author_email': author_email,
            'author_name': author_name,
            'author_link': iri_to_uri(author_link),
            'pubdate': pubdate,
            'comments': comments,
            'unique_id': unique_id,
            'enclosure': enclosure,
            'categories': categories or (),
            'item_copyright': item_copyright,
            'ttl': ttl,
        }
        item.update(kwargs)
        self.items.append(item)

    def num_items(self):
        return len(self.items)

    def root_attributes(self):
        """
        Return extra attributes to place on the root (i.e. feed/channel) element.
        Called from write().
        """
        return {}

    def add_root_elements(self, handler):
        """
        Add elements in the root (i.e. feed/channel) element. Called
        from write().
        """
        pass

    def item_attributes(self, item):
        """
        Return extra attributes to place on each item (i.e. item/entry) element.
        """
        return {}

    def add_item_elements(self, handler, item):
        """
        Add elements on each item (i.e. item/entry) element.
        """
        pass

    def write(self, outfile, encoding):
        """
        Outputs the feed in the given encoding to outfile, which is a file-like
        object. Subclasses should override this.
        """
        raise NotImplementedError

    def writeString(self, encoding):
        """
        Returns the feed in the given encoding as a string.
        """
        from StringIO import StringIO
        s = StringIO()
        self.write(s, encoding)
        return s.getvalue()

    def latest_post_date(self):
        """
        Returns the latest item's pubdate. If none of them have a pubdate,
        this returns the current date/time.
        """
        updates = [i['pubdate'] for i in self.items if i['pubdate'] is not None]
        if len(updates) > 0:
            updates.sort()
            return updates[-1]
        else:
            return datetime.datetime.now()

class Enclosure(object):
    "Represents an RSS enclosure"
    def __init__(self, url, length, mime_type):
        "All args are expected to be Python Unicode objects"
        self.length, self.mime_type = length, mime_type
        self.url = iri_to_uri(url)

class RssFeed(SyndicationFeed):
    mime_type = 'application/rss+xml'
    _version = u"?"
    def write(self, outfile, encoding):
        handler = SimplerXMLGenerator(outfile, encoding)
        handler.startDocument()
        handler.startElement(u"rss", self.rss_attributes())
        handler.startElement(u"channel", self.root_attributes())
        self.add_root_elements(handler)
        self.write_items(handler)
        self.endChannelElement(handler)
        handler.endElement(u"rss")

    def rss_attributes(self):
        return {u"version": self._version}

    def write_items(self, handler):
        for item in self.items:
            handler.startElement(u'item', self.item_attributes(item))
            self.add_item_elements(handler, item)
            handler.endElement(u"item")

    def add_root_elements(self, handler):
        handler.addQuickElement(u"title", self.feed['title'])
        handler.addQuickElement(u"link", self.feed['link'])
        handler.addQuickElement(u"description", self.feed['description'])
        if self.feed['language'] is not None:
            handler.addQuickElement(u"language", self.feed['language'])
        for cat in self.feed['categories']:
            handler.addQuickElement(u"category", cat)
        if self.feed['feed_copyright'] is not None:
            handler.addQuickElement(u"copyright", self.feed['feed_copyright'])
        handler.addQuickElement(u"lastBuildDate", rfc2822_date(self.latest_post_date()).decode('utf-8'))
        if self.feed['ttl'] is not None:
            handler.addQuickElement(u"ttl", self.feed['ttl'])

    def endChannelElement(self, handler):
        handler.endElement(u"channel")

class RssUserland091Feed(RssFeed):
    _version = u"0.91"
    def add_item_elements(self, handler, item):
        handler.addQuickElement(u"title", item['title'])
        handler.addQuickElement(u"link", item['link'])
        if item['description'] is not None:
            handler.addQuickElement(u"description", item['description'])

class Rss201rev2Feed(RssFeed):
    # Spec: http://blogs.law.harvard.edu/tech/rss
    _version = u"2.0"
    def add_item_elements(self, handler, item):
        handler.addQuickElement(u"title", item['title'])
        handler.addQuickElement(u"link", item['link'])
        if item['description'] is not None:
            handler.addQuickElement(u"description", item['description'])

        # Author information.
        if item["author_name"] and item["author_email"]:
            handler.addQuickElement(u"author", "%s (%s)" % \
                (item['author_email'], item['author_name']))
        elif item["author_email"]:
            handler.addQuickElement(u"author", item["author_email"])
        elif item["author_name"]:
            handler.addQuickElement(u"dc:creator", item["author_name"], {"xmlns:dc": u"http://purl.org/dc/elements/1.1/"})

        if item['pubdate'] is not None:
            handler.addQuickElement(u"pubDate", rfc2822_date(item['pubdate']).decode('utf-8'))
        if item['comments'] is not None:
            handler.addQuickElement(u"comments", item['comments'])
        if item['unique_id'] is not None:
            handler.addQuickElement(u"guid", item['unique_id'])
        if item['ttl'] is not None:
            handler.addQuickElement(u"ttl", item['ttl'])

        # Enclosure.
        if item['enclosure'] is not None:
            handler.addQuickElement(u"enclosure", '',
                {u"url": item['enclosure'].url, u"length": item['enclosure'].length,
                    u"type": item['enclosure'].mime_type})

        # Categories.
        for cat in item['categories']:
            handler.addQuickElement(u"category", cat)

class Atom1Feed(SyndicationFeed):
    # Spec: http://atompub.org/2005/07/11/draft-ietf-atompub-format-10.html
    mime_type = 'application/atom+xml'
    ns = u"http://www.w3.org/2005/Atom"

    def write(self, outfile, encoding):
        handler = SimplerXMLGenerator(outfile, encoding)
        handler.startDocument()
        handler.startElement(u'feed', self.root_attributes())
        self.add_root_elements(handler)
        self.write_items(handler)
        handler.endElement(u"feed")

    def root_attributes(self):
        if self.feed['language'] is not None:
            return {u"xmlns": self.ns, u"xml:lang": self.feed['language']}
        else:
            return {u"xmlns": self.ns}

    def add_root_elements(self, handler):
        handler.addQuickElement(u"title", self.feed['title'])
        handler.addQuickElement(u"link", "", {u"rel": u"alternate", u"href": self.feed['link']})
        if self.feed['feed_url'] is not None:
            handler.addQuickElement(u"link", "", {u"rel": u"self", u"href": self.feed['feed_url']})
        handler.addQuickElement(u"id", self.feed['id'])
        handler.addQuickElement(u"updated", rfc3339_date(self.latest_post_date()).decode('utf-8'))
        if self.feed['author_name'] is not None:
            handler.startElement(u"author", {})
            handler.addQuickElement(u"name", self.feed['author_name'])
            if self.feed['author_email'] is not None:
                handler.addQuickElement(u"email", self.feed['author_email'])
            if self.feed['author_link'] is not None:
                handler.addQuickElement(u"uri", self.feed['author_link'])
            handler.endElement(u"author")
        if self.feed['subtitle'] is not None:
            handler.addQuickElement(u"subtitle", self.feed['subtitle'])
        for cat in self.feed['categories']:
            handler.addQuickElement(u"category", "", {u"term": cat})
        if self.feed['feed_copyright'] is not None:
            handler.addQuickElement(u"rights", self.feed['feed_copyright'])

    def write_items(self, handler):
        for item in self.items:
            handler.startElement(u"entry", self.item_attributes(item))
            self.add_item_elements(handler, item)
            handler.endElement(u"entry")

    def add_item_elements(self, handler, item):
        handler.addQuickElement(u"title", item['title'])
        handler.addQuickElement(u"link", u"", {u"href": item['link'], u"rel": u"alternate"})
        if item['pubdate'] is not None:
            handler.addQuickElement(u"updated", rfc3339_date(item['pubdate']).decode('utf-8'))
            handler.addQuickElement(u"published", rfc3339_date(item['pubdate']).decode('utf-8'))

        # Author information.
        if item['author_name'] is not None:
            handler.startElement(u"author", {})
            handler.addQuickElement(u"name", item['author_name'])
            if item['author_email'] is not None:
                handler.addQuickElement(u"email", item['author_email'])
            if item['author_link'] is not None:
                handler.addQuickElement(u"uri", item['author_link'])
            handler.endElement(u"author")

        # Unique ID.
        if item['unique_id'] is not None:
            unique_id = item['unique_id']
        else:
            unique_id = get_tag_uri(item['link'], item['pubdate'])
        handler.addQuickElement(u"id", unique_id)

        # Summary.
        if item['description'] is not None:
            handler.addQuickElement(u"summary", item['description'], {u"type": u"html"})

        # Enclosure.
        if item['enclosure'] is not None:
            handler.addQuickElement(u"link", '',
                {u"rel": u"enclosure",
                 u"href": item['enclosure'].url,
                 u"length": item['enclosure'].length,
                 u"type": item['enclosure'].mime_type})

        # Categories.
        for cat in item['categories']:
            handler.addQuickElement(u"category", u"", {u"term": cat})

        # Rights.
        if item['item_copyright'] is not None:
            handler.addQuickElement(u"rights", item['item_copyright'])

# This isolates the decision of what the system default is, so calling code can
# do "feedgenerator.DefaultFeed" instead of "feedgenerator.Rss201rev2Feed".
DefaultFeed = Rss201rev2Feed


#### The following code comes from ``django.contrib.gis.feeds`` ####

class GeoFeedMixin(object):
    """
    This mixin provides the necessary routines for SyndicationFeed subclasses
    to produce simple GeoRSS or W3C Geo elements.

    Subclasses recognize a ``geometry`` keyword argument to ``.add_item()``.
    The value may be any of several types:

    * a 2-element tuple or list of floats representing latitude/longitude: 
      ``(X, Y)``.  This is called a "point".

    * a 4-element tuple or list of floats representing a box:
      ``(X0, Y0, X1, Y1)``.

    * a tuple or list of two points: ``( (X0, Y0), (X1, Y1) )``.

    * a ``Geometry`` instance. (Or any compatible class.)  This provides
      limited support for points, lines, and polygons. Read the ``Geometry``
      docstring and the source of ``GeoFeedMixin.add_georss_element()``
      before using this.

    The mixin provides one class attribute:

    .. attribute:: is_input_latitude_first

       The default value False indicates that input data is in
       latitude/longitude order. Change to True if the input data is
       longitude/latitude. The output is always written latitude/longitude
       to conform to the GeoRSS spec.

       The reason for this attribute is that the Django original stores data
       in longitude/latutude order and reverses the arguments before writing.
       WebHelpers does not do this by default, but if you're using Django data
       or other data that has longitude first, you'll have to set this.
    """

    # Set to True if the input data is in lat-lon order, or False if lon-lat.
    # The output is always written in lat-lon order.
    is_input_latitude_first = True

    def georss_coords(self, coords):
        """
        In GeoRSS coordinate pairs are ordered by lat/lon and separated by
        a single white space.  Given a tuple of coordinates, this will return
        a unicode GeoRSS representation.
        """
        if self.is_input_latitude_first:
            return u' '.join([u'%f %f' % x for x in coords])
        else:
            return u' '.join([u'%f %f' % (x[1], x[0]) for x in coords])

    def add_georss_point(self, handler, coords, w3c_geo=False):
        """
        Adds a GeoRSS point with the given coords using the given handler.
        Handles the differences between simple GeoRSS and the more popular
        W3C Geo specification.
        """
        if w3c_geo:
            if self.is_input_latitude_first:
                lat, lon = coords[:2]
            else:
                lon, lat = coords[:2]
            handler.addQuickElement(u'geo:lat', u'%f' % lat)
            handler.addQuickElement(u'geo:lon', u'%f' % lon)
        else:
            handler.addQuickElement(u'georss:point', self.georss_coords((coords,)))

    def add_georss_element(self, handler, item, w3c_geo=False):
        """
        This routine adds a GeoRSS XML element using the given item and handler.
        """
        # Getting the Geometry object.
        geom = item.get('geometry', None)
        if geom is not None:
            if isinstance(geom, (list, tuple)):
                # Special case if a tuple/list was passed in.  The tuple may be
                # a point or a box
                box_coords = None
                if isinstance(geom[0], (list, tuple)):
                    # Box: ( (X0, Y0), (X1, Y1) )
                    if len(geom) == 2:
                        box_coords = geom
                    else:
                        raise ValueError('Only should be two sets of coordinates.')
                else:
                    if len(geom) == 2:
                        # Point: (X, Y)
                        self.add_georss_point(handler, geom, w3c_geo=w3c_geo)
                    elif len(geom) == 4:
                        # Box: (X0, Y0, X1, Y1)
                        box_coords = (geom[:2], geom[2:])
                    else:
                        raise ValueError('Only should be 2 or 4 numeric elements.')
                # If a GeoRSS box was given via tuple.
                if not box_coords is None:
                    if w3c_geo: raise ValueError('Cannot use simple GeoRSS box in W3C Geo feeds.')
                    handler.addQuickElement(u'georss:box', self.georss_coords(box_coords))
            else:
                # Getting the lower-case geometry type.
                gtype = str(geom.geom_type).lower()
                if gtype == 'point':
                    self.add_georss_point(handler, geom.coords, w3c_geo=w3c_geo) 
                else:
                    if w3c_geo: raise ValueError('W3C Geo only supports Point geometries.')
                    # For formatting consistent w/the GeoRSS simple standard:
                    # http://georss.org/1.0#simple
                    if gtype in ('linestring', 'linearring'):
                        handler.addQuickElement(u'georss:line', self.georss_coords(geom.coords))
                    elif gtype in ('polygon',):
                        # Only support the exterior ring.
                        handler.addQuickElement(u'georss:polygon', self.georss_coords(geom[0].coords))
                    else:
                        raise ValueError('Geometry type "%s" not supported.' % geom.geom_type)

### SyndicationFeed subclasses ###
class GeoRSSFeed(Rss201rev2Feed, GeoFeedMixin):
    def rss_attributes(self):
        attrs = super(GeoRSSFeed, self).rss_attributes()
        attrs[u'xmlns:georss'] = u'http://www.georss.org/georss'
        return attrs

    def add_item_elements(self, handler, item):
        super(GeoRSSFeed, self).add_item_elements(handler, item)
        self.add_georss_element(handler, item)

    def add_root_elements(self, handler):
        super(GeoRSSFeed, self).add_root_elements(handler)
        self.add_georss_element(handler, self.feed)

class GeoAtom1Feed(Atom1Feed, GeoFeedMixin):
    def root_attributes(self):
        attrs = super(GeoAtom1Feed, self).root_attributes()
        attrs[u'xmlns:georss'] = u'http://www.georss.org/georss'
        return attrs

    def add_item_elements(self, handler, item):
        super(GeoAtom1Feed, self).add_item_elements(handler, item)
        self.add_georss_element(handler, item)

    def add_root_elements(self, handler):
        super(GeoAtom1Feed, self).add_root_elements(handler)
        self.add_georss_element(handler, self.feed)

class W3CGeoFeed(Rss201rev2Feed, GeoFeedMixin):
    def rss_attributes(self):
        attrs = super(W3CGeoFeed, self).rss_attributes()
        attrs[u'xmlns:geo'] = u'http://www.w3.org/2003/01/geo/wgs84_pos#'
        return attrs

    def add_item_elements(self, handler, item):
        super(W3CGeoFeed, self).add_item_elements(handler, item)
        self.add_georss_element(handler, item, w3c_geo=True)

    def add_root_elements(self, handler):
        super(W3CGeoFeed, self).add_root_elements(handler)
        self.add_georss_element(handler, self.feed, w3c_geo=True)


class Geometry(object):
    """A basic geometry class for ``GeoFeedMixin``.

    Instances have two public attributes:

    .. attribute:: geom_type

       "point", "linestring", "linearring", "polygon"

    .. attribute:: coords

       For **point**, a tuple or list of two floats: ``(X, Y)``.

       For **linestring** or **linearring**, a string: ``"X0 Y0  X1 Y1 ..."``.

       For **polygon**, a list of strings: ``["X0 Y0  X1 Y1 ..."]``. Only the
       first element is used because the Geo classes support only the exterior
       ring.

    The constructor does not check its argument types.
      
    This class was created for WebHelpers based on the interface expected by
    ``GeoFeedMixin.add_georss_element()``.  The class is untested. Please send
    us feedback on whether it works for you.
    """

    def __init__(self, geom_type, coords):
        self.geom_type = geom_type
        coords = coords
