from jinja2 import nodes
from jinja2.ext import Extension

import lib.base as base


class SnippetExtension(Extension):
    ''' Custom snippet tag

    {% snippet template_name> [, <keyword>=<value>].. %}

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

