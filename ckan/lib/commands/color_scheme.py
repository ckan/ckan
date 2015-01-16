import os
import re

from ckan.lib.commands import CkanCommand


class CreateColorSchemeCommand(CkanCommand):
    '''Create or remove a color scheme.

    After running this, you'll need to regenerate the css files. See paster's
    less command for details.

    color               - creates a random color scheme
    color clear         - clears any color scheme
    color <'HEX'>       - uses as base color eg '#ff00ff' must be quoted.
    color <VALUE>       - a float between 0.0 and 1.0 used as base hue
    color <COLOR_NAME>  - html color name used for base color eg lightblue
    '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 1
    min_args = 0

    rules = [
        '@layoutLinkColor',
        '@mastheadBackgroundColor',
        '@btnPrimaryBackground',
        '@btnPrimaryBackgroundHighlight',
    ]

    # list of predefined colors
    color_list = {
        'aliceblue': '#f0fff8',
        'antiquewhite': '#faebd7',
        'aqua': '#00ffff',
        'aquamarine': '#7fffd4',
        'azure': '#f0ffff',
        'beige': '#f5f5dc',
        'bisque': '#ffe4c4',
        'black': '#000000',
        'blanchedalmond': '#ffebcd',
        'blue': '#0000ff',
        'blueviolet': '#8a2be2',
        'brown': '#a52a2a',
        'burlywood': '#deb887',
        'cadetblue': '#5f9ea0',
        'chartreuse': '#7fff00',
        'chocolate': '#d2691e',
        'coral': '#ff7f50',
        'cornflowerblue': '#6495ed',
        'cornsilk': '#fff8dc',
        'crimson': '#dc143c',
        'cyan': '#00ffff',
        'darkblue': '#00008b',
        'darkcyan': '#008b8b',
        'darkgoldenrod': '#b8860b',
        'darkgray': '#a9a9a9',
        'darkgrey': '#a9a9a9',
        'darkgreen': '#006400',
        'darkkhaki': '#bdb76b',
        'darkmagenta': '#8b008b',
        'darkolivegreen': '#556b2f',
        'darkorange': '#ff8c00',
        'darkorchid': '#9932cc',
        'darkred': '#8b0000',
        'darksalmon': '#e9967a',
        'darkseagreen': '#8fbc8f',
        'darkslateblue': '#483d8b',
        'darkslategray': '#2f4f4f',
        'darkslategrey': '#2f4f4f',
        'darkturquoise': '#00ced1',
        'darkviolet': '#9400d3',
        'deeppink': '#ff1493',
        'deepskyblue': '#00bfff',
        'dimgray': '#696969',
        'dimgrey': '#696969',
        'dodgerblue': '#1e90ff',
        'firebrick': '#b22222',
        'floralwhite': '#fffaf0',
        'forestgreen': '#228b22',
        'fuchsia': '#ff00ff',
        'gainsboro': '#dcdcdc',
        'ghostwhite': '#f8f8ff',
        'gold': '#ffd700',
        'goldenrod': '#daa520',
        'gray': '#808080',
        'grey': '#808080',
        'green': '#008000',
        'greenyellow': '#adff2f',
        'honeydew': '#f0fff0',
        'hotpink': '#ff69b4',
        'indianred ': '#cd5c5c',
        'indigo ': '#4b0082',
        'ivory': '#fffff0',
        'khaki': '#f0e68c',
        'lavender': '#e6e6fa',
        'lavenderblush': '#fff0f5',
        'lawngreen': '#7cfc00',
        'lemonchiffon': '#fffacd',
        'lightblue': '#add8e6',
        'lightcoral': '#f08080',
        'lightcyan': '#e0ffff',
        'lightgoldenrodyellow': '#fafad2',
        'lightgray': '#d3d3d3',
        'lightgrey': '#d3d3d3',
        'lightgreen': '#90ee90',
        'lightpink': '#ffb6c1',
        'lightsalmon': '#ffa07a',
        'lightseagreen': '#20b2aa',
        'lightskyblue': '#87cefa',
        'lightslategray': '#778899',
        'lightslategrey': '#778899',
        'lightsteelblue': '#b0c4de',
        'lightyellow': '#ffffe0',
        'lime': '#00ff00',
        'limegreen': '#32cd32',
        'linen': '#faf0e6',
        'magenta': '#ff00ff',
        'maroon': '#800000',
        'mediumaquamarine': '#66cdaa',
        'mediumblue': '#0000cd',
        'mediumorchid': '#ba55d3',
        'mediumpurple': '#9370d8',
        'mediumseagreen': '#3cb371',
        'mediumslateblue': '#7b68ee',
        'mediumspringgreen': '#00fa9a',
        'mediumturquoise': '#48d1cc',
        'mediumvioletred': '#c71585',
        'midnightblue': '#191970',
        'mintcream': '#f5fffa',
        'mistyrose': '#ffe4e1',
        'moccasin': '#ffe4b5',
        'navajowhite': '#ffdead',
        'navy': '#000080',
        'oldlace': '#fdf5e6',
        'olive': '#808000',
        'olivedrab': '#6b8e23',
        'orange': '#ffa500',
        'orangered': '#ff4500',
        'orchid': '#da70d6',
        'palegoldenrod': '#eee8aa',
        'palegreen': '#98fb98',
        'paleturquoise': '#afeeee',
        'palevioletred': '#d87093',
        'papayawhip': '#ffefd5',
        'peachpuff': '#ffdab9',
        'peru': '#cd853f',
        'pink': '#ffc0cb',
        'plum': '#dda0dd',
        'powderblue': '#b0e0e6',
        'purple': '#800080',
        'red': '#ff0000',
        'rosybrown': '#bc8f8f',
        'royalblue': '#4169e1',
        'saddlebrown': '#8b4513',
        'salmon': '#fa8072',
        'sandybrown': '#f4a460',
        'seagreen': '#2e8b57',
        'seashell': '#fff5ee',
        'sienna': '#a0522d',
        'silver': '#c0c0c0',
        'skyblue': '#87ceeb',
        'slateblue': '#6a5acd',
        'slategray': '#708090',
        'slategrey': '#708090',
        'snow': '#fffafa',
        'springgreen': '#00ff7f',
        'steelblue': '#4682b4',
        'tan': '#d2b48c',
        'teal': '#008080',
        'thistle': '#d8bfd8',
        'tomato': '#ff6347',
        'turquoise': '#40e0d0',
        'violet': '#ee82ee',
        'wheat': '#f5deb3',
        'white': '#ffffff',
        'whitesmoke': '#f5f5f5',
        'yellow': '#ffff00',
        'yellowgreen': '#9acd32',
    }

    def create_colors(self, hue, num_colors=5, saturation=None,
                      lightness=None):
        if saturation is None:
            saturation = 0.9
        if lightness is None:
            lightness = 40
        else:
            lightness *= 100

        import math
        saturation -= math.trunc(saturation)

        print hue, saturation
        import colorsys
        ''' Create n related colours '''
        colors = []
        for i in xrange(num_colors):
            ix = i * (1.0/num_colors)
            _lightness = (lightness + (ix * 40))/100.
            if _lightness > 1.0:
                _lightness = 1.0
            color = colorsys.hls_to_rgb(hue, _lightness, saturation)
            hex_color = '#'
            for part in color:
                hex_color += '%02x' % int(part * 255)
            # check and remove any bad values
            if not re.match('^\#[0-9a-f]{6}$', hex_color):
                hex_color = '#FFFFFF'
            colors.append(hex_color)
        return colors

    def command(self):

        hue = None
        saturation = None
        lightness = None

        path = os.path.dirname(__file__)
        path = os.path.join(path, '..', '..', 'public', 'base', 'less',
                            'custom.less')

        if self.args:
            arg = self.args[0]
            rgb = None
            if arg == 'clear':
                os.remove(path)
                print 'custom colors removed.'
            elif arg.startswith('#'):
                color = arg[1:]
                if len(color) == 3:
                    rgb = [int(x, 16) * 16 for x in color]
                elif len(color) == 6:
                    rgb = [int(x, 16) for x in re.findall('..', color)]
                else:
                    print 'ERROR: invalid color'
            elif arg.lower() in self.color_list:
                color = self.color_list[arg.lower()][1:]
                rgb = [int(x, 16) for x in re.findall('..', color)]
            else:
                try:
                    hue = float(self.args[0])
                except ValueError:
                    print 'ERROR argument `%s` not recognised' % arg
            if rgb:
                import colorsys
                hue, lightness, saturation = colorsys.rgb_to_hls(*rgb)
                lightness = lightness / 340
                # deal with greys
                if not (hue == 0.0 and saturation == 0.0):
                    saturation = None
        else:
            import random
            hue = random.random()
        if hue is not None:
            f = open(path, 'w')
            colors = self.create_colors(hue, saturation=saturation,
                                        lightness=lightness)
            for i in xrange(len(self.rules)):
                f.write('%s: %s;\n' % (self.rules[i], colors[i]))
                print '%s: %s;\n' % (self.rules[i], colors[i])
            f.close
            print 'Color scheme has been created.'
        print 'Make sure less is run for changes to take effect.'
