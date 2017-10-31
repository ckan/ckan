import click
import validators
try:
    from urllib import parser as urlparse
except ImportError:
    import urlparse


class URL(click.ParamType):

    def convert(self, value, param, ctx):
        if not validators.url(value):
            self.fail('Invalid URL ')
        return value