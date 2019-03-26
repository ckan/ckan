# encoding: utf-8

import colorsys
import logging
import os
import random
import re

import click
import webcolors

from ckan.common import config

log = logging.getLogger(__name__)

RULES = [
    u'@layoutLinkColor',
    u'@mastheadBackgroundColor',
    u'@btnPrimaryBackground',
    u'@btnPrimaryBackgroundHighlight',
]


class Hue(click.ParamType):
    name = u'hue'

    def convert(self, value, param, ctx):
        try:
            hue = float(value)
        except ValueError:
            self.fail(value)
        if not 0 <= hue <= 1:
            self.fail(u'{} not between 0.0 and 1.0'.format(value))
        return hue


class ColorName(click.ParamType):
    name = u'color-name'

    def convert(self, value, param, ctx):
        try:
            return webcolors.name_to_rgb(value)
        except ValueError:
            self.fail(value)


class HexColor(click.ParamType):
    name = u'hex-color'

    def convert(self, value, param, ctx):
        value = value.lstrip(u'#')
        if len(value) == 3:
            value = u''.join(char * 2 for char in value)
        if len(value) != 6:
            self.fail(u'<{}> is not a color string.'.format(value))
        try:
            rgb = [int(value[i:i + 2], 16) for i in range(0, 6, 2)]
        except ValueError:
            self.fail(u'<{}> is not a hexadecimal string.'.format(value))
        return rgb


def create_colors(hue, saturation=.9, lightness=.4):
    lightness *= 100
    saturation -= int(saturation)

    colors = []
    for i in range(len(RULES)):
        ix = i * (1.0 / len(RULES))
        _lightness = min(1., abs((lightness + (ix * 40)) / 100.))

        color = colorsys.hls_to_rgb(hue, _lightness, saturation)
        hex_color = u'#'
        for part in color:
            hex_color += u'%02x' % int(part * 255)

        # check and remove any bad values
        if not re.match(u'^#[0-9a-f]{6}$', hex_color):
            hex_color = u'#FFFFFF'
        colors.append(hex_color)

    f = open(get_custom_theme_path(), u'w')
    for rule, color in zip(RULES, colors):
        f.write(u'%s: %s;\n' % (rule, color))
        click.echo(u'%s: %s;\n' % (rule, color))
    f.close()
    click.secho(u'Color scheme has been created.', fg=u'green', bold=True)


def get_custom_theme_path():
    return os.path.join(
        os.path.dirname(__file__), u'..',
        config.get(u'ckan.base_public_folder', u'public'), u'base', u'less',
        u'custom.less'
    )


@click.group(
    short_help=u'Create or remove a color scheme.',
    help=u'After running this, you will need to regenerate '
    u'the css files. See `less` command for details'
)
def color():
    pass


@color.command(short_help=u'Clears any color scheme.')
def clear():
    custom_theme = get_custom_theme_path()
    if os.path.isfile(custom_theme):
        os.remove(custom_theme)
    click.secho(u'Custom theme removed.', fg=u'green', bold=True)


@color.command(name=u'random', short_help=u'Creates a random color scheme.')
def generate_random():
    create_colors(random.random())


@color.command(name=u'hex', short_help=u'Uses as base color(eg. "ff00ff").')
@click.argument(u'color', type=HexColor())
def generate_hex(color):
    hue, saturation, lightness = colorsys.rgb_to_hls(*color)
    create_colors(hue, saturation, lightness)


@color.command(
    name=u'hue', short_help=u'A float between 0.0 and 1.0 used as base hue.'
)
@click.argument(u'hue', type=Hue())
def generate_hue(hue):
    create_colors(hue)


@color.command(
    name=u'name',
    short_help=u'HTML color name used for base color(eg. maroon).'
)
@click.argument(u'color', type=ColorName())
def generate_name(color):
    hue, saturation, lightness = colorsys.rgb_to_hls(*color)
    create_colors(hue, saturation, lightness)
