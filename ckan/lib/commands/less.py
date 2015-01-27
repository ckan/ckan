import os

from ckan.lib.commands import CkanCommand


class LessCommand(CkanCommand):
    '''Compile all root less documents into their CSS counterparts

    Usage:

        paster less

    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 0

    def command(self):
        self.less()

    custom_css = {
        'fuchsia': '''
            @layoutLinkColor: #E73892;
            @footerTextColor: mix(#FFF, @layoutLinkColor, 60%);
            @footerLinkColor: @footerTextColor;
            @mastheadBackgroundColor: @layoutLinkColor;
            @btnPrimaryBackground: lighten(@layoutLinkColor, 10%);
            @btnPrimaryBackgroundHighlight: @layoutLinkColor;
            ''',

        'green': '''
            @layoutLinkColor: #2F9B45;
            @footerTextColor: mix(#FFF, @layoutLinkColor, 60%);
            @footerLinkColor: @footerTextColor;
            @mastheadBackgroundColor: @layoutLinkColor;
            @btnPrimaryBackground: lighten(@layoutLinkColor, 10%);
            @btnPrimaryBackgroundHighlight: @layoutLinkColor;
            ''',

        'red': '''
            @layoutLinkColor: #C14531;
            @footerTextColor: mix(#FFF, @layoutLinkColor, 60%);
            @footerLinkColor: @footerTextColor;
            @mastheadBackgroundColor: @layoutLinkColor;
            @btnPrimaryBackground: lighten(@layoutLinkColor, 10%);
            @btnPrimaryBackgroundHighlight: @layoutLinkColor;
            ''',

        'maroon': '''
            @layoutLinkColor: #810606;
            @footerTextColor: mix(#FFF, @layoutLinkColor, 60%);
            @footerLinkColor: @footerTextColor;
            @mastheadBackgroundColor: @layoutLinkColor;
            @btnPrimaryBackground: lighten(@layoutLinkColor, 10%);
            @btnPrimaryBackgroundHighlight: @layoutLinkColor;
            ''',
    }

    def less(self):
        ''' Compile less files '''
        import subprocess
        command = 'npm bin'
        process = subprocess.Popen(command, shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   universal_newlines=True)
        output = process.communicate()
        directory = output[0].strip()
        less_bin = os.path.join(directory, 'lessc')

        root = os.path.join(os.path.dirname(__file__),
                            '..', '..', 'public', 'base')
        root = os.path.abspath(root)
        custom_less = os.path.join(root, 'less', 'custom.less')
        for color in self.custom_css:
            f = open(custom_less, 'w')
            f.write(self.custom_css[color])
            f.close()
            self.compile_less(root, less_bin, color)
        f = open(custom_less, 'w')
        f.write('// This file is needed in order for ./bin/less to'
                ' compile in less 1.3.1+\n')
        f.close()
        self.compile_less(root, less_bin, 'main')

    def compile_less(self, root, less_bin, color):
        print 'compile %s.css' % color
        import subprocess
        main_less = os.path.join(root, 'less', 'main.less')
        main_css = os.path.join(root, 'css', '%s.css' % color)

        command = '%s %s %s' % (less_bin, main_less, main_css)

        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   universal_newlines=True)
        process.communicate()
