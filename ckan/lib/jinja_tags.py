from jinja2 import nodes
from jinja2.ext import Extension

import lib.base as base
import lib.helpers as h


class BaseExtension(Extension):
    ''' Base class for creating custom jinja2 tags.
    parse expects a tag of the format
    {% tag_name args, kw %}
    after parsing it will call _call(args, kw) which must be defined. '''

    def parse(self, parser):
        stream = parser.stream
        tag = stream.next()
        # get arguments
        args = []
        kwargs = []
        while not stream.current.test_any('block_end'):
            if args or kwargs:
                stream.expect('comma')
            if stream.current.test('name') and stream.look().test('assign'):
                key = nodes.Const(stream.next().value)
                stream.skip()
                value = parser.parse_expression()
                kwargs.append(nodes.Pair(key, value, lineno=key.lineno))
            else:
                args.append(parser.parse_expression())

        def make_call_node(*kw):
            return self.call_method('_call', args=[
                nodes.List(args),
                nodes.Dict(kwargs),
            ], kwargs=kw)

        return nodes.Output([make_call_node()]).set_lineno(tag.lineno)


class SnippetExtension(BaseExtension):
    ''' Custom snippet tag

    {% snippet <template_name> [, <keyword>=<value>].. %}

    see lib.helpers.snippet() for more details.
    '''

    tags = set(['snippet'])

    @classmethod
    def _call(cls, args, kwargs):
        assert len(args) == 1
        return base.render_snippet(args[0], **kwargs)


class UrlForExtension(BaseExtension):
    ''' Custom url_for tag

    {% url_for <params> %}

    see lib.helpers.url_for() for more details.
    '''

    tags = set(['url_for'])

    @classmethod
    def _call(cls, args, kwargs):
        return h.url_for(*args, **kwargs)


class LinkForExtension(BaseExtension):
    ''' Custom link_for tag

    {% link_for <params> %}

    see lib.helpers.nav_link() for more details.
    '''

    tags = set(['link_for'])

    @classmethod
    def _call(cls, args, kwargs):
        return h.nav_link(*args, **kwargs)
