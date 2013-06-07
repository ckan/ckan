'''
The ConfigParser eats whitespace on continuation lines but we want
ReStructuredText for which whitespace is significant.

this parser only removes the first two spaces of continuation lines.
It also keeps blank lines.
'''


import ConfigParser


class ConfigIniParser(ConfigParser.RawConfigParser):
    def _read(self, fp, fpname):
        """Parse a sectioned setup file.

        The sections in setup file contains a title line at the top,
        indicated by a name in square brackets (`[]'), plus key/value
        options lines, indicated by `name: value' format lines.
        Continuations are represented by an embedded newline then
        leading whitespace.  Blank lines, lines beginning with a '#',
        and just about everything else are ignored.
        """
        cursect = None                            # None, or a dictionary
        optname = None
        lineno = 0
        e = None                                  # None, or an exception
        while True:
            line = fp.readline()
            if not line:
                break
            lineno = lineno + 1
            # comment or blank line?
            if line[0] in '#;':
                continue
            if (line.strip() and line.split(None, 1)[0].lower() == 'rem'
                    and line[0] in "rR"):
                # no leading whitespace
                continue
            # continuation line?
            if line[0].isspace() and cursect is not None and optname:
                value = line[:-1]
                if value.startswith('  '):
                    value = value[2:]
                if value or True:
                    cursect[optname] = "%s\n%s" % (cursect[optname], value)
            # a section header or option header?
            else:
                # is it a section header?
                mo = self.SECTCRE.match(line)
                if mo:
                    sectname = mo.group('header')
                    if sectname in self._sections:
                        raise Exception('%s has been included more than once'
                                        ' in the config_options.ini'
                                        % sectname)
                        cursect = self._sections[sectname]
                    elif sectname == ConfigParser.DEFAULTSECT:
                        cursect = self._defaults
                    else:
                        cursect = {'__name__': sectname}
                        self._sections[sectname] = cursect
                    # So sections can't start with a continuation line
                    optname = None
                # no section header in the file?
                elif cursect is None:
                    raise ConfigParser.MissingSectionHeaderError(
                        fpname, lineno, line)
                # an option line?
                else:
                    mo = self.OPTCRE.match(line)
                    if mo:
                        optname, vi, optval = mo.group('option', 'vi', 'value')
                        if vi in ('=', ':') and ';' in optval:
                            # ';' is a comment delimiter only if it follows
                            # a spacing character
                            pos = optval.find(';')
                            if pos != -1 and optval[pos - 1].isspace():
                                optval = optval[:pos]
                        optval = optval.strip()
                        # allow empty values
                        if optval == '""':
                            optval = ''
                        optname = self.optionxform(optname.rstrip())
                        cursect[optname] = optval
                    else:
                        # a non-fatal parsing error occurred.  set up the
                        # exception but keep going. the exception will be
                        # raised at the end of the file and will contain a
                        # list of all bogus lines
                        if not e:
                            e = ConfigParser.ParsingError(fpname)
                        e.append(lineno, repr(line))
        # if any parsing errors occurred, raise an exception
        if e:
            raise e
