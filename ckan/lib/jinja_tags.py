from jinja2 import nodes
from jinja2.ext import Extension

import lib.base as base
import lib.helpers as h


class SnippetExtension(Extension):
    ''' Custom snippet tag

    {% snippet <template_name> [, <keyword>=<value>].. %}

    This is mostly magic..
    '''

    tags = set(['snippet'])

    def parse(self, parser):
        stream = parser.stream
        tag = stream.next()
        template_name = parser.parse_expression()
        # get keywords
        kwargs = []
        while not stream.current.test_any('block_end'):
            stream.expect('comma')
            if stream.current.test('name') and stream.look().test('assign'):
                key = nodes.Const(stream.next().value)
                stream.skip()
                value = parser.parse_expression()
                kwargs.append(nodes.Pair(key, value, lineno=key.lineno))

        def make_call_node(*kw):
            return self.call_method('_render', args=[
                template_name,
                nodes.Dict(kwargs),
            ], kwargs=kw)

        return nodes.Output([make_call_node()]).set_lineno(tag.lineno)

    @classmethod
    def _render(cls, template_name, kwargs):
        return base.render_snippet(template_name, **kwargs)


class UrlForExtension(Extension):
    ''' Custom url_for tag
    {% url_for(<params>) %}
    '''

    tags = set(['url_for'])

    def parse(self, parser):
        stream = parser.stream
        tag = stream.next()
        # get arguments
        args = []
        kwargs = []
        stream.expect('lparen')
        while stream.current.type != 'rparen':
            if args or kwargs:
                stream.expect('comma')
            if stream.current.test('name') and stream.look().test('assign'):
                key = nodes.Const(stream.next().value)
                stream.skip()
                value = parser.parse_expression()
                kwargs.append(nodes.Pair(key, value, lineno=key.lineno))
            else:
                args.append(parser.parse_expression())
        stream.expect('rparen')

        def make_call_node(*kw):
            return self.call_method('_url_for', args=[
                nodes.List(args),
                nodes.Dict(kwargs),
            ], kwargs=kw)

        return nodes.Output([make_call_node()]).set_lineno(tag.lineno)

    @classmethod
    def _url_for(cls, args, kwargs):
        return h.url_for(*args, **kwargs)
